# Kodi Android 14 TV — Setup & Restore

Automated Kodi installation for **Sharp 4K UHDTV** running Android 14 / Google TV.  
Includes channel list (German HD, Austrian, Russian, international, radio) and master lock protection.

---

> **Status 2026-10-30:** TVHeadend is removed from all hosts (kellertreppe, heissa, ipgate1) and pvr.hts is disabled — see
> [Guest house TV system](#guest-house-tv-system-2026-10-30) at the end.

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
| `pvr-instance-settings.xml` | PVR IPTV Simple Client configuration (M3U from kellertreppe, see Guest house TV system) |
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

---

## Guest house TV system (2026-10-30)

Everything below lives in [`tvcontrol/`](tvcontrol/) — details in
[tvcontrol/README.md](tvcontrol/README.md) (SAT, guest remote, restore) and
[tvcontrol/iptv/README.md](tvcontrol/iptv/README.md) (IPTV, relays, family access).

### Overview

| Address | What guests get | Source |
|---|---|---|
| `tv.heissa.de` = `sat.heissa.de` | 50 free German-language channels (DE/AT/CH, no shopping), defaults **arte** (39) / **ANTENNE BAYERN** (934) | Astra 19.2°E, built-in DVB-S tuner |
| `de.heissa.de` | FRITZ!Box cable (DVB-C via RTSP, preferred) + German IPTV | home connection |
| `at.` `ch.` `it.heissa.de` | Austrian / Swiss / Italian IPTV | geo-blocked ones via Privado country exits on ipgate1 |
| `us.heissa.de` | US IPTV | geo-blocked ones via the US IP of heissa |
| `fr.heissa.de` | French IPTV | all via ipgate1 directly (French IP) |
| `ru.heissa.de` | Russian IPTV, names in Latin script | all via the US IP of heissa (EU blocks some channels) |
| `https://tv.heissa.de/tv_all.pdf` | printable list, one section per address | rebuilt daily |

Every page is a phone-friendly Bootstrap list with search. **▶ Browser** plays the stream on the phone or
laptop (hls.js), **TV** plays it on the Sharp (Kodi JSON-RPC, home/VPN only). Players work too:
`mpv https://ru.heissa.de/list.m3u`.

### SAT (built-in tuner)
- Scripted channel list over adb, screen-driven (uiautomator + key events, every step checks the screen):
  `tv_channel_init.py` (rescan, Astra „Österreichliste"), `tv_channels.py list / purge-encrypted`
  (page-wise, list ≈ 85 s, purge ≈ 2.5 min), manual transponder scan for Antenne Bayern (12148 H 27500).
- `update_guest_list.sh`: TV list → KingOfSat data → free German-language filter → top 50 → web + PDF.
- Daily 12:56: TV switches itself on at 12:55, cron tunes Antenne Bayern (`tv_tune.sh 934`).

### IPTV (Kodi `pvr.iptvsimple`, no channel manager)
- TVHeadend removed; Kodi reads one M3U (`http://192.168.178.218:8090/m3u/de/all.m3u`), ~500 TV + 106 radio.
- `make_country_m3u.py`: per-country lists; cable channels win over internet copies; shopping, adult,
  placeholders and dead public-broadcaster SD entries removed.
- `hls_relay.py`: country HLS relay (token in the path, rewrites playlists, serves one variant ≤ 5 Mbit/s so
  Kodi opens in time). ipgate1 `10.9.0.1:18099` (CH/AT via Privado), heissa `127.0.0.1:18099` (US/RU).
- One download per channel: relay single-flight memory cache + Apache front cache — N viewers of one channel → one stream from the source.
- Daily 04:30 `iptv_daily.sh`: every channel streamed up to 60 s with ffmpeg; nothing arrives → removed from
  lists, frontend and PDF (first run: 375 alive, 241 dead). heissa pulls the lists at 05:30.

### Access and protection
- Home LAN / home IPv6 prefix / VPN: no login. Family worldwide: user `family` + 6-digit PIN
  (Apache Basic Auth); 3 wrong PINs → 10 min ban (fail2ban `iptv-auth`).
- More than 9 foreign IPs streaming within 15 min → every further IP banned for a day + mail
  (`iptv_share_guard.py`, fail2ban `iptv-share`).
- Lists carry the relay token and are never public; tokens and PIN are not in this repo.

### Capacity (measured)
heissa 600 Mbit/s → ~50 parallel relay streams (US/RU); Privado tunnel ~50 Mbit/s per country → ~10
different CH/AT channels at a time (same channel for many viewers costs one stream thanks to the cache).

### TV basics (Sharp 4K UHDTV, Android 14, MediaTek MT9676)
- ADB over LAN `192.168.178.195:5555` and OpenVPN `10.8.0.13:5555` (OpenVPN for Android, always-on);
  port 5555 is lost after a power cut → once `adb tcpip 5555` over USB.
- Auto power on 12:55 / off 13:00 (pseudo hotel mode window). Pitfalls of the firmware menus:
  see tvcontrol/README.md.
