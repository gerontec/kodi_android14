<?php
// Shared access control for the guest remotes (tv.heissa.de, de.heissa.de):
// home LAN, home IPv6 prefix / public IPv4 (cron-refreshed), VPN; heissa proxy passes X-Forwarded-For.

const DATA = '/var/lib/tvremote';
const PROXY = '10.8.0.1';

function in_cidr(string $ip, string $cidr): bool {
    [$net, $bits] = explode('/', $cidr);
    $a = @inet_pton($ip); $b = @inet_pton($net);
    if ($a === false || $b === false || strlen($a) !== strlen($b)) return false;
    $bytes = intdiv((int)$bits, 8); $rest = (int)$bits % 8;
    if (substr($a, 0, $bytes) !== substr($b, 0, $bytes)) return false;
    if ($rest === 0) return true;
    $mask = chr((0xff << (8 - $rest)) & 0xff);
    return (($a[$bytes] & $mask) === ($b[$bytes] & $mask));
}

function client_ip(): string {
    $ip = $_SERVER['REMOTE_ADDR'] ?? '';
    if ($ip === PROXY && !empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
        // heissa's Apache appends the real client as the last entry
        $list = array_map('trim', explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']));
        $ip = end($list);
    }
    if (str_starts_with($ip, '::ffff:')) $ip = substr($ip, 7);
    return $ip;
}

function allowed(string $ip): bool {
    $nets = ['192.168.178.0/24', '192.168.5.0/24', '10.8.0.0/24', 'fd10:8::/64', 'fd00::/64'];
    // current home IPv6 /64 prefixes and public IPv4, refreshed by cron (prefix may change)
    foreach (@file(DATA . '/home_nets', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [] as $n) $nets[] = $n;
    foreach ($nets as $n) if (in_cidr($ip, $n)) return true;
    return false;
}

function require_allowed(): string {
    $ip = client_ip();
    if (!allowed($ip)) {
        http_response_code(403);
        echo "<!doctype html><meta charset=utf-8><title>TV</title><p>Nur im Haus-WLAN · home Wi-Fi only ($ip)</p>";
        exit;
    }
    return $ip;
}
