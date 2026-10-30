#!/usr/bin/env python3
"""Build per-country IPTV lists for Kodi (pvr.iptvsimple) from the checked TVHeadend playlist.

  - working.m3u (alive from home) -> original stream URL, Kodi plays it directly
  - FRITZ!Box cable tuner (DVB-C via RTSP, LAN only) -> preferred for every channel it carries
  - raw_<cc>.m3u entries marked [Geo-blocked] -> URL through the country relay
    https://<cc>.heissa.de/<token>/<b64url>.m3u8 (hls_relay.py), only for countries with a relay

usage: make_country_m3u.py --iptv /home/pi/iptv --token-file token --out outdir
  writes outdir/<cc>/list.m3u for each country and outdir/de/all.m3u (all countries, grouped)
"""
import argparse
import base64
import os
import re
import urllib.request
from collections import defaultdict

RELAYS = {"ch", "at", "us"}          # countries with a working exit (it: no Privado tunnel yet)
LISTS = ["de", "at", "ch", "it", "us"]
NAMES = {"de": "Deutschland", "at": "Österreich", "ch": "Schweiz", "it": "Italia", "us": "USA"}
FRITZBOX = {"tvhd": "Kabel HD", "tvsd": "Kabel SD", "radio": "Kabel Radio"}
# shopping, adult and placeholder entries never go into a list
JUNK_NAME = re.compile(r"^\W*$|\b(QVC\w*|HSE\w*|Juwelo|1-2-3\.tv|Channel ?21|sonnenklar|Shop ?LC|Mediashop|"
                       r"Astro ?TV|Sex\w*|Erotik\w*|Babestation\w*|Teleshopping)\b", re.I)
JUNK_GROUP = re.compile(r"shop|adult|erotic|xxx", re.I)


def junk(info):
    name = info.rpartition(",")[2].strip()
    group = re.search(r'group-title="([^"]*)"', info)
    return bool(JUNK_NAME.search(name) or (group and JUNK_GROUP.search(group.group(1))))


def plain(name):
    """Comparable channel name: no resolution/status tags, no HD suffix."""
    name = re.sub(r"\s*[\[(][^\])]*[\])]", "", name.rpartition(",")[2])
    return re.sub(r"[^a-z0-9äöü]", "", re.sub(r"\bhd\b", "", name.lower()))


def fritzbox(base):
    """Cable channels from the FRITZ!Box m3u lists as (extinf, rtsp-url) in group order."""
    out = []
    for lst, group in FRITZBOX.items():
        try:
            text = urllib.request.urlopen(f"{base}/dvb/m3u/{lst}.m3u", timeout=15).read().decode("utf-8", "replace")
        except OSError as e:
            print(f"warning: FRITZ!Box list {lst} not available: {e}")
            continue
        info = None
        for line in text.splitlines():
            if line.startswith("#EXTINF"):
                info = line
            elif line.startswith("rtsp://") and info:
                name = info.rpartition(",")[2].strip()
                # public broadcasters switched SD off; the box still lists "ZDF SD" etc. from its last scan
                if not (lst == "tvsd" and name.endswith(" SD")) and not JUNK_NAME.search(name):
                    radio = ' radio="true"' if lst == "radio" else ""   # iptvsimple: radio section
                    out.append((f'#EXTINF:-1{radio} group-title="{group}",{name}', line.strip()))
                info = None
    return out


def entries(path):
    """Yield (extinf_line, url) pairs of an m3u file."""
    info = None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("#EXTINF"):
            info = line
        elif line and not line.startswith("#") and info:
            yield info, line
            info = None


def country(info, fallback=""):
    m = re.search(r'tvg-id="[^"@]*\.([a-z]{2})(?:@[^"]*)?"', info)
    return m.group(1) if m else fallback


def regroup(info, group):
    """Set group-title (Kodi shows it as channel group) and drop iptv-org status tags from the name."""
    info = re.sub(r'\s*group-title="[^"]*"', "", info)
    info = info.replace("#EXTINF:-1", '#EXTINF:-1 group-title="%s"' % group, 1)
    head, _, name = info.rpartition(",")
    name = re.sub(r"\s*\[(Geo-blocked|Not 24/7)\]", "", name, flags=re.I).strip()
    return head + "," + name


def b64(url):
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iptv", default="/home/pi/iptv")
    ap.add_argument("--token-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fritzbox", default="http://192.168.178.1", help="cable tuner base URL, '' to skip")
    a = ap.parse_args()
    token = open(a.token_file).read().strip()
    lists, seen = defaultdict(list), set()
    cable = fritzbox(a.fritzbox) if a.fritzbox else []
    on_cable = {plain(i) for i, _ in cable}

    for info, url in entries(os.path.join(a.iptv, "working.m3u")):
        cc = country(info)
        if junk(info):
            continue
        if cc in ("de", "at", "ch") and plain(info) in on_cable:
            continue                    # the cable tuner carries it: no internet copy
        if cc in LISTS and url not in seen:
            seen.add(url)
            lists[cc].append((regroup(info, NAMES[cc]), url))

    for cc in sorted(RELAYS):
        raw = os.path.join(a.iptv, f"raw_{cc}.m3u")
        if not os.path.exists(raw):
            continue
        for info, url in entries(raw):
            if "geo-blocked" in info.lower() and url not in seen and ".m3u8" in url and not junk(info):
                seen.add(url)
                relay = f"https://{cc}.heissa.de/{token}/{b64(url)}.m3u8"
                lists[cc].append((regroup(info, NAMES[cc] + " (geo)"), relay))

    def write(f, items, sort=True):
        for info, url in (sorted(items, key=lambda e: e[0].rpartition(",")[2].lower()) if sort else items):
            f.write(f"{info}\n{url}\n")

    for cc in LISTS:
        os.makedirs(os.path.join(a.out, cc), exist_ok=True)
        with open(os.path.join(a.out, cc, "list.m3u"), "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            if cc == "de":
                write(f, cable, sort=False)     # FRITZ!Box order = cable programme order
            write(f, lists[cc])
    with open(os.path.join(a.out, "de", "all.m3u"), "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        write(f, cable, sort=False)
        for cc in LISTS:
            write(f, lists[cc])
    print(f"cable (FRITZ!Box): {len(cable)} channels")
    for cc in LISTS:
        geo = sum(1 for _, u in lists[cc] if ".heissa.de/" in u)
        print(f"{cc}: {len(lists[cc])} channels ({geo} via relay)")


if __name__ == "__main__":
    main()
