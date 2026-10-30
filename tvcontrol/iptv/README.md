# IPTV per country (Kodi pvr.iptvsimple, no channel manager)

TVHeadend was removed (2026-10-30). Kodi on the TV reads one M3U and plays streams itself.

| Host | Content | Stream path |
|---|---|---|
| `sat.heissa.de` | Astra 19.2E guest list (Live TV), same as tv.heissa.de | TV tuner |
| `de.heissa.de` | FRITZ!Box cable (DVB-C via RTSP, preferred) + German IPTV; `/` = phone frontend (plays in Kodi) | direct from home |
| `at/ch.heissa.de` | Austrian / Swiss IPTV | geo-blocked ones via relay on ipgate1 (Privado exits 1043/1041) |
| `it.heissa.de` | Italian IPTV | direct (no Italian exit yet) |
| `us.heissa.de` | US IPTV | geo-blocked ones via relay on heissa (US IP) |
| `ru.heissa.de` | Russian IPTV, names transliterated to Latin | **all** via relay on heissa (US IP): EU blocks some Russian channels; list = what plays from the US (`probe_m3u.py raw_ru.m3u` run on heissa → `--ru-alive`) |

- `make_country_m3u.py` (kellertreppe): alive IPTV list + FRITZ!Box `/dvb/m3u/{tvhd,tvsd,radio}.m3u`
  → `<cc>/list.m3u` + `de/all.m3u`; drops shopping/adult/placeholders and the dead public-broadcaster
  SD entries; cable radio gets `radio="true"`. Kodi: iptvsimple `m3uUrl=http://192.168.178.218:8090/m3u/de/all.m3u`.
- `hls_relay.py`: `GET /<cc>/<token>/<b64url>[.ext]`, fetches through the country exit (curl, SOCKS ok),
  rewrites playlists so segments follow. ipgate1: `10.9.0.1:18099` (ch/at), heissa: `127.0.0.1:18099` (us).
  Must run as its own user on ipgate1 — replies of the SOCKS users (uid 993/994) get the Privado fwmark and
  would leave through the tunnel instead of wg0.
- `iptv-country.conf`: Apache vhosts on heissa; lists only for home IPs/VPN (they carry the relay token).
- `tv_all_pdf.py`: `tv_all.pdf`, one section per subdomain (sat numbers, Kodi channel numbers).
- Install iptvsimple without the GUI: Kodi EventServer builtin `InstallAddon(pvr.iptvsimple)`, confirm with
  JSON-RPC `Input.Left` + `Input.Select`.

## Daily check and publishing

- `iptv_daily.sh` (kellertreppe, cron 04:30): candidate lists → `stream_check.py` streams every channel with
  ffmpeg up to 60 s (alive at 512 KB, dead below 64 KB; cable max 2 parallel) → `dead.txt` →
  lists rebuilt with `--dead` → frontend lists, `tv_all.pdf` (also at https://tv.heissa.de/tv_all.pdf).
- `iptv_pull.sh` (heissa, cron 05:30): pulls the checked lists from http://10.8.0.6:8090/m3u/ over the VPN.
- `https://<cc>.heissa.de/` = channel list with **▶ Browser** (hls.js, plays on the phone/laptop) and
  **TV** (plays in Kodi on the Sharp); other paths go to the relay. Any player works too:
  `mpv https://ru.heissa.de/list.m3u`.

## Family access worldwide

- Start pages and lists: home connection / VPN without login, everyone else with one shared password
  (Apache Basic Auth, user `family`, 6-digit PIN, `/etc/apache2/iptv-family.htpasswd`, `htpasswd -B` to change it).
  fail2ban jail `iptv-auth` (filter apache-auth): 3 wrong logins within 10 min → 10 min ban.
  Logged-in family members can watch in the browser or any player, but the **TV** button (Kodi on the Sharp)
  stays home/VPN only (`lib.php` `require_allowed(true)` + `allowed()`).
- `iptv_share_guard.py` (heissa, root cron every minute): more than 9 distinct foreign IPs streaming within
  15 min → every further IP is banned for 1 day via fail2ban jail `iptv-share` (+ mail).
- Capacity (measured 2026-10-30): heissa 600 Mbit/s → ~50 parallel streams (us/ru, max 5 Mbit/s each);
  Privado tunnel on ipgate1 ~50 Mbit/s per country → ~9-10 parallel ch/at streams.

## Front cache (one download per channel)

The relay sends `Cache-Control: max-age=60` for segments and `max-age=2` for playlists; Apache on heissa
caches the stream paths (`CacheEnable disk` + `CacheLock`, htcacheclean 2 GB). N viewers of one channel cost
the source / Privado tunnel one download (checked: second request `X-Cache: HIT`, 8.4 s → 2.7 s).
Real multicast is not possible over the internet; the FRITZ!Box serves cable TV unicast (RTSP) only.
