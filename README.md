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

## Boot Behaviour — Kodi as Primary App

### How it works

`kodi_launcher.apk` is a minimal Android launcher that declares the `HOME` category in its manifest. It is installed on the TV and registered as the preferred HOME activity:

```bash
adb connect 192.168.178.43:5555
adb install kodi_launcher.apk
adb shell cmd package set-home-activity de.gerontec.kodilauncher/.LauncherActivity
```

When the TV **powers on**, Android resolves the HOME activity using the preferred-activity registry. Our launcher is selected, immediately starts Kodi, and exits — so Kodi is the first app the user sees after boot.

> **Note:** The **Home button** on the remote still navigates to the Google TV Launcher.  
> This is a Google TV restriction that cannot be bypassed without root access.  
> The Google TV home screen remains accessible via the Home button (lowest priority in practice — Kodi is primary at boot).

The `install.py` script handles the APK install and home-activity registration automatically.

---

## Switching to SAT TV (Astra DVB-S) from within Kodi

The TV has a built-in DVB-S satellite tuner (Astra 19.2°E via the satellite dish input).  
A shortcut to switch directly to the satellite tuner is available inside Kodi under **Favourites**.

### How to switch

1. In Kodi, open **Favourites** (star icon or via the menu)
2. Select **"SAT TV (Astra)"**
3. The MTK TV Center opens and switches to the DVB-S satellite input

### How to return to Kodi

- Press **Back** repeatedly until the Android home screen appears, then relaunch Kodi
- Or use the app switcher on the remote to switch back to Kodi directly

### Technical details

The favourite calls Android's `StartAndroidActivity` built-in:

```
StartAndroidActivity(com.mediatek.tv.oneworld.tvcenter,,,)
```

To switch to satellite from the command line:

```bash
adb shell am start -n com.mediatek.tv.oneworld.tvcenter/.nav.TurnkeyUiMainActivity
```

---

## Kodi Web Interface

The Kodi web server must be enabled manually after first install:

**Kodi → Settings → Services → Control → Allow remote control via HTTP**

- URL: `http://192.168.178.43:8080`
- Username: `kodi`
- Password: `654321`
