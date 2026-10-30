# IPTV per country (Kodi pvr.iptvsimple, no channel manager)

TVHeadend was removed (2026-10-30). Kodi on the TV reads one M3U and plays streams itself.

| Host | Content | Stream path |
|---|---|---|
| `sat.heissa.de` | Astra 19.2E guest list (Live TV), same as tv.heissa.de | TV tuner |
| `de.heissa.de` | FRITZ!Box cable (DVB-C via RTSP, preferred) + German IPTV; `/` = phone frontend (plays in Kodi) | direct from home |
| `at/ch.heissa.de` | Austrian / Swiss IPTV | geo-blocked ones via relay on ipgate1 (Privado exits 1043/1041) |
| `it.heissa.de` | Italian IPTV | direct (no Italian exit yet) |
| `us.heissa.de` | US IPTV | geo-blocked ones via relay on heissa (US IP) |

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
