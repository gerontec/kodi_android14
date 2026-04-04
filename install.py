#!/usr/bin/env python3
"""
Kodi Android 14 TV - Install / Restore Script
Installiert Senderliste, PVR-Einstellungen und Masterlock auf Sharp 4K TV.

Verwendung:
    python3 install.py [TV_IP]
    python3 install.py 192.168.178.43      # Standard-IP
"""

import subprocess
import sys
import time
import os
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TV_IP      = sys.argv[1] if len(sys.argv) > 1 else "192.168.178.43"
ADB_PORT   = 5555
ADB_TARGET = f"{TV_IP}:{ADB_PORT}"
KODI_PKG   = "org.xbmc.kodi"
KODI_DATA  = f"/sdcard/Android/data/{KODI_PKG}/files/.kodi"
PLAYLIST_REMOTE = "/sdcard/Download/tvsd_filtered.m3u"

KODI_USER = "kodi"
KODI_PASS = "654321"
KODI_PORT = 8080

FILES = {
    "playlist":  "tvsd_filtered.m3u",
    "pvr":       "pvr-instance-settings.xml",
    "profiles":  "profiles.xml",
}


def run(cmd, check=True, capture=True):
    r = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"Fehler: {cmd}\n{r.stderr}")
    return r.stdout.strip()


def adb(cmd, check=True):
    return run(f"adb -s {ADB_TARGET} {cmd}", check=check)


def step(msg):
    print(f"\n{'='*55}\n  {msg}\n{'='*55}")


def wait_for_kodi_webserver(timeout=45):
    url = f"http://{KODI_USER}:{KODI_PASS}@{TV_IP}:{KODI_PORT}/jsonrpc"
    payload = b'{"jsonrpc":"2.0","method":"JSONRPC.Ping","id":1}'
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as r:
                if b"pong" in r.read():
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def kodi_rpc(method, params=None):
    import json
    url = f"http://{KODI_USER}:{KODI_PASS}@{TV_IP}:{KODI_PORT}/jsonrpc"
    body = json.dumps({"jsonrpc": "2.0", "method": method,
                       "params": params or {}, "id": 1}).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def check_files():
    step("Prüfe lokale Dateien")
    ok = True
    for key, fname in FILES.items():
        path = os.path.join(SCRIPT_DIR, fname)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  OK  {fname}  ({size} Bytes)")
        else:
            print(f"  FEHLT  {fname}")
            ok = False
    if not ok:
        sys.exit("Abbruch: Dateien fehlen.")


def connect_adb():
    step(f"ADB verbinden mit {ADB_TARGET}")
    run(f"adb connect {ADB_TARGET}", check=False)
    time.sleep(2)
    devices = run("adb devices")
    if ADB_TARGET not in devices:
        sys.exit(f"Gerät {ADB_TARGET} nicht erreichbar. ADB aktiviert?")
    model = adb("shell getprop ro.product.model", check=False)
    print(f"  Verbunden: {model}")


def start_kodi():
    step("Starte Kodi")
    adb(f"shell monkey -p {KODI_PKG} -c android.intent.category.LAUNCHER 1",
        check=False)
    print("  Warte auf Kodi-Start (15s)...")
    time.sleep(15)


def check_kodi_dirs():
    step("Prüfe Kodi-Verzeichnisse")
    result = adb(f"shell ls {KODI_DATA}/userdata/ 2>/dev/null", check=False)
    if "addon_data" not in result:
        print("  Verzeichnisse noch nicht vorhanden — warte weitere 10s...")
        time.sleep(10)
        result = adb(f"shell ls {KODI_DATA}/userdata/ 2>/dev/null", check=False)
        if "addon_data" not in result:
            sys.exit("Kodi-Verzeichnisse nicht gefunden. Kodi einmal manuell starten.")
    print("  Kodi-Verzeichnisse vorhanden.")


