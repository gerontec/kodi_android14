#!/usr/bin/env python3
"""Stream every channel of an M3U up to 60 s with ffmpeg; channels that deliver nothing are dead.

A channel counts as alive as soon as ALIVE_BYTES of media arrived (early stop saves relay bandwidth);
it is dead when less than DEAD_BELOW bytes arrive within 60 s. FRITZ!Box RTSP channels are tested
at most CABLE_PARALLEL at a time (few cable tuners). Relay URLs are tested end to end, exactly as Kodi
plays them; the report names the source URL behind a relay.

usage: stream_check.py all.m3u dead.txt report.tsv
"""
import base64
import concurrent.futures as cf
import re
import subprocess
import sys
import threading
import time

LIMIT_S = 60
ALIVE_BYTES = 512 * 1024      # enough for a radio stream (~30 s at 128 kbit/s) or a few TV seconds
DEAD_BELOW = 64 * 1024
PARALLEL = 12
CABLE_PARALLEL = 2
cable_slots = threading.Semaphore(CABLE_PARALLEL)


def source_url(url):
    """Original stream URL behind a heissa relay URL (https://<cc>.heissa.de/<token>/<b64>.ext)."""
    m = re.match(r"https://[a-z]{2}\.heissa\.de/[^/]+/([A-Za-z0-9_-]+)(?:\.\w+)?$", url)
    if not m:
        return url
    s = m.group(1)
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


def probe(url):
    # RTSP (FRITZ!Box cable): UDP only (TCP -> 461), and the socket timeout option is -timeout;
    # -rw_timeout is unknown for rtsp and made every cable channel look dead
    opts = (["-rtsp_transport", "udp", "-timeout", "20000000"] if url.startswith("rtsp://")
            else ["-rw_timeout", "20000000"])
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", *opts,
           "-i", url, "-t", str(LIMIT_S), "-map", "0:v?", "-map", "0:a?", "-c", "copy", "-f", "mpegts", "pipe:1"]
    got, start = 0, time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while time.time() - start < LIMIT_S + 15:
            chunk = p.stdout.read1(65536) if hasattr(p.stdout, "read1") else p.stdout.read(65536)
            if not chunk:
                break
            got += len(chunk)
            if got >= ALIVE_BYTES:
                break
    finally:
        p.kill()
        p.wait()
    return got, round(time.time() - start, 1)


def check(entry):
    name, url = entry
    if url.startswith("rtsp://"):
        with cable_slots:
            got, secs = probe(url)
    else:
        got, secs = probe(url)
    return name, url, got, secs


def entries(path):
    out, name = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("#EXTINF"):
            name = line.rpartition(",")[2]
        elif line and not line.startswith("#") and name:
            out.append((name, line))
            name = None
    return out


def main(m3u, dead_path, report_path):
    todo = list({url: (name, url) for name, url in entries(m3u)}.values())
    print(f"checking {len(todo)} channels, up to {LIMIT_S}s each", flush=True)
    dead, rows = [], []
    with cf.ThreadPoolExecutor(PARALLEL) as ex:
        for name, url, got, secs in ex.map(check, todo):
            ok = got >= DEAD_BELOW
            rows.append(f"{'OK' if ok else 'DEAD'}\t{got}\t{secs}\t{name}\t{source_url(url)}")
            if not ok:
                dead.append(source_url(url))
    open(report_path, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    open(dead_path, "w", encoding="utf-8").write("\n".join(sorted(set(dead))) + ("\n" if dead else ""))
    print(f"alive {len(rows) - len(dead)}, dead {len(dead)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
