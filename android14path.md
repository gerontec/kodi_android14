# Android 14 / Google TV — Sharp 4K UHDTV — Path Reference

Device: **Sharp 4K UHDTV** · SoC: **MediaTek MT9676PA** · Android 14 (SDK 34) · Google TV

---

## DVB-S / TV Input System

### TV Input IDs (TvInputManager)

Found via `adb shell dumpsys tv_input`:

| Input | ID | State |
|-------|----|-------|
| **DVB-S (Satellite)** | `com.mediatek.dtv.tvinput.dvbtuner/.DvbsTvInputService/HW0` | 0 |
| DVB-T (Antenna) | `com.mediatek.dtv.tvinput.dvbtuner/.DvbTvInputService/HW0` | 0 |
| DVB-C (Cable) | `com.mediatek.dtv.tvinput.dvbtuner/.DvbcTvInputService/HW0` | 0 |
| HDMI 1 | `com.mediatek.tis/.HdmiInputService/HW2` | 1 |
| HDMI 2 | `com.mediatek.tis/.HdmiInputService/HW3` | 1 |
| HDMI 3 | `com.mediatek.tis/.HdmiInputService/HW4` | 1 |
| HDMI 4 | `com.mediatek.tis/.HdmiInputService/HW5` | 1 |
| Analog | `com.mediatek.tis/.AnalogInputService/HW1` | 0 |
| Composite | `com.mediatek.tis/.CompositeInputService/HW6` | 2 |

### TV Center App

Package: `com.mediatek.tv.oneworld.tvcenter`  
APK: `/system_ext/priv-app/TvLivePlayer/TvLivePlayer.apk`  
Main Activity: `com.mediatek.tv.oneworld.tvcenter.nav.TurnkeyUiMainActivity`

### DVB-S Switch Intent (MediaTek-specific)

**Discovered by decompiling TvLivePlayer.apk** — strings in smali reveal:

```
DVB-T source(tunerType == 0): stop OpApp
DVB-C source(tunerType == 1): stop OpApp
DVB-S source(tunerType == 2): prefer Satellite
DVB-S source(tunerType == 3): general Satellite
```

Intent action: `com.mediatek.tv.action.TUNER_TYPE`  
Extra key: `tunerType` (integer)

```bash
adb shell am start \
  -a com.mediatek.tv.action.TUNER_TYPE \
  -n com.mediatek.tv.oneworld.tvcenter/.nav.TurnkeyUiMainActivity \
  --ei tunerType 2 \
  -f 0x10000000
```

Log confirmation (`adb logcat`):
```
TIFChannelDataHelp: resetCurrentChannelListId() serviceListType is SERVICE_LIST_TYPE_DVB_PREFERRED_SATELLITE
TurnkeyUiMainActivity: onNewIntent
```

**Note:** The standard Android TV approach (`android.intent.action.VIEW` with `android.media.tv.extra.INPUT_ID`) was tried first but did not switch the source correctly on this device. The MediaTek-specific `TUNER_TYPE` intent is required.

### Other useful TV Center intents

| Action | Purpose |
|--------|---------|
| `com.mediatek.tv.action.TUNER_TYPE` | Switch tuner source (use `--ei tunerType N`) |
| `android.mtk.intent.action.Setup_Source` | Source setup |
| `com.android.tv.action.VIEW_EPG_EU` | Open EPG (European) |
| `com.android.tv.action.VIEW_FVP` | Favourite program list |

---

## Launcher System

### Registered HOME activities (priority order)

Found via `adb shell pm query-activities -a android.intent.action.MAIN -c android.intent.category.HOME`:

| Priority | Package | Activity | State |
|----------|---------|----------|-------|
| 2 | `com.google.android.apps.tv.launcherx` | `home.HomeActivity` | enabled (system) |
| 1 | `com.google.android.tungsten.setupwraith` | `RecoveryActivity` | activity disabled |
| 1 | `de.gerontec.kodilauncher` | `LauncherActivity` | enabled (user) |
| -1000 | `com.android.tv.settings` | `system.FallbackHome` | enabled (system) |

### Default launcher

**Default (unchanged):** `com.google.android.apps.tv.launcherx` — Google TV Launcher  
Priority 2 as a privileged system app. Cannot be overridden by user-installed apps on Android 14 without root. `adb shell cmd package set-home-activity` reports success but has no effect when a higher-priority system launcher exists.

**Home button always opens Google TV Launcher** — platform restriction.

### Kodi Launcher APK

Package: `de.gerontec.kodilauncher`  
Source: `LauncherActivity.smali` + `BootReceiver.smali`

**Default (original):** LauncherActivity started Kodi directly and finished (Theme.NoDisplay, no UI).

**Changed:** LauncherActivity now shows a `AlertDialog` (Theme.DeviceDefault.Dialog.Alert) with two items:
- `Kodi` → starts `org.xbmc.kodi/.Splash`
- `SAT / DVB-S` → fires `TUNER_TYPE` intent with `tunerType=2`

BootReceiver unchanged — still auto-starts Kodi on `BOOT_COMPLETED` (priority 999).

---

## Sleep / Display Settings

### Default (as found)

```
stay_on_while_plugged_in = 3   ← kept screen always ON, sleep never activated
screen_off_timeout       = 3600000  (1h, was already set)
wifi_sleep_policy        = 2   (WiFi never sleeps — already correct)
sleep_timeout            = 1234567890  (no deep sleep)
```

### Changed

```bash
adb shell settings put global stay_on_while_plugged_in 0   # allow screen-off when plugged in
```

All other values left unchanged. Result: screen turns off after 1 hour (light sleep), network stays active, no deep suspend.

---

## ADB Quick Reference

```bash
# Connect
adb connect 192.168.178.43:5555

# List TV inputs
adb shell dumpsys tv_input | grep 'TvInputInfo'

# Show all home launchers with priority
adb shell pm query-activities -a android.intent.action.MAIN -c android.intent.category.HOME

# Show current default launcher
adb shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME

# Switch to DVB-S
adb shell am start -a com.mediatek.tv.action.TUNER_TYPE \
  -n com.mediatek.tv.oneworld.tvcenter/.nav.TurnkeyUiMainActivity \
  --ei tunerType 2 -f 0x10000000

# Check sleep settings
adb shell settings get global stay_on_while_plugged_in
adb shell settings get system screen_off_timeout
adb shell settings get global wifi_sleep_policy
```
