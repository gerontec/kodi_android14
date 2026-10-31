<?php
// Browser player for the FRITZ!Box cable channels of the de list: RTSP -> HLS on demand (cable_hls.sh),
// home LAN / VPN only (cable tuners and CPU are local).  /cable/<n>/index.m3u8, /cable/<n>/segK.ts
require __DIR__ . '/lib.php';
const HLS = '/dev/shm/cablehls';
const TUNERS = 2;                 // browser sessions at once; Kodi needs a tuner too

if (!allowed(client_ip())) { http_response_code(403); exit; }
$i = $_GET['i'] ?? ''; $f = $_GET['f'] ?? '';
if (!ctype_digit($i) || !preg_match('/^(index\.m3u8|seg\d+\.ts)$/', $f)) { http_response_code(404); exit; }

// entry n of the de list (same counting as iptv.php) must be a cable channel
$url = null; $n = -1; $ext = false;
foreach (@file(DATA . '/iptv_de.m3u', FILE_IGNORE_NEW_LINES) ?: [] as $line) {
    if (str_starts_with($line, '#EXTINF')) { $ext = true; continue; }
    if ($line === '' || $line[0] === '#' || !$ext) continue;
    $ext = false;
    if (++$n === (int)$i) { $url = $line; break; }
}
if ($url === null || !str_starts_with($url, 'rtsp://')) { http_response_code(404); exit; }

function running(string $dir): bool {
    $pid = (int)@file_get_contents("$dir/pid");
    return $pid > 0 && file_exists("/proc/$pid");
}

$dir = HLS . "/$i";
if ($f === 'index.m3u8') {
    @mkdir(HLS);
    $lock = fopen(HLS . '/.lock', 'c');
    flock($lock, LOCK_EX);
    if (!running($dir)) {
        // free a tuner: stop the session that was watched least recently
        $other = [];
        foreach (glob(HLS . '/*', GLOB_ONLYDIR) as $d) if (running($d)) $other[$d] = @filemtime("$d/last");
        if (count($other) >= TUNERS) {
            asort($other);
            posix_kill((int)file_get_contents(array_key_first($other) . '/pid'), SIGTERM);
            sleep(1);
        }
        exec('setsid ' . escapeshellarg(__DIR__ . '/cable_hls.sh') . ' ' . escapeshellarg($i) . ' '
             . escapeshellarg($url) . ' > /dev/null 2>&1 &');
        for ($t = 0; $t < 30 && !running($dir); $t++) usleep(100000);
    }
    flock($lock, LOCK_UN);
    touch("$dir/last");
    // first segment: probe + tune + 2 s of video; give up after 11 s like the players
    for ($t = 0; $t < 110 && !is_file("$dir/index.m3u8"); $t++) usleep(100000);
}
$p = "$dir/$f";
if (!is_file($p)) { http_response_code(404); exit; }
header('Cache-Control: no-store');
header('Content-Type: ' . ($f === 'index.m3u8' ? 'application/vnd.apple.mpegurl' : 'video/mp2t'));
header('Content-Length: ' . filesize($p));
readfile($p);
