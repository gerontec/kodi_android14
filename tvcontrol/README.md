# TV control over adb — channel list, pseudo hotel mode, guest list

Scripts for the Sharp 4K UHDTV (Google TV, Android 14, MediaTek MT9676, product `MT9676_Sharp`).
They should work on other Android 14 TVs with the MediaTek "OneWorld" Live TV
(`com.mediatek.tv.oneworld.tvcenter`) — adapt the German on-screen texts if your UI language differs.

Why screen-driven: on Android 14 the channel database is only readable by system apps
(`READ_EPG_DATA` is not grantable, `content query content://android.media.tv/channel` returns
nothing for the shell) and there is no export intent. The scripts therefore read the screen with
`uiautomator dump` and press keys with `input keyevent`. **Every step checks the expected
on-screen text first and aborts if it differs** — no blind clicking after a firmware update.

Requirements: `adb` on the controlling host, the host's adb key authorised on the TV,
TCP adb enabled once via USB: `adb tcpip 5555` (lost after a power cut, survives standby).

| Script | What it does |
|---|---|
| `tv_channel_init.py` | Deletes all channels and re-installs Astra 19.2°E with the pre-sorted operator list **Österreichliste** (Settings → Kanäle → Satellit → Kanalinstallationsmodus *Bevorzugter Satellit* → rescan). ~97 channels, ORF/ATV/ServusTV first, German public channels from 32 on. |
| `tv_channels.py list [--type T]` | Prints `number<TAB>name` of the Live TV list. `T`: `Alle Kanäle`, `Digital`, `Radio`, `Kostenlos`, `Verschlüsselt`, `Favoriten1..3`. |
| `tv_channels.py purge-encrypted [--yes]` | Ticks every channel of the *Verschlüsselt* filter in *Kanalverwaltung → Kanäle löschen*, verifies the ticked set equals the encrypted set, then deletes. Without `--yes` it backs out (dry run). |
| `kos_transponders.py page.html list.tsv` | Adds the transponder (MHz pol SR) per channel from a saved KingOfSat position page (`https://en.kingofsat.net/pos-19.2E`). |
| `channel_pdf.py list_tp.tsv out.pdf` | Guest channel list (German/English): favourites page + all channels, transponder in the right column. |
| `tvremote/` | PHP guest remote (tv.heissa.de): channel list + switching from the phone, see below. |
| `tv_restore.py backup` / `restore [--dry-run]` | Pseudo hotel mode: snapshot Android settings + Kodi config, put back every value that drifted, tune the default channel. |

## Re-create the sorted free channel list

```bash
TV=192.168.178.195:5555
python3 tv_channel_init.py --tv $TV --yes          # rescan, ~10 min, deletes the old list
python3 tv_channels.py purge-encrypted --tv $TV     # dry run: shows what would go
python3 tv_channels.py purge-encrypted --tv $TV --yes
python3 tv_channels.py list --tv $TV > channels.tsv
curl -s -A Mozilla/5.0 https://en.kingofsat.net/pos-19.2E -o kos.html
python3 kos_transponders.py kos.html channels.tsv > channels_tp.tsv
python3 channel_pdf.py channels_tp.tsv Senderliste_Gaeste.pdf
```

Watch the TV or follow the script output; it prints each step.

Timing (MT9676, one `uiautomator dump` ≈ 3 s): the scripts dump once per screen page and
send key sequences in one `input keyevent` call — full list read ≈ 85 s, purge with
tick + verify ≈ 2.5 min, scan ≈ 10 min.

## After every channel scan: rebuild guest list (web + PDF)

```bash
# on kellertreppe (adb access to the TV); ~8 min, mostly reading the TV list
/home/pi/tvrestore/update_guest_list.sh --mail
SKIP_READ=1 /home/pi/tvrestore/update_guest_list.sh   # reuse the last read list
```

Chain: `tv_channels.py list` → KingOfSat Astra 19.2E page → `kos_transponders.py --guest`
(free, German audio, country DE/AT/CH; radio rows have no country; allowlist for German-language
foreign channels like arte; no shopping/adult/test) → `guest_selection.py` (ranked, max 50:
32 TV + 18 radio; defaults **arte** and **ANTENNE BAYERN** shown bold) →
`/var/lib/tvremote/channels.json` (tv.heissa.de) + `Senderliste_Gaeste.pdf` (mailed via sendmail).

## Daily restore (pseudo hotel mode)

Active now: cron on kellertreppe `56 12 * * * /home/pi/tvrestore/tv_tune.sh 934` (Antenne Bayern).

The TV switches itself on at 12:55 and off at 13:00 (Settings → System → Stromversorgung &
Energie → Automatisch ein-/ausschalten). A cron job on an always-on host in the same LAN
restores the baseline in that window:

```cron
56 12 * * *  python3 /home/pi/tvrestore/tv_restore.py restore
```

`tv_restore.py backup` once after everything is set up the way guests should find it.
What it cannot restore: the channel list itself (not readable without root) — use
`tv_channel_init.py` + `purge-encrypted` for that.

## Guest remote (tvremote/)

`index.php` (Bootstrap 5, works on phones) lists `/var/lib/tvremote/channels.json` and switches
the TV via `sudo -u pi tv_tune.sh <number>` (sudoers allows exactly that script; digits only,
flock, max one switch per 3 s). Runs on an always-on LAN host (nginx + php-fpm, port 8090);
`tv.heissa.de` on the public server reverse-proxies to it over OpenVPN and drops any
client-supplied `X-Forwarded-For`. Allowed clients: home LAN IPv4, the current home IPv6 /64
and public IPv4 (`update_home_nets.sh`, cron every 10 min), VPN 10.8.0.0/24. Everyone else: 403.

## Firmware pitfalls found

- **Never tap the satellite entry under „Manuelle Satelliteneinstellung" in mode
  „Bevorzugter Satellit"** — it immediately starts an operator-list rescan and overwrites the
  current list. Switch to „Allgemeiner Satellit" first (switching the mode does not rescan).
- Delete view: the **yellow** key („Auswählen") ticks a row, OK does nothing; the confirm
  dialog buttons are TextViews „Abbrechen"/„Weiter"; the delete list does not wrap.
- An empty list type (e.g. „Verschlüsselt" after the purge) cannot be selected — treated as empty.
- Manual transponder scan (Manuelle Satelliteneinstellung, mode „Allgemeiner Satellit"):
  the symbol-rate EditText is not updated in `uiautomator dump` — check it by screenshot;
  `input text` works once the field is in edit mode. A manual scan restored the full Astra list.
- „Kanäle neu sortieren" has no criteria (it only renumbers); there is no "encrypted last" sort.

- Auto on/off: the rhythm dialog always shows the title „Einschaltzeit" and once wrote the
  *power-on* value when the *power-off* entry was selected — read the list back after every change.
- Time picker starts at the current time, minutes do not wrap below 00.
- Channel list: right after switching the list type nothing is focused; the first DPAD key
  only sets focus.
- `uiautomator dump` hangs while protected video is on screen in rare cases; use timeouts.
- Screenshots of live tuner video are blank (secure surface) — read the on-screen texts instead.
