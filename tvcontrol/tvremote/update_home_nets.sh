#!/bin/sh
# Refresh the home IPv6 /64 prefixes and public IPv4 for the tvremote ACL (cron, every 10 min).
out=/var/lib/tvremote/home_nets
tmp=$(mktemp)
ip -6 addr show scope global | awk '/inet6 2/ {split($2,a,"/"); print a[1]}' | while read a; do
    python3 -c "import ipaddress,sys; print(ipaddress.ip_interface(sys.argv[1]+'/64').network)" "$a"
done | sort -u > "$tmp"
v4=$(curl -4 -s -m 10 https://ifconfig.me)
case "$v4" in *.*.*.*) echo "$v4/32" >> "$tmp";; esac
[ -s "$tmp" ] && mv "$tmp" "$out" && chmod 644 "$out" || rm -f "$tmp"
