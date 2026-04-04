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

## Kodi Web Interface

The Kodi web server must be enabled manually after first install:

**Kodi → Settings → Services → Control → Allow remote control via HTTP**

- URL: `http://192.168.178.43:8080`
- Username: `kodi`
- Password: `654321`
