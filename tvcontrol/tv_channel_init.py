#!/usr/bin/env python3
"""Re-install the Sharp TV satellite channel list (Astra 19.2E, operator list "Österreichliste").

Drives the Google TV settings wizard over adb by on-screen text; every step checks the
expected text first and aborts if the screen differs, so a firmware change never makes it
click blindly. WARNING: the rescan deletes all installed channels.

usage: tv_channel_init.py [--tv 192.168.178.195:5555] [--yes]
"""
import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

TV = "192.168.178.195:5555"


def adb(*a, timeout=30):
    return subprocess.run(["adb", "-s", TV, *a], capture_output=True, text=True, timeout=timeout).stdout


def screen():
    """Visible nodes as (text, centre-x, centre-y)."""
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = adb("shell", "cat", "/sdcard/ui.xml")
    nodes = []
    for n in ET.fromstring(xml[xml.index("<?xml"):]).iter("node"):
        t = n.get("text")
        if t:
            x1, y1, x2, y2 = map(int, re.findall(r"\d+", n.get("bounds")))
            nodes.append((t, (x1 + x2) // 2, (y1 + y2) // 2))
    return nodes


def wait_for(text, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        nodes = screen()
        if any(text in t for t, _, _ in nodes):
            return nodes
        time.sleep(2)
    sys.exit(f"abort: '{text}' did not appear; screen shows {[t for t, _, _ in screen()][:12]}")


def tap(text, expect_after=None):
    nodes = wait_for(text)
    x, y = next((x, y) for t, x, y in nodes if t == text or text in t)
    print(f"tap '{text}'")
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(2)
    if expect_after:
        wait_for(expect_after)


def main():
    global TV
    ap = argparse.ArgumentParser()
    ap.add_argument("--tv", default=TV)
    ap.add_argument("--yes", action="store_true", help="really delete and rescan")
    a = ap.parse_args()
    TV = a.tv
    if not a.yes:
        sys.exit("refusing without --yes: the rescan deletes all installed channels")

    adb("shell", "am", "start", "-a", "android.settings.SETTINGS")
    time.sleep(3)
    tap("Kanäle & Eingänge")
    tap("Kanäle", expect_after="Satellit")
    adb("shell", "input", "keyevent", "DPAD_RIGHT")
    # operator list mode, then the full rescan
    tap("Kanalinstallationsmodus", expect_after="Bevorzugter Satellit")
    tap("Bevorzugter Satellit")
    tap("Satelliten werden noch einmal gesucht", expect_after="Dadurch werden alle")
    tap("OK", expect_after="Antennentyp")
    tap("Nächster Schritt", expect_after="Kanalliste auswählen")
    tap("Österreichliste", expect_after="LNB-Liste")
    wait_for("Astra1 19.2°E")
    tap("Nächster Schritt", expect_after="Kanalsuchlauf")
    tap("Suchlauf", expect_after="Suchlauf wird ausgeführt")

    # wait for the scan to finish (status line disappears)
    while True:
        texts = [t for t, _, _ in screen()]
        status = next((t for t in texts if t.startswith("Status")), None)
        if not status:
            break
        print(status, next((t for t in texts if "Kanäle:" in t), ""))
        time.sleep(20)
    print("scan finished; screen:", [t for t, _, _ in screen()][:15])


if __name__ == "__main__":
    main()
