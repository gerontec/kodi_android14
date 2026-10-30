#!/usr/bin/env python3
"""Sharp TV (MediaTek Live TV) channel list tools over adb, driven by on-screen text.

  tv_channels.py list [--type Kostenlos|Verschlüsselt|Radio|...]   print number<TAB>name
  tv_channels.py purge-encrypted [--yes]                            delete all encrypted channels

Every step checks what is on screen; the purge only deletes after the ticked set equals the
encrypted set read from the list filter. Without --yes it ticks, verifies and backs out.
"""
import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

TV = "192.168.178.195:5555"
LIVE_TV = ["am", "start", "-a", "com.mediatek.tv.action.TUNER_TYPE",
           "-n", "com.mediatek.tv.oneworld.tvcenter/.nav.TurnkeyUiMainActivity",
           "--ei", "tunerType", "2"]


def adb(*a, timeout=30):
    return subprocess.run(["adb", "-s", TV, *a], capture_output=True, text=True, timeout=timeout).stdout


def key(*names, pause=0.6):
    # one adb call for a whole key sequence; the TV handles queued keyevents in order
    if names:
        adb("shell", "input", "keyevent", *names)
        time.sleep(pause)


def keys(name, count, pause=1.2):
    """Press one key `count` times in a single adb call."""
    if count > 0:
        key(*([name] * count), pause=pause)


def dump():
    # uiautomator occasionally hangs on the TV: kill it and retry
    for attempt in range(3):
        try:
            # dump and read back in one round trip
            xml = adb("shell", "uiautomator dump /sdcard/ui.xml >/dev/null && cat /sdcard/ui.xml", timeout=25)
            return ET.fromstring(xml[xml.index("<?xml"):])
        except (subprocess.TimeoutExpired, ValueError, ET.ParseError):
            adb("shell", "pkill", "-f", "uiautomator", timeout=10)
            time.sleep(2)
    sys.exit("abort: uiautomator dump failed 3 times")


def texts(root):
    return [n.get("text") for n in root.iter("node") if n.get("text")]


NUM_IDS = ("item_NumberTV", "channel_info_no")
NAME_IDS = ("item_NameTV", "channel_info_name")


def _rid(n):
    return n.get("resource-id") or ""


def rows(root):
    """Channel rows on screen: (number, name, checked, focused)."""
    parent = {c: p for p in root.iter("node") for c in p}
    out = []
    for n in root.iter("node"):
        if not _rid(n).endswith(NUM_IDS) or not (n.get("text") or "").isdigit():
            continue
        # the row is the nearest ancestor holding the checkbox/focus ("*_item_root"), max 3 levels up
        row = parent.get(n, n)
        for _ in range(3):
            if _rid(row).endswith("item_root") or parent.get(row) is None:
                break
            row = parent[row]
        name = next((k.get("text") for k in row.iter("node") if _rid(k).endswith(NAME_IDS)), "")
        chk = any(k.get("checked") == "true" for k in row.iter("node") if _rid(k).endswith("channel_info_check"))
        # focus sits on the row container or one level above it
        foc = any(x is not None and x.get("focused") == "true" for x in (row, parent.get(row))) \
            or any(k.get("focused") == "true" for k in row.iter("node"))
        y = int(re.findall(r"\d+", row.get("bounds") or "[0,0][0,0]")[1])
        out.append((y, int(n.get("text")), name, chk, foc))
    # screen order, top to bottom; the wrapping list may show 99 above 7
    return [r[1:] for r in sorted(out)]


def focused_number(root):
    f = [r for r in rows(root) if r[3]]
    return f[-1][0] if f else None


def in_list(root):
    return any(t.startswith(("Kanalliste", "Kanäle löschen")) for t in texts(root))


def live_tv_in_front():
    return "tvcenter" in adb("shell", "dumpsys window | grep mCurrentFocus")


def open_list():
    # BACK would leave Live TV, so only start it and wait for info banners to fade out
    for attempt in range(3):
        if not live_tv_in_front():
            adb("shell", *LIVE_TV)
        time.sleep(7)
        if in_list(dump()):
            return
        key("DPAD_CENTER")
        time.sleep(3)
        if in_list(dump()):
            return
    sys.exit("abort: channel list did not open")


def focused_text(root):
    f = [n.get("text") for n in root.iter("node") if n.get("focused") == "true" and n.get("text")]
    if f:
        return f[0]
    # focus may sit on a container; take the first text inside it
    for n in root.iter("node"):
        if n.get("focused") == "true":
            t = [k.get("text") for k in n.iter("node") if k.get("text")]
            if t:
                return t[0]
    return None


