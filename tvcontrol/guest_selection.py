#!/usr/bin/env python3
"""Pick at most 50 guest channels from the filtered list (kos_transponders.py --guest output).

usage: guest_selection.py guest.tsv > selection.tsv   (same columns, ranked: TV first, then radio)
       guest_selection.py guest.tsv --json > channels.json   (for tvremote; arte / Antenne Bayern = default)
"""
import json
import re
import sys

MAX_TOTAL = 50
DEFAULT = r"^ANTENNE BAYERN$|^arte HD$"       # radio default / TV default, shown bold

# ranked by importance for guests; regex on the TV's channel name, first matching channel wins
TV = [
    r"^arte HD$", r"^Das Erste HD$", r"^ZDF HD$", r"^BR Fernsehen S(ü|ue)d HD$", r"^3sat HD$",
    r"^phoenix HD$", r"^zdf_neo HD$", r"^ZDFinfo HD$", r"^ONE HD$", r"^tagesschau24 HD$",
    r"^RTL Television$|^RTL Austria$", r"^SAT\.1$|^SAT\.1 A$", r"^ProSieben$|^ProSieben Austria$",
    r"^VOX$|^VOX Austria$", r"^kabel eins$|^Kabel 1 Austria$", r"^RTLZWEI$|^RTLZWEI Austria$",
    r"^ntv$|^ntv Austria$", r"^WELT$", r"^N24 DOKU$", r"^ORF 2 EUROPE HD$", r"^KiKA HD$",
    r"^SUPER RTL", r"^DMAX$|^DMAX Austria$", r"^sixx", r"^TELE 5$", r"^kabel eins Doku$",
    r"^SAT\.1 Gold", r"^Pro7 MAXX", r"^NITRO$|^NITRO Austria$", r"^ARD alpha HD$",
    r"^münchen\.tv", r"^SPORT1$", r"^Eurosport 1 Deutschland$", r"^DELUXE MUSIC$",
    r"^SWR BW HD$", r"^hr-fernsehen HD$", r"^NDR FS HH HD$", r"^WDR HD Köln$",
]
RADIO = [
    r"^ANTENNE BAYERN$", r"^Bayern 1$", r"^BAYERN 3$", r"^BR24$", r"^Bayern 2$", r"^BR-KLASSIK$",
    r"^ROCK ANTENNE$", r"^OLDIE ANTENNE$", r"^Klassik Radio$", r"^BR Schlager$", r"^BR-Heimat$",
    r"^Dlf$", r"^Dlf Kultur$", r"^SWR3$", r"^ORF HITRADIO OE3$", r"^ORF FM4$", r"^ORF OE1$",
    r"^1LIVE$", r"^NDR 2", r"^WDR 2$", r"^sunshine live$", r"^Dlf Nova$",
]
MAX_RADIO = 18


def load(path):
    out = []
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 8 and p[0].isdigit():
            out.append(p)
    return out


def pick(rows, patterns, radio, limit):
    chosen = []
    for pat in patterns:
        m = next((r for r in rows if (r[7] == "1") == radio and re.search(pat, r[1], re.I)
                  and r not in chosen), None)
        if m:
            chosen.append(m)
        if len(chosen) >= limit:
            break
    return chosen


def main(path, as_json):
    rows = load(path)
    radio = pick(rows, RADIO, True, MAX_RADIO)
    tv = pick(rows, TV, False, MAX_TOTAL - len(radio))
    sel = tv + radio
    if as_json:
        json.dump([{"num": int(r[0]), "name": r[1], "radio": r[7] == "1", "tp": r[2],
                    "default": bool(re.search(DEFAULT, r[1]))} for r in sel],
                  sys.stdout, ensure_ascii=False)
    else:
        for r in sel:
            print("\t".join(r))
    print(f"selected {len(tv)} TV + {len(radio)} radio = {len(sel)}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], "--json" in sys.argv)
