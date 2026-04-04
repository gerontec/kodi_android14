# Telegram on Kodi TV

Telegram is installed on the Sharp 4K Android TV as a communication client,
enabling incoming and outgoing voice/video calls directly on the TV screen.

---

## Installation

```bash
# Download official Telegram APK
wget -O /tmp/telegram.apk "https://telegram.org/dl/android/apk"

# Install via ADB
adb -s <TV_IP>:5555 install -r /tmp/telegram.apk
```

Package name: `org.telegram.messenger.web`

---

## Permissions

All permissions are granted silently via ADB — no on-screen dialog required:

```bash
PKG=org.telegram.messenger.web

adb shell pm grant $PKG android.permission.RECORD_AUDIO
adb shell pm grant $PKG android.permission.CAMERA
adb shell pm grant $PKG android.permission.READ_CONTACTS
adb shell appops set $PKG SYSTEM_ALERT_WINDOW allow
```

### Android 14 permission state after grant

| Permission | Mode | Effect |
|------------|------|--------|
| `RECORD_AUDIO` | foreground | Mic active during calls |
| `CAMERA` | foreground | Camera active during calls |
| `FOREGROUND_SERVICE_MICROPHONE` | declared | Mic stays active while call is running, even if screen dims |
| `FOREGROUND_SERVICE_CAMERA` | declared | Same for camera |
| `SYSTEM_ALERT_WINDOW` | allow | Incoming call overlay works over Kodi |

No system-level mic kill-switch (sensor_privacy) is active on this device.

---

## Login

Connect the USB keyboard to the TV, then:

1. Launch Telegram from Kodi Favourites → **Telegram**
2. Enter your phone number
3. Enter the SMS confirmation code
4. Done — incoming calls will ring on the TV even while Kodi is running

---

## Kodi Integration

Telegram is added to Kodi Favourites for quick launch (`favourites.xml`):

```xml
<favourite name="Telegram">StartAndroidActivity(org.telegram.messenger.web,,,)</favourite>
```

To launch Telegram from the command line:

```bash
adb shell am start -n org.telegram.messenger.web/org.telegram.messenger.LaunchActivity
```

---

## Status Notifications via Bot API

A Telegram bot (configured separately on the local network) can send
status messages to the TV owner using the Bot API:

```python
import urllib.request, json

def send_status(token, chat_id, text):
    body = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read()).get("ok")
```

Store `token` and `chat_id` in environment variables or a secrets file,
never in source code.

---

## Architecture

```
[Phone / PC]  ←──Telegram call──→  [Sharp TV]
                                       │
                              org.telegram.messenger.web
                              RECORD_AUDIO: foreground
                              SYSTEM_ALERT_WINDOW: allow
                                       │
                              Kodi running in background
                              (call overlay appears on top)
```

---

## Notes

- The TV has no built-in camera — video calls work audio-only unless a USB camera is connected
- The TV microphone hardware is available (`/dev/snd/pcmC*D*c` devices present)
- Google Assistant also uses the mic but does not block other apps from accessing it
- Telegram runs as a regular Android app; the Google TV HOME button still works normally
- After a TV reboot, Telegram stays installed but must be reopened manually for incoming calls
