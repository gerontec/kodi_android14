#!/usr/bin/env python3
"""Map channel names to their Astra 19.2E transponder from a saved KingOfSat position page.

usage: kos_transponders.py kos_pos-19.2E.html channels.tsv > channels_tp.tsv
       (adds a 3rd column "12149 H 27500" per channel; empty when not found)
"""
import html
import re
import sys


def transponders(page):
    """{normalised channel name: 'freq pol SR'} in page order (first hit wins)."""
    out, tp = {}, None
    # transponder header, then channel links: the TV shows the service name from title="Id: ..."
    token = re.compile(r'<td class="bld">(\d+)(?:\.\d+)? ([HV])</td>.*?<td><a class="bld">(\d+)</a></td>'
                       r'|<a ([^>]*class="A\d"[^>]*)>([^<]*)</a>', re.S | re.I)
    for m in token.finditer(page):
        if m.group(1):
            tp = f"{m.group(1)} {m.group(2)} {m.group(3)}"
        elif tp:
            sid = re.search(r'title="Id: ([^"]*)"', m.group(4))
            for name in (sid.group(1) if sid else None, m.group(5)):
                if name:
                    out.setdefault(norm(html.unescape(name)), tp)
    return out


def norm(s):
    return re.sub(r"[^a-z0-9äöü]", "", s.lower())


def main(page_path, tsv_path):
    tps = transponders(open(page_path, encoding="utf-8", errors="replace").read())
    for line in open(tsv_path, encoding="utf-8"):
        num, _, name = line.rstrip("\n").partition("\t")
        print(f"{num}\t{name}\t{tps.get(norm(name), '')}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