def push_playlist():
    step("Playlist auf TV kopieren")
    src = os.path.join(SCRIPT_DIR, FILES["playlist"])
    adb(f"push {src} {PLAYLIST_REMOTE}")
    lines = open(src, encoding="utf-8").read().count("#EXTINF")
    print(f"  {lines} Sender kopiert → {PLAYLIST_REMOTE}")


def push_pvr_settings():
    step("PVR IPTV Simple Einstellungen schreiben")
    pvr_dir = f"{KODI_DATA}/userdata/addon_data/pvr.iptvsimple"
    adb(f"shell mkdir -p {pvr_dir}", check=False)
    src = os.path.join(SCRIPT_DIR, FILES["pvr"])
    dst = f"{pvr_dir}/instance-settings-1.xml"
    with open(src, "rb") as f:
        content = f.read()
    proc = subprocess.Popen(
        ["adb", "-s", ADB_TARGET, "shell", f"cat > '{dst}'"],
        stdin=subprocess.PIPE
    )
    proc.communicate(input=content)
    print(f"  PVR-Einstellungen geschrieben.")


def push_profiles():
    step("Masterlock (profiles.xml) schreiben")
    dst = f"{KODI_DATA}/userdata/profiles.xml"
    src = os.path.join(SCRIPT_DIR, FILES["profiles"])
    with open(src, "rb") as f:
        content = f.read()
    proc = subprocess.Popen(
        ["adb", "-s", ADB_TARGET, "shell", f"cat > '{dst}'"],
        stdin=subprocess.PIPE
    )
    proc.communicate(input=content)
    print("  Masterlock-PIN 1234 gesetzt (Einstellungen + Addon-Manager gesperrt).")


def restart_kodi():
    step("Kodi neu starten")
    # Try graceful quit via JSON-RPC if web server is up
    try:
        kodi_rpc("Application.Quit")
        print("  Kodi beendet (JSON-RPC).")
        time.sleep(4)
    except Exception:
        adb(f"shell am force-stop {KODI_PKG}", check=False)
        time.sleep(2)
    adb(f"shell monkey -p {KODI_PKG} -c android.intent.category.LAUNCHER 1",
        check=False)
    print("  Warte auf Kodi + Webserver...")
    if wait_for_kodi_webserver():
        print("  Kodi läuft und Webserver antwortet.")
    else:
        print("  Webserver nicht erreichbar — bitte Kodi manuell prüfen.")


def verify():
    step("Verifizierung")
    try:
        result = kodi_rpc("PVR.GetChannels",
                          {"channelgroupid": "alltv", "properties": ["channelname"]})
        channels = result.get("result", {}).get("channels", [])
        print(f"  PVR meldet {len(channels)} Sender geladen.")
        if channels:
            for ch in channels[:5]:
                print(f"    • {ch['channelname']}")
            if len(channels) > 5:
                print(f"    ... +{len(channels)-5} weitere")
    except Exception as e:
        print(f"  PVR-Abfrage nicht möglich: {e}")
        print("  (Normal — Sender laden evtl. noch.)")


def main():
    print(f"""
╔══════════════════════════════════════════════╗
║  Kodi Android 14 TV — Install / Restore      ║
║  Ziel: {ADB_TARGET:<38}║
╚══════════════════════════════════════════════╝
""")
    check_files()
    connect_adb()
    start_kodi()
    check_kodi_dirs()
    push_playlist()
    push_pvr_settings()
    push_profiles()
    restart_kodi()
    verify()

    print(f"""
╔══════════════════════════════════════════════╗
║  Installation abgeschlossen!                 ║
║                                              ║
║  Masterlock PIN:  1234                       ║
║  Kodi Webserver:  http://{TV_IP}:{KODI_PORT}    ║
║  Kodi Login:      {KODI_USER} / {KODI_PASS}              ║
║                                              ║
║  Senderliste: {PLAYLIST_REMOTE:<32}║
╚══════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
