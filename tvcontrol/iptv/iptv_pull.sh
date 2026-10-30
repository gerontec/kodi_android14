#!/bin/sh
# heissa: fetch the checked IPTV lists from kellertreppe over the VPN (cron 05:30, after iptv_daily.sh)
for f in de/list.m3u de/all.m3u at/list.m3u ch/list.m3u it/list.m3u us/list.m3u ru/list.m3u fr/list.m3u; do
    tmp=/var/www/iptv/$f.new
    if curl -sf -m 60 -o "$tmp" "http://10.8.0.6:8090/m3u/$f" && head -1 "$tmp" | grep -q '^#EXTM3U'; then
        mv "$tmp" "/var/www/iptv/$f"
    else
        rm -f "$tmp"; echo "$(date '+%F %T') pull failed: $f" >&2
    fi
done
