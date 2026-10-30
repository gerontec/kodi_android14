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
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXITS = {}
TOKEN = ""
CHUNK = 64 * 1024


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
        p = curl(url, EXITS[cc])
        head = p.stdout.read(CHUNK)
        if not head and p.wait() != 0:
            return self.send_error(502, "upstream failed")
        if head.lstrip().startswith(b"#EXTM3U"):
            body = head + p.stdout.read()
            p.wait()
            data = rewrite(body.decode("utf-8", "replace"), url).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(200)
        ctype = {".ts": "video/mp2t", ".aac": "audio/aac", ".mp4": "video/mp4", ".m4s": "video/iso.segment",
                 ".vtt": "text/vtt"}.get(ext_of(url), "application/octet-stream")
        self.send_header("Content-Type", ctype)
        self.end_headers()
        try:
            while head:
                self.wfile.write(head)
                head = p.stdout.read(CHUNK)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            p.kill()


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
