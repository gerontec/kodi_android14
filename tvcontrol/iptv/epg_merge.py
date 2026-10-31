#!/usr/bin/env python3
"""Merge XMLTV files (channels + programmes), write gzip for Kodi and a compact now/next JSON for the web.

usage: epg_merge.py a.xml [b.xml ...] out.xml.gz epg_now.json
"""
import datetime
import gzip
import json
import sys
import xml.etree.ElementTree as ET


def main(*args):
    *inputs, out_gz, out_json = args
    tv = ET.Element("tv", {"generator-info-name": "heissa epg (iptv-org grabber)"})
    channels, progs = {}, []
    for path in inputs:
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            continue
        for ch in root.findall("channel"):
            channels.setdefault(ch.get("id"), ch)
        progs += [p for p in root.findall("programme") if p.get("channel") in channels]
    tv.extend(channels.values())
    tv.extend(progs)
    with gzip.open(out_gz, "wb") as f:
        ET.ElementTree(tv).write(f, encoding="utf-8", xml_declaration=True)
    # now/next for the web: programmes overlapping the next 8 hours, per channel
    now = datetime.datetime.now(datetime.timezone.utc)
    soon = {}
    for p in progs:
        start = datetime.datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
        stop = datetime.datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
        if stop > now and start < now + datetime.timedelta(hours=8):
            title = (p.findtext("title") or "").strip()
            soon.setdefault(p.get("channel"), []).append([int(start.timestamp()), int(stop.timestamp()), title])
    for v in soon.values():
        v.sort()
    json.dump(soon, open(out_json, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(channels)} channels, {len(progs)} programmes, now/next for {len(soon)} channels")


if __name__ == "__main__":
    main(*sys.argv[1:])
