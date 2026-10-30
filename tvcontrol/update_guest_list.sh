#!/bin/sh
# Rebuild the guest channel list after a channel scan: TV list -> KingOfSat data -> filter
# (free, German-language DE/AT/CH, no shopping/adult) -> top 50 -> tv.heissa.de + PDF.
# usage: [SKIP_READ=1] update_guest_list.sh [--mail]   (runs on kellertreppe, TV via adb)
set -e
TV=${TV:-192.168.178.195:5555}
DIR=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-/home/pi/tvrestore/guestlist}
OUT_JSON=/var/lib/tvremote/channels.json
MAILTO=gh@heissa.de
mkdir -p "$WORK"
cd "$WORK"

if [ "${SKIP_READ:-0}" = 1 ] && [ -s channels.tsv ]; then
    echo "1/5 using existing channels.tsv (SKIP_READ=1)"
else
    echo "1/5 read channel list from the TV"
    python3 -u "$DIR/tv_channels.py" list --tv "$TV" > channels.tsv.new
    [ "$(wc -l < channels.tsv.new)" -gt 20 ] || { echo "abort: channel list too short" >&2; exit 1; }
    mv channels.tsv.new channels.tsv
fi

echo "2/5 fetch KingOfSat Astra 19.2E"
if curl -s -m 60 -A "Mozilla/5.0" https://en.kingofsat.net/pos-19.2E -o kos.html.new \
   && [ "$(wc -c < kos.html.new)" -gt 500000 ]; then
    mv kos.html.new kos.html
else
    echo "warning: KingOfSat download failed, using the last copy" >&2
fi

echo "3/5 filter free German-language channels"
python3 "$DIR/kos_transponders.py" kos.html channels.tsv --guest > guest.tsv

echo "4/5 pick 50 and publish to tv.heissa.de"
python3 "$DIR/guest_selection.py" guest.tsv > selection.tsv
python3 "$DIR/guest_selection.py" guest.tsv --json > channels.json
cp channels.json "$OUT_JSON"

echo "5/5 PDF"
python3 "$DIR/channel_pdf.py" selection.tsv Senderliste_Gaeste.pdf
if [ "$1" = "--mail" ]; then
    python3 - "$MAILTO" <<'PY'
import sys, subprocess
from email.message import EmailMessage
m = EmailMessage()
m["To"], m["Subject"] = sys.argv[1], "Senderliste Gaeste Sharp-TV"
m.set_content("Senderliste fuer die Gaeste (Astra 19,2 Ost, frei, deutschsprachig D/AT/CH, max. 50).\n"
              "Standard: arte (TV), ANTENNE BAYERN (Radio).\nHandy im Haus-WLAN: https://tv.heissa.de\n")
m.add_attachment(open("Senderliste_Gaeste.pdf", "rb").read(), maintype="application",
                 subtype="pdf", filename="Senderliste_Gaeste.pdf")
subprocess.run(["/usr/sbin/sendmail", "-t"], input=m.as_bytes(), check=True)
PY
    echo "mailed to $MAILTO"
fi
echo "done: $WORK/Senderliste_Gaeste.pdf"
