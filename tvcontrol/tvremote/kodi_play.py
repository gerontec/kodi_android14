#!/usr/bin/env python3
"""Play entry N of the de.heissa.de IPTV list in Kodi on the Sharp TV (runs as pi: adb key owner).

usage: kodi_play.py N [CC]   (N = 0-based index into /var/lib/tvremote/iptv_<CC>.m3u, CC default de)
"""
import base64
import json
import subprocess
import sys
import time
import urllib.request

TV = "192.168.178.195:5555"
KODI = "http://192.168.178.195:8080/jsonrpc"
AUTH = "Basic " + base64.b64encode(b"kodi:654321").decode()
LIST = "/var/lib/tvremote/iptv_{}.m3u"


def rpc(method, params=None):
    req = urllib.request.Request(KODI, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                                 "params": params or {}}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": AUTH})
    return json.load(urllib.request.urlopen(req, timeout=10))


def channels(cc):
    out, name = [], None
    for line in open(LIST.format(cc), encoding="utf-8"):
        line = line.strip()
        if line.startswith("#EXTINF"):
            name = line.rpartition(",")[2]
        elif line and not line.startswith("#") and name:
            out.append((name, line))
            name = None
    return out


def kodi_up():
    try:
        return rpc("JSONRPC.Ping").get("result") == "pong"
    except OSError:
        return False


def main():
    n = int(sys.argv[1])
    cc = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ("de", "at", "ch", "it", "us", "ru", "fr") else "de"
    name, url = channels(cc)[n]
    if not kodi_up():
        subprocess.run(["adb", "connect", TV], capture_output=True, timeout=15)
        subprocess.run(["adb", "-s", TV, "shell", "monkey", "-p", "org.xbmc.kodi", "-c",
                        "android.intent.category.LEANBACK_LAUNCHER", "1"], capture_output=True, timeout=20)
        for _ in range(20):
            time.sleep(2)
            if kodi_up():
                break
        else:
            sys.exit("Kodi did not start")
    r = rpc("Player.Open", {"item": {"file": url}})
    if r.get("result") != "OK":
        sys.exit(f"Kodi: {r}")
    print(name)


if __name__ == "__main__":
    main()
