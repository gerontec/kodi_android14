#!/usr/bin/env python3
"""Test: dispctl.so via ctypes — läuft lokal (x86) oder auf TV (ARM)"""

import ctypes, os, sys

SO_PATHS = [
    "/data/data/com.termux/files/home/dispctl.so",  # TV (Termux home, exec erlaubt)
    "/data/local/tmp/dispctl.so",                   # TV (fallback)
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "dispctl.so"),  # lokal
]

lib = None
for p in SO_PATHS:
    if os.path.exists(p):
        lib = ctypes.CDLL(p)
        print(f"Loaded: {p}")
        break

if not lib:
    print("FEHLER: dispctl.so nicht gefunden", file=sys.stderr)
    sys.exit(1)

lib.screen_off.restype     = ctypes.c_int
lib.screen_on.restype      = ctypes.c_int
lib.screen_saver.restype   = ctypes.c_int
lib.screen_state.restype   = ctypes.c_int
lib.launch_source.restype  = ctypes.c_int
lib.launch_source.argtypes = [ctypes.c_int]

print("\n=== dispctl ctypes Test ===")

rc = lib.screen_state()
print(f"screen_state()         → {rc} ({'ON' if rc==1 else 'OFF' if rc==0 else 'UNKNOWN'})")

rc = lib.screen_off()
print(f"screen_off()           → rc={rc}")

rc = lib.screen_on()
print(f"screen_on()            → rc={rc}")

rc = lib.launch_source(1)
print(f"launch_source(1=Kodi)  → rc={rc}")

rc = lib.launch_source(99)
print(f"launch_source(99=bad)  → rc={rc}")

print("\nOK" if True else "")
