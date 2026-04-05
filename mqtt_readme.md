# dispctl — Android TV Display Control via MQTT

Native ARMv7 binary für Android 14 TV (Sharp/Kodi).  
Kein Root erforderlich. Läuft als ADB-Shell-User.

## Features

- Bildschirm **ein / aus / toggle / screensaver**
- **MQTT-Daemon** mit Auto-Reconnect
- Status-Report alle **5 Minuten** automatisch
- Termux:Boot Integration für Autostart nach Reboot

## Installation

```bash
# Binary auf TV pushen (ADB WiFi Port 44401)
adb connect 192.168.178.43:44401
adb push dispctl_arm /data/local/tmp/dispctl
adb shell chmod +x /data/local/tmp/dispctl
```

## CLI-Verwendung

```bash
adb shell /data/local/tmp/dispctl --on
adb shell /data/local/tmp/dispctl --off
adb shell /data/local/tmp/dispctl --toggle
adb shell /data/local/tmp/dispctl --saver
adb shell /data/local/tmp/dispctl --status
```

## MQTT-Daemon starten

```bash
adb shell "/data/local/tmp/dispctl --mqtt 192.168.178.218 tv/display &"
```

### Topics

| Topic | Richtung | Payload |
|---|---|---|
| `tv/display/set` | Subscribe | `ON` / `OFF` / `TOGGLE` / `SAVER` / `STATUS` |
| `tv/display/state` | Publish | `ON` / `OFF` |

Status wird automatisch alle 5 Minuten gepublished.

### Beispiele

```bash
mosquitto_pub -h 192.168.178.218 -t tv/display/set -m OFF
mosquitto_pub -h 192.168.178.218 -t tv/display/set -m ON
mosquitto_pub -h 192.168.178.218 -t tv/display/set -m STATUS
mosquitto_sub -h 192.168.178.218 -t tv/display/state
```

## Autostart via Termux:Boot

In Termux-Terminal einmalig eingeben:

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/dispctl.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 8
while true; do
    /data/local/tmp/dispctl --mqtt 192.168.178.218 tv/display >> /data/local/tmp/dispctl.log 2>&1
    sleep 5
done
EOF
chmod +x ~/.termux/boot/dispctl.sh
```

Benötigt: **Termux** + **Termux:Boot** (beide von F-Droid)

## Build

```bash
sudo apt install gcc-arm-linux-gnueabi
arm-linux-gnueabi-gcc -O2 -static -march=armv7-a -mfloat-abi=softfp dispctl.c -o dispctl_arm
```

## Technische Details

- Screen-Control via `input keyevent KEYCODE_SLEEP / KEYCODE_WAKEUP`
- Screen-Status via `dumpsys power` → `mWakefulness=Awake`
- MQTT: minimale eigene Implementierung, keine externe Library
- ADB WiFi Port: `44401` (Android 14 dynamisch vergeben, per nmap ermitteln)
