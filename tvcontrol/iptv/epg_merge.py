#!/usr/bin/env python3
"""Merge XMLTV files (channels + programmes), write gzip for Kodi and a compact guide JSON for the web.

Programmes starting more than 36 h after the build are dropped (Kodi and web).
JSON: {tvg-id: [[start, stop, title, meta], ...]} for that range (the pages pick the running one), meta = {d: description, i: image, y: year, g: genre, s: sub-title,
e: episode (S01E02), r: rating} with empty fields left out.

usage: epg_merge.py a.xml [b.xml ...] out.xml.gz epg_now.json
"""
import datetime
import gzip
import json
import sys
import xml.etree.ElementTree as ET

DESC_MAX = 400
AHEAD = datetime.timedelta(hours=36)   # never more guide than this into the future


def episode(p):
    """S01E02 from onscreen or xmltv_ns (0-based 'season.episode.part')."""
    for e in p.findall("episode-num"):
        if e.get("system") == "onscreen" and (e.text or "").strip():
            return e.text.strip()
    for e in p.findall("episode-num"):
        if e.get("system") == "xmltv_ns":
            se = [x.split("/")[0].strip() for x in (e.text or "").split(".")]
            if len(se) >= 2 and se[1].isdigit():
                return (f"S{int(se[0]) + 1:02d}" if se[0].isdigit() else "") + f"E{int(se[1]) + 1:02d}"
    return ""


def meta(p):
    desc = (p.findtext("desc") or "").strip()
    if len(desc) > DESC_MAX:
        desc = desc[:DESC_MAX].rsplit(" ", 1)[0] + " …"
    icon = p.find("icon")
    image = (icon.get("src") if icon is not None else "") or (p.findtext("image") or "").strip()
    genres = []
    for c in p.findall("category"):
        t = (c.text or "").strip()
        if t and t not in genres:
            genres.append(t)
    m = {"d": desc, "i": image, "y": (p.findtext("date") or "").strip()[:4],
         "g": ", ".join(genres[:2]), "s": (p.findtext("sub-title") or "").strip(), "e": episode(p),
         "r": (p.findtext("rating/value") or "").strip()}
    return {k: v for k, v in m.items() if v}


def main(*args):
    *inputs, out_gz, out_json = args
    tv = ET.Element("tv", {"generator-info-name": "heissa epg (iptv-org grabber)"})
    channels, progs = {}, []
    limit = datetime.datetime.now(datetime.timezone.utc) + AHEAD
    for path in inputs:
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            continue
        for ch in root.findall("channel"):
            channels.setdefault(ch.get("id"), ch)
        progs += [p for p in root.findall("programme") if p.get("channel") in channels
                  and datetime.datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z") < limit]
    tv.extend(channels.values())
    tv.extend(progs)
    with gzip.open(out_gz, "wb") as f:
        ET.ElementTree(tv).write(f, encoding="utf-8", xml_declaration=True)
    # guide for the web: everything not yet over within the 36 h (the pages pick the running programme)
    now = datetime.datetime.now(datetime.timezone.utc)
    soon = {}
    for p in progs:
        start = datetime.datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
        stop = datetime.datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
        if stop > now:
            title = (p.findtext("title") or "").strip()
            soon.setdefault(p.get("channel"), []).append([int(start.timestamp()), int(stop.timestamp()), title,
                                                          meta(p)])
    for v in soon.values():
        v.sort()
    json.dump(soon, open(out_json, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(channels)} channels, {len(progs)} programmes, guide for {len(soon)} channels")


if __name__ == "__main__":
    main(*sys.argv[1:])
