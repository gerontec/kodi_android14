# Kodi Android 14 TV — Setup & Restore

Automated Kodi installation for **Sharp 4K UHDTV** running Android 14 / Google TV.  
Includes channel list (German HD, Austrian, Russian, international, radio) and master lock protection.

---

## Step 1 — Enable Developer Mode & ADB on the TV

You need to activate **USB Debugging** (network ADB) via the TV remote before running the install script.

### 1.1 Enable Developer Options

Using your remote control:

1. Press the **Home** button
2. Navigate to **Settings** (gear icon, top right)
3. Scroll down to **Device Preferences**
4. Select **About**
5. Scroll down to **Build** (or **Build number**)
6. Press **OK / Select** on the remote **7 times** in a row
   > After the 4th press you will see: *"You are X steps away from being a developer"*  
   > After the 7th press: *"You are now a developer!"*
7. Press **Back** to return to Device Preferences
8. **Developer options** now appears in the Device Preferences menu

### 1.2 Enable Network ADB (Wireless Debugging)

1. Go to **Settings → Device Preferences → Developer options**
2. Scroll to **USB debugging** → turn **ON**
3. Scroll to **Network debugging** (or **ADB over network**) → turn **ON**
   > A dialog may appear asking to allow ADB — confirm with **OK**
4. Note the IP address shown on screen (e.g. `192.168.178.43:5555`)

> **Note:** On some Sharp/Google TV builds the setting is called  
> *"Wireless debugging"* instead of *"Network debugging"* — enable it and use the shown IP/port.

### 1.3 Connect from your PC

Open a terminal on the PC that is on the same network as the TV:

```bash
adb connect 192.168.178.43:5555
adb devices   # should show the TV as "device"
```

A confirmation dialog may appear on the TV screen — select **Always allow** and press OK.

---

## Step 2 — Install / Restore Kodi

### Requirements

- Python 3.x
- ADB installed (`sudo apt install adb` or from [Android SDK](https://developer.android.com/tools/releases/platform-tools))
- Kodi installed on the TV (from Google Play Store)
- Kodi started at least once (to create its data directories)

### Clone the repository

```bash
git clone git@github.com:gerontec/kodi_android14.git
cd kodi_android14
```

### Run the install script

```bash
python3 install.py
# or with a specific TV IP:
python3 install.py 192.168.178.43
```

The script will automatically:
1. Connect to the TV via ADB
2. Start Kodi to initialize its directories
3. Copy the channel playlist to `/sdcard/Download/tvsd_filtered.m3u`
4. Write PVR IPTV Simple Client settings
5. Apply master lock (PIN: `1234`)
6. Restart Kodi and verify channels loaded

---

## What gets installed

| File | Description |
|------|-------------|
| `tvsd_filtered.m3u` | 150 TV channels + 106 radio stations |
| `pvr-instance-settings.xml` | PVR IPTV Simple Client configuration |
| `profiles.xml` | Kodi master lock (PIN protection) |

### Channel groups

| Group | Count |
|-------|-------|
| 🇩🇪 Deutschland HD | 22 (ARD, ZDF, arte, 3sat, Phoenix …) |
| 🇦🇹 Österreich | 2 (ORF 1, ORF 2) |
| 🇷🇺 Russland | 2 (Первый канал HD, TV BRICS) |
| 🇨🇳 China | 1 (CCTV+ 中国环球电视网) |
| 🇿🇦 Südafrika | 1 (Cape Town TV) |
| 🇫🇮 Suomi / Finland | 1 (MTV3) |
| 🇳🇿 New Zealand | 1 (Bravo NZ) |
| 🌍 International | 6 (BBC, Al Jazeera, CNN, CGTN, CNBC, euronews) |
| Sonstige | 8 |
| 📻 Radio | 106 |

> TV channels are streamed via the local **FritzBox DVB-C tuner** (`rtsp://192.168.178.1:554/…`).  
> The FritzBox must be reachable on the same network.

---

## Master Lock

Kodi settings and the addon manager are PIN-protected to prevent guest changes.

- **Default PIN:** `1234`
- To change: Kodi → Settings → System → Master lock → Change PIN

---

## Kodi Launcher — Source Selector App

`kodi_launcher.apk` (`de.gerontec.kodilauncher`) is a custom Android launcher app that serves two purposes:

1. **Boot auto-start** — starts Kodi automatically when the TV powers on
2. **Source selector** — when launched manually, shows a dialog to choose between Kodi and SAT/DVB-S

### Install

```bash
adb connect 192.168.178.43:5555
adb install kodi_launcher.apk
```

### Boot behaviour

The app registers a `BootReceiver` with priority 999 for `BOOT_COMPLETED`. When the TV powers on, Kodi starts automatically without any user interaction.

### Source selector dialog

When launched from the Google TV app grid (or any shortcut), the launcher shows:

```
┌──────────────┐
│   TV Quelle  │
├──────────────┤
│  Kodi        │
│  SAT / DVB-S │
└──────────────┘
```

- **Kodi** — launches `org.xbmc.kodi` directly
- **SAT / DVB-S** — opens the MediaTek TV Center in DVB-S satellite mode (Astra 19.2°E)
- **Back / Cancel** — closes the dialog, returns to previous app

The launcher activity uses `Theme.DeviceDefault.Dialog.Alert` so the dialog appears as a transparent overlay — fully navigable with the TV remote D-pad.

### Why not set as default HOME?

On Android 14 / Google TV, the built-in Google TV Launcher is a privileged system app with manifest priority 2. User-installed apps are capped at priority 0 and cannot override it without root. The **Home button always opens Google TV** — this is a platform restriction, not a bug.

The Kodi Launcher sits alongside Google TV as a launchable app. The boot-start via `BootReceiver` ensures Kodi is always the first thing visible after power-on regardless.

### Manifest priority

| App | Priority | Role |
|-----|----------|------|
| Google TV Launcher | 2 (system) | Home button target |
| `de.gerontec.kodilauncher` | 1 | Boot auto-start + source selector |
| FallbackHome | -1000 | Emergency fallback |

---

## Switching to SAT TV (Astra DVB-S)

The TV has a built-in DVB-S satellite tuner (Astra 19.2°E). There are two ways to switch to it:

### Via the Kodi Launcher (recommended)

Open the **Kodi Launcher** app from the Google TV home screen and select **SAT / DVB-S**.

### Via Kodi Favourites

1. In Kodi, open **Favourites** (star icon or via the menu)
2. Select **"SAT TV (Astra)"**

### How to return to Kodi

- Use the **app switcher** on the remote to switch back to Kodi directly
- Or press **Back** to reach the Google TV home screen, then relaunch Kodi

### Technical details

The DVB-S switch sends a MediaTek-specific intent with `tunerType=2` (preferred satellite):

```bash
adb shell am start \
  -a com.mediatek.tv.action.TUNER_TYPE \
  -n com.mediatek.tv.oneworld.tvcenter/.nav.TurnkeyUiMainActivity \
  --ei tunerType 2 \
  -f 0x10000000
```

| tunerType | Source |
|-----------|--------|
| 0 | DVB-T (antenna) |
| 1 | DVB-C (cable) |
| **2** | **DVB-S preferred satellite** |
| 3 | DVB-S general satellite |

TV Input ID for direct ADB use: `com.mediatek.dtv.tvinput.dvbtuner/.DvbsTvInputService/HW0`

---

## Kodi Web Interface

The Kodi web server must be enabled manually after first install:

**Kodi → Settings → Services → Control → Allow remote control via HTTP**

- URL: `http://192.168.178.43:8080`
- Username: `kodi`
- Password: `654321`
