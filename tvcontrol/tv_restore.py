#!/usr/bin/env python3
"""Pseudo hotel mode for the Sharp TV: snapshot a known-good config and put it back daily.

Runs on kellertreppe (same LAN as the TV, adb key authorised).
  tv_restore.py backup              save Android settings + Kodi config as the baseline
  tv_restore.py restore [--dry-run] write back every setting that drifted, restore Kodi, tune default
Cron (TV switches itself on at 12:55):  56 12 * * *  python3 /home/pi/tvrestore/tv_restore.py restore
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tarfile

TV = "192.168.178.195:5555"
BASE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(BASE, "baseline")
LOG = os.path.join(BASE, "restore.log")
KODI = "/sdcard/Android/data/org.xbmc.kodi/files/.kodi/userdata"
KODI_FILES = ["guisettings.xml", "favourites.xml", "sources.xml", "profiles.xml",
              "addon_data/pvr.hts"]
DEFAULT_CHANNEL = "934"   # ANTENNE BAYERN on Astra 19.2E

# values that change on their own or must never be rewritten
VOLATILE = re.compile(
    r"(boot_count|phenotype|timestamp|_time$|time_|uptime|count$|_count|ntp|wifi|bluetooth|ble_"
    r"|adb|android_id|ota|update|usage|last_|network|netstats|captive|mobile|data_roaming"
    r"|device_provisioned|user_setup|lock_screen|screensaver|zram|verifier|gms|checkin"
    r"|always_on_vpn|tether|nfc|location|airplane|sync|backup|install|package|dropbox|anr)", re.I)
NAMESPACES = ["global", "system", "secure"]


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def adb(*args, timeout=30):
    return subprocess.run(["adb", "-s", TV, *args], capture_output=True, text=True,
                          timeout=timeout).stdout


def connect():
    subprocess.run(["adb", "connect", TV], capture_output=True, timeout=15)
    if adb("shell", "echo ok").strip() != "ok":
        log("TV not reachable via adb (powered off, or adb port lost after power cut)")
        sys.exit(1)


def read_settings():
    out = {}
    for ns in NAMESPACES:
        out[ns] = {}
        for line in adb("shell", "settings", "list", ns).splitlines():
            k, sep, v = line.partition("=")
            if sep:
                out[ns][k] = v
    return out


def backup():
    connect()
    os.makedirs(BASELINE, exist_ok=True)
    with open(os.path.join(BASELINE, "settings.json"), "w") as f:
        json.dump(read_settings(), f, indent=1, sort_keys=True)
    kdir = os.path.join(BASELINE, "kodi")
    os.makedirs(kdir, exist_ok=True)
    for rel in KODI_FILES:
        # pull into the parent dir so files and dirs keep their names on repeated backups
        parent = os.path.join(kdir, os.path.dirname(rel))
        os.makedirs(parent, exist_ok=True)
        adb("pull", f"{KODI}/{rel}", parent + "/", timeout=60)
    with tarfile.open(os.path.join(BASE, f"baseline_{datetime.date.today()}.tgz"), "w:gz") as t:
        t.add(BASELINE, arcname="baseline")
    log(f"backup saved to {BASELINE}")


def restore(dry):
    connect()
    with open(os.path.join(BASELINE, "settings.json")) as f:
        want = json.load(f)
    have = read_settings()
    changed = 0
    for ns in NAMESPACES:
        for k, v in want[ns].items():
            if VOLATILE.search(k) or have[ns].get(k) == v:
                continue
            log(f"{'would set' if dry else 'set'} {ns} {k}: {have[ns].get(k)!r} -> {v!r}")
            if not dry:
                # null in the baseline means the key was unset
                if v == "null":
                    adb("shell", "settings", "delete", ns, k)
                else:
                    adb("shell", "settings", "put", ns, k, v)
            changed += 1
    log(f"settings: {changed} drifted value(s) {'found' if dry else 'restored'}")
    if dry:
        return
    # Kodi rewrites guisettings on exit, so stop it before pushing the baseline
    adb("shell", "am", "force-stop", "org.xbmc.kodi")
    for rel in KODI_FILES:
        src = os.path.join(BASELINE, "kodi", rel)
        if os.path.exists(src):
            target = f"{KODI}/{os.path.dirname(rel)}" if os.path.isdir(src) else f"{KODI}/{rel}"
            adb("push", src, target, timeout=60)
    log("kodi config restored")
    # live TV on the satellite tuner, then the default station by number
    adb("shell", "am", "start", "-a", "com.mediatek.tv.action.TUNER_TYPE",
        "-n", "com.mediatek.tv.oneworld.tvcenter/.nav.TurnkeyUiMainActivity",
        "--ei", "tunerType", "2", "-f", "0x10000000")
    subprocess.run(["sleep", "8"])
    for d in DEFAULT_CHANNEL:
        adb("shell", "input", "keyevent", f"KEYCODE_{d}")
    log(f"tuned DVB-S channel {DEFAULT_CHANNEL}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["backup", "restore"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    backup() if a.mode == "backup" else restore(a.dry_run)
