#!/usr/bin/env python3
"""Ban stream sharing: if more than MAX_FOREIGN distinct foreign IPs streamed through the IPTV relays
within WINDOW, every foreign IP beyond the first MAX_FOREIGN (by first request) is banned via fail2ban
(jail iptv-share, 1 day) and gh@heissa.de gets a mail. Home connection and VPN never count.

cron (heissa, root): * * * * * /usr/local/bin/iptv_share_guard.py
"""
import datetime
import ipaddress
import re
import subprocess

LOG = "/var/log/apache2/iptv_access.log"
WINDOW = datetime.timedelta(minutes=15)
MAX_FOREIGN = 9
TRUSTED = [ipaddress.ip_network(n) for n in
           ("178.25.117.246/32", "2a02:810d:4117:7300::/64", "10.8.0.0/24", "10.9.0.0/24",
            "127.0.0.0/8", "::1/128", "74.208.77.214/32", "2607:f1c0:f081:e500::/64")]
STREAM = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "GET /[A-Za-z0-9_-]{16,}/\S+ HTTP/[\d.]+" (200|206) ')


def trusted(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return any(a in n for n in TRUSTED)


def banned():
    out = subprocess.run(["fail2ban-client", "status", "iptv-share"], capture_output=True, text=True).stdout
    m = re.search(r"Banned IP list:\s*(.*)", out)
    return set(m.group(1).split()) if m else set()


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    first_seen = {}
    with open(LOG, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = STREAM.match(line)
            if not m or trusted(m.group(1)):
                continue
            t = datetime.datetime.strptime(m.group(2), "%d/%b/%Y:%H:%M:%S %z")
            if now - t <= WINDOW:
                first_seen.setdefault(m.group(1), t)
    ips = sorted(first_seen, key=first_seen.get)
    if len(ips) <= MAX_FOREIGN:
        return
    already = banned()
    new = [ip for ip in ips[MAX_FOREIGN:] if ip not in already]
    for ip in new:
        subprocess.run(["fail2ban-client", "set", "iptv-share", "banip", ip], capture_output=True)
    if new:
        body = (f"Subject: IPTV: {len(ips)} fremde IPs streamen - {len(new)} gesperrt\nTo: gh@heissa.de\n\n"
                f"Innerhalb von 15 min haben {len(ips)} fremde IPs ueber die Relays gestreamt (erlaubt: "
                f"{MAX_FOREIGN}).\nErlaubt (zuerst gesehen): {', '.join(ips[:MAX_FOREIGN])}\n"
                f"Gesperrt fuer 1 Tag: {', '.join(new)}\n\n"
                f"Entsperren: fail2ban-client set iptv-share unbanip <IP>\n"
                f"Bei Verdacht auf Weitergabe: Token in /etc/hls_relay.token tauschen (ipgate1 + heissa) und Listen neu erzeugen.\n")
        subprocess.run(["/usr/sbin/sendmail", "-t"], input=body.encode(), check=False)


if __name__ == "__main__":
    main()
