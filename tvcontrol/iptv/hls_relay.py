#!/usr/bin/env python3
"""Country HLS relay: fetches a stream through a country exit and rewrites playlists so that
segments come through the relay too.

  GET /<cc>/<token>/<b64url>[.ext]   cc = country key from EXITS, b64url = urlsafe base64 of the source URL

Playlist URIs are rewritten to sibling paths (<b64url>.ext), so the relay works behind a reverse proxy
that maps a host (ch.heissa.de) to /<cc>/. Fetching uses curl so SOCKS exits need no extra modules.

usage: hls_relay.py --bind 10.9.0.1 --port 8099 --token-file /etc/hls_relay.token \
                    --exit ch=socks5h://10.9.0.1:1041 --exit de=direct
"""
import argparse
import base64
import re
import subprocess
import sys
import threading
import time
import urllib.parse
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXITS = {}
TOKEN = ""
CHUNK = 64 * 1024
SEGMENT_TTL, PLAYLIST_TTL = 60, 1          # seconds a fetched body is shared with other viewers
CACHE_MAX = 400 * 1024 * 1024              # bytes kept in memory (LRU)


class SingleFlight:
    """Shared upstream fetches: the first request for a URL downloads it, concurrent and later
    requests within the TTL get the same bytes. N viewers of one channel = one upstream stream."""

    def __init__(self):
        self.lock = threading.Lock()
        self.inflight = {}                 # key -> Event
        self.store = OrderedDict()         # key -> (expires, body)
        self.size = 0

    def get(self, key, fetch, ttl_of):
        while True:
            with self.lock:
                hit = self.store.get(key)
                if hit and hit[0] > time.time():
                    self.store.move_to_end(key)
                    return hit[1], True
                ev = self.inflight.get(key)
                if ev is None:
                    ev = self.inflight[key] = threading.Event()
                    break
            ev.wait(45)                    # another request is fetching this URL
        try:
            body = fetch()
            if body is not None:
                with self.lock:
                    old = self.store.pop(key, None)
                    if old:
                        self.size -= len(old[1])
                    self.store[key] = (time.time() + ttl_of(body), body)
                    self.size += len(body)
                    while self.size > CACHE_MAX and self.store:
                        _, (_, b) = self.store.popitem(last=False)
                        self.size -= len(b)
            return body, False
        finally:
            with self.lock:
                self.inflight.pop(key, None)
            ev.set()


FLIGHT = SingleFlight()


def b64e(url):
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


def ext_of(url):
    m = re.search(r"\.(m3u8|ts|aac|mp4|m4s|vtt|key|mpd)(?:$|\?)", url, re.I)
    return "." + m.group(1).lower() if m else ""


def curl(url, exit_url):
    cmd = ["curl", "-s", "-L", "--fail", "--max-time", "30", "-A",
           "Mozilla/5.0 (X11; Linux x86_64) Kodi/21", url]
    if exit_url != "direct":
        cmd[1:1] = ["--proxy", exit_url]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


MAX_BW = 5_000_000   # long-haul relay: one variant up to 5 Mbit/s


def one_variant(playlist):
    """Reduce a master playlist to a single variant (best <= MAX_BW, else the lowest).
    Kodi's ffmpeg HLS demuxer probes every variant on open, which times out over the relay."""
    lines = playlist.splitlines()
    variants = [(int(re.search(r"BANDWIDTH=(\d+)", l).group(1)), i)
                for i, l in enumerate(lines) if l.startswith("#EXT-X-STREAM-INF") and "BANDWIDTH=" in l]
    if len(variants) < 2:
        return playlist
    fit = [v for v in variants if v[0] <= MAX_BW]
    keep = max(fit)[1] if fit else min(variants)[1]
    drop = {i for _, i in variants if i != keep}
    drop |= {i + 1 for i in drop}                      # the URI line after each dropped STREAM-INF
    return "\n".join(l for i, l in enumerate(lines) if i not in drop)


def rewrite(playlist, base):
    """Point every URI of an HLS playlist at the relay (sibling path, same directory)."""
    playlist = one_variant(playlist)
    out = []
    for line in playlist.splitlines():
        if line and not line.startswith("#"):
            absu = urllib.parse.urljoin(base, line.strip())
            out.append(b64e(absu) + ext_of(absu))
        elif 'URI="' in line:
            out.append(re.sub(r'URI="([^"]+)"',
                              lambda m: 'URI="%s%s"' % (b64e(urllib.parse.urljoin(base, m.group(1))),
                                                         ext_of(m.group(1))), line))
        else:
            out.append(line)
    return "\n".join(out) + "\n"


class Relay(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        parts = self.path.split("?")[0].strip("/").split("/")
        if len(parts) != 3 or parts[1] != TOKEN or parts[0] not in EXITS:
            return self.send_error(404)
        cc, enc = parts[0], re.sub(r"\.[a-z0-9]+$", "", parts[2])
        try:
            url = b64d(enc)
        except Exception:
            return self.send_error(400)
        if not url.startswith(("http://", "https://")):
            return self.send_error(400)
        def fetch():
            p = curl(url, EXITS[cc])
            body = p.stdout.read()
            return body if p.wait() == 0 and body else None

        body, shared = FLIGHT.get((cc, url), fetch,
                                  lambda b: PLAYLIST_TTL if b.lstrip().startswith(b"#EXTM3U") else SEGMENT_TTL)
        if body is None:
            return self.send_error(502, "upstream failed")
        if body.lstrip().startswith(b"#EXTM3U"):
            data = rewrite(body.decode("utf-8", "replace"), url).encode()
            ctype, cache = "application/vnd.apple.mpegurl", "public, max-age=2"
        else:
            data = body
            ctype = {".ts": "video/mp2t", ".aac": "audio/aac", ".mp4": "video/mp4", ".m4s": "video/iso.segment",
                     ".vtt": "text/vtt"}.get(ext_of(url), "application/octet-stream")
            cache = "public, max-age=60"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        # segments never change; front caches and other viewers reuse them
        self.send_header("Cache-Control", cache)
        self.send_header("X-Relay", "shared" if shared else "fetched")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    global TOKEN
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--token-file", required=True)
    ap.add_argument("--exit", action="append", default=[], help="cc=socks5h://host:port or cc=direct")
    a = ap.parse_args()
    TOKEN = open(a.token_file).read().strip()
    for e in a.exit:
        cc, _, target = e.partition("=")
        EXITS[cc] = target
    ThreadingHTTPServer((a.bind, a.port), Relay).serve_forever()


if __name__ == "__main__":
    main()