def choose_type(name):
    key("PROG_YELLOW")
    time.sleep(1)
    for _ in range(12):
        if focused_text(dump()) == name:
            break
        key("DPAD_DOWN")
    else:
        sys.exit(f"abort: type '{name}' not found")
    key("DPAD_CENTER")
    time.sleep(2)
    root = dump()
    if f"Kanalliste - {name}" in texts(root):
        return True
    if "Typ auswählen" in texts(root):
        # the TV does not open an empty list type; close the menu and report it as empty
        key("BACK")
        return False
    sys.exit(f"abort: list type '{name}' not active")


def pages(wrap):
    """Yield one screen dump per page; between pages the focus is stepped past the last visible row.
    wrap=True: the list wraps (Live TV list), stop when a page brings nothing new.
    wrap=False: non-wrapping list (delete view), start at the top, stop when the focus no longer moves."""
    if not wrap:
        keys("PROG_RED", 20, pause=1.5)          # page up to the top
        keys("DPAD_UP", 12, pause=1.5)
    seen, idle, last_focus = set(), 0, None
    for _ in range(60):
        root = dump()
        if not in_list(root):
            sys.exit("abort: list closed while walking (no further key presses)")
        vis = rows(root)
        f = focused_number(root)
        if f is None:                           # first key only sets focus
            key("DPAD_DOWN")
            continue
        pos = [f]                               # consumer may move the focus and report it here
        yield root, pos
        f = pos[0]
        new = {r[0] for r in vis} - seen
        seen |= {r[0] for r in vis}
        if wrap:
            idle = idle + 1 if not new else 0
            if idle >= 2:
                return
        else:
            if f == last_focus and not new:
                return
        last_focus = f
        order = [r[0] for r in vis]
        # step to the last visible row and one further, which scrolls a fresh page in
        steps = len(order) - order.index(f) if f in order else len(order)
        keys("DPAD_DOWN", steps)
    sys.exit("abort: list end not reached within 60 pages")


def read_list(type_name):
    open_list()
    if not choose_type(type_name):
        key("BACK")
        return {}
    result = {}
    for root, _ in pages(wrap=True):
        for n, name, _, _ in rows(root):
            result[n] = name
    key("BACK")
    return result


def purge_encrypted(really):
    enc = read_list("Verschlüsselt")
    print(f"encrypted: {len(enc)}", "; ".join(f"{n} {v}" for n, v in sorted(enc.items())))
    if not enc:
        return
    open_list()
    key("PROG_RED")
    time.sleep(2)
    for _ in range(8):
        if focused_text(dump()) == "Kanäle löschen":
            break
        key("DPAD_DOWN")
    else:
        sys.exit("abort: 'Kanäle löschen' not in channel management menu")
    key("DPAD_CENTER")
    time.sleep(2)
    if "Kanäle löschen" not in texts(dump()):
        sys.exit("abort: delete view did not open")
    ticked = set()
    for root, pos in pages(wrap=False):
        vis = rows(root)
        order = [r[0] for r in vis]
        cur = pos[0]
        for n, _, chk, _ in vis:
            if n in enc and n not in ticked and order.index(n) >= order.index(cur):
                keys("DPAD_DOWN", order.index(n) - order.index(cur))
                if not chk:
                    key("PROG_YELLOW")  # yellow = "Auswählen" toggles the tick; OK does nothing here
                ticked.add(n)
                cur = n
        pos[0] = cur
    # verify page-wise that the ticks on screen are exactly the encrypted set
    checked = set()
    for root, _ in pages(wrap=False):
        checked |= {n for n, _, chk, _ in rows(root) if chk}
    if checked != set(enc):
        sys.exit(f"abort: ticked {sorted(checked)} != encrypted {sorted(enc)}; nothing deleted (press BACK on TV)")
    print(f"ticked and verified: {sorted(checked)}")
    if not really:
        for _ in range(3):
            key("BACK")
        print("dry run: backed out without deleting")
        return
    key("PROG_BLUE")
    time.sleep(2)
    root = dump()
    print("confirm screen:", texts(root)[:8])
    # dialog buttons are TextViews here ("Abbrechen"/"Weiter"); skip the colour-key legend (channel_nav_*)
    btns = [n for n in root.iter("node") if n.get("text") in ("OK", "Ja", "Weiter", "Bestätigen")
            and "channel_nav" not in _rid(n)]
    if len(btns) != 1:
        sys.exit(f"abort: expected exactly one confirm button, found {[b.get('text') for b in btns]}; check the TV")
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", btns[0].get("bounds")))
    print(f"tap confirm '{btns[0].get('text')}'")
    adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
    time.sleep(3)
    left = read_list("Verschlüsselt")
    print(f"encrypted channels left: {len(left)}")


def main():
    global TV
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "purge-encrypted"])
    ap.add_argument("--type", default="Alle Kanäle")
    ap.add_argument("--tv", default=TV)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    TV = a.tv
    if a.cmd == "list":
        for n, name in sorted(read_list(a.type).items()):
            print(f"{n}\t{name}")
    else:
        purge_encrypted(a.yes)


if __name__ == "__main__":
    main()
