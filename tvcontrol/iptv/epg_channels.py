#!/usr/bin/env python3
"""channels.xml for the iptv-org EPG grabber: every channel of our country lists that has a guide,
one source site per channel (by preference), xmltv_id = our tvg-id so Kodi and the web pages match.

usage: epg_channels.py [--rank N] [--skip ids.txt] guides.json out.channels.xml list.m3u [list.m3u ...]
  --rank N   use the N-th best site of each channel (second pass for channels the first site missed)
  --skip     file with tvg-ids that already have programmes
"""
import html
import json
import re
import sys

# preferred guide sites (first match wins); others are used if nothing preferred exists
PREFER = ["tv.mail.ru", "epg.iptvx.one", "i.mjh.nz", "plex.tv", "xumo.tv", "tv.sfr.fr",
          "chaines-tv.orange.fr", "web.magentatv.de", "sky.com"]


def main(guides_path, out_path, *lists, rank=0, skip=()):
    guides = {}
    for g in json.load(open(guides_path, encoding="utf-8")):
        ch = (g.get("channel") or "").lower()
        if ch and g.get("site") and g.get("site_id"):
            guides.setdefault(ch, []).append(g)
    ids = {}
    for path in lists:
        for m in re.finditer(r'tvg-id="([^"]+)"[^\n]*,(.*)', open(path, encoding="utf-8").read()):
            ids.setdefault(m.group(1), m.group(2).strip())
    rows, missing = [], 0
    for tvg_id, name in sorted(ids.items()):
        if tvg_id in skip:
            continue
        cands = guides.get(tvg_id.lower().split("@")[0], [])
        cands = sorted({c["site"]: c for c in cands}.values(),
                       key=lambda c: PREFER.index(c["site"]) if c["site"] in PREFER else len(PREFER))
        if len(cands) <= rank:
            missing += 1
            continue
        g = cands[rank]
        rows.append(f'  <channel site="{g["site"]}" lang="{g.get("lang", "en")}" '
                    f'xmltv_id="{html.escape(tvg_id)}" site_id="{html.escape(g["site_id"])}">'
                    f'{html.escape(name)}</channel>')
    with open(out_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<channels>\n' + "\n".join(rows) + "\n</channels>\n")
    print(f"{len(rows)} channels with a guide, {missing} without")


if __name__ == "__main__":
    args, rank, skip = sys.argv[1:], 0, set()
    while args and args[0].startswith("--"):
        opt, val = args.pop(0), args.pop(0)
        if opt == "--rank":
            rank = int(val)
        elif opt == "--skip":
            skip = set(open(val, encoding="utf-8").read().split())
    main(*args, rank=rank, skip=skip)
