#!/bin/sh
# Daily IPTV maintenance on kellertreppe (cron 04:30, TV is off):
# build all candidate lists -> stream every channel up to 60 s -> rebuild lists without the dead ones
# -> Kodi/frontend lists + tv_all.pdf. heissa pulls the lists from http://10.8.0.6:8090/m3u/ at 05:30.
set -e
cd /home/pi/tvrestore
ARGS="--iptv /home/pi/iptv --token-file hls_relay.token --ru-alive probe_ru_us.tsv"
python3 make_country_m3u.py $ARGS --out m3u_candidates > /dev/null
python3 stream_check.py m3u_candidates/de/all.m3u dead.txt stream_check_report.tsv
python3 make_country_m3u.py $ARGS --dead dead.txt --out m3u
for c in de at ch it us ru; do cp m3u/$c/list.m3u /var/lib/tvremote/iptv_$c.m3u; done
chmod -R a+rX m3u
python3 tv_all_pdf.py guestlist/selection.tsv m3u tv_all.pdf > /dev/null
cp tv_all.pdf /var/www/tvremote/tv_all.pdf          # https://tv.heissa.de/tv_all.pdf (linked in both frontends)
echo "$(date '+%F %T') done: $(wc -l < dead.txt) dead"
