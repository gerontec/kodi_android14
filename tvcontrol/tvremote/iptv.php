<?php
// de.heissa.de: IPTV / cable channel list for guests; tapping plays the channel in Kodi on the TV.
// List: /var/lib/tvremote/iptv_de.m3u (make_country_m3u.py), playback: sudo -u pi kodi_play.py <index>.
require __DIR__ . '/lib.php';
$ip = require_allowed(true);
$can_tv = allowed($ip);          // only home LAN / VPN may switch the TV

// list per country: ?cc=de|at|ch|it|us|ru  (/var/lib/tvremote/iptv_<cc>.m3u)
$cc = preg_match('/^(de|at|ch|it|us|ru|fr)$/', $_GET['cc'] ?? 'de') ? ($_GET['cc'] ?? 'de') : 'de';
$titles = ['de' => 'Kabel & IPTV Deutschland', 'at' => 'Österreich · IPTV', 'ch' => 'Schweiz · IPTV',
           'it' => 'Italia · IPTV', 'us' => 'USA · IPTV', 'ru' => 'Russia · IPTV (via US)', 'fr' => 'France · IPTV'];
$items = [];
$name = null; $group = '';
foreach (@file(DATA . "/iptv_$cc.m3u", FILE_IGNORE_NEW_LINES) ?: [] as $line) {
    if (str_starts_with($line, '#EXTINF')) {
        $name = trim(substr($line, strrpos($line, ',') + 1));
        $group = preg_match('/group-title="([^"]*)"/', $line, $m) ? $m[1] : '';
        $tvgid = preg_match('/tvg-id="([^"]*)"/', $line, $m) ? $m[1] : '';
    } elseif ($line !== '' && $line[0] !== '#' && $name !== null) {
        $items[] = ['name' => $name, 'group' => $group, 'url' => $line, 'id' => $tvgid];
        $name = null;
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['i'])) {
    header('Content-Type: application/json');
    if (!$can_tv) {
        http_response_code(403);
        echo json_encode(['ok' => false, 'msg' => 'TV nur im Haus · TV control at home only']);
        exit;
    }
    $i = (string)$_POST['i'];
    if (!ctype_digit($i) || (int)$i >= count($items)) {
        echo json_encode(['ok' => false, 'msg' => 'unknown channel']);
        exit;
    }
    $out = []; $rc = 0;
    exec('sudo -n -u pi /home/pi/tvrestore/kodi_play.py ' . escapeshellarg($i) . ' ' . escapeshellarg($cc) . ' 2>&1', $out, $rc);
    error_log("iptv $ip -> $cc/$i rc=$rc");
    echo json_encode(['ok' => $rc === 0, 'i' => (int)$i,
                      'msg' => $rc === 0 ? '▶ ' . $items[(int)$i]['name'] : 'Fehler · error: ' . implode(' ', $out)]);
    exit;
}

$groups = [];
foreach ($items as $i => $c) $groups[$c['group']][] = [$i, $c['name'], $c['url'], $c['id']];
// now/next from the daily EPG build (epg_merge.py): {tvg-id: [[start, stop, title], ...]}
$epg_all = json_decode(@file_get_contents(DATA . '/epg_now.json') ?: '{}', true) ?: [];
// English translations of Cyrillic titles (dell, NLLB, epg_titles_translate.py): {original: english}
$tr = json_decode(@file_get_contents(DATA . '/epg_titles_en.json') ?: '{}', true) ?: [];
$epg = [];
foreach ($items as $c) {
    if ($c['id'] === '' || !isset($epg_all[$c['id']])) continue;
    $epg[$c['id']] = array_map(fn($p) => [$p[0], $p[1], $p[2], $tr[$p[2]] ?? ''], $epg_all[$c['id']]);
}
// [title, english or '', until]
function now_prog(array $epg, string $id): ?array {
    foreach ($epg[$id] ?? [] as [$a, $b, $t, $en]) if ($a <= time() && time() < $b) return [$t, $en, date('H:i', $b)];
    return null;
}
?>
<!doctype html>
<html lang="de" data-bs-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title><?= htmlspecialchars($titles[$cc]) ?></title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script>
  if (matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.dataset.bsTheme = 'dark';
</script>
<style>
  html, body { height:100%; }
  body { display:flex; flex-direction:column; }
  #list { flex:1 1 auto; overflow-y:auto; -webkit-overflow-scrolling:touch; overscroll-behavior:contain; }
  .ch { min-height:50px; font-size:1.05rem; }
  .ch.busy { opacity:.5; }
</style>
</head>
<body>
<header class="border-bottom bg-body p-3 pb-2">
  <a class="btn btn-sm btn-outline-secondary float-end" href="https://tv.heissa.de/tv_all.pdf" target="_blank">PDF</a>
  <h1 class="h5 mb-2"><?= htmlspecialchars($titles[$cc]) ?></h1>
  <select id="g" class="form-select mb-2">
    <option value="">Alle Gruppen · all groups</option>
    <?php foreach (array_keys($groups) as $g): ?>
      <option><?= htmlspecialchars($g) ?></option>
    <?php endforeach; ?>
  </select>
  <input type="search" id="q" class="form-control form-control-lg" placeholder="Suchen · search"
         autocomplete="off" enterkeyhint="search">
</header>
<div id="player" class="d-none bg-black position-relative">
  <video id="v" controls playsinline class="w-100" style="max-height:45vh"></video>
  <div id="epgline" class="position-absolute top-0 start-0 m-2 px-2 py-1 rounded small text-white"
       style="background:rgba(0,0,0,.55); pointer-events:none"></div>
  <button id="cc" type="button" class="btn btn-sm btn-dark position-absolute top-0 end-0 m-2 d-none">CC</button>
</div>
<main id="list" class="px-2 px-sm-3 pb-5">
<?php foreach ($groups as $g => $list): ?>
  <section data-group="<?= htmlspecialchars($g) ?>">
  <h2 class="h6 text-uppercase text-body-secondary mt-3 mb-2 ms-1"><?= htmlspecialchars($g) ?></h2>
  <div class="list-group">
  <?php foreach ($list as [$i, $n, $u, $id]): $now = now_prog($epg, $id); ?>
    <div class="ch list-group-item d-flex align-items-center gap-2" data-i="<?= $i ?>" data-id="<?= htmlspecialchars($id) ?>"
      data-n="<?= htmlspecialchars(strtolower($n . ' ' . ($now ? $now[0] . ' ' . $now[1] : ''))) ?>">
      <span class="name flex-grow-1"><?= htmlspecialchars($n) ?>
        <?php if ($now): ?><br><small class="now text-body-secondary">▸ <?= htmlspecialchars($now[0]) ?> · bis <?= $now[2] ?>
          <?php if ($now[1] !== ''): ?><br><span class="fst-italic">EN: <?= htmlspecialchars($now[1]) ?></span><?php endif; ?></small><?php endif; ?></span>
      <?php if (preg_match('#^https?://#', $u)): ?>
        <button type="button" class="btn btn-sm btn-primary web" data-url="<?= htmlspecialchars($u) ?>">▶ Browser</button>
      <?php elseif ($can_tv && $cc === 'de' && str_starts_with($u, 'rtsp://')): ?>
        <!-- cable: converted to HLS on kellertreppe (cable.php); VLC plays the RTSP URL directly -->
        <button type="button" class="btn btn-sm btn-primary web" data-url="cable/<?= $i ?>/index.m3u8">▶ Browser</button>
        <a class="btn btn-sm btn-outline-secondary" href="<?= htmlspecialchars($u) ?>">VLC</a>
      <?php endif; ?>
      <?php if ($can_tv): ?><button type="button" class="btn btn-sm btn-outline-secondary tv">TV</button><?php endif; ?>
    </div>
  <?php endforeach; ?>
  </div>
  </section>
<?php endforeach; ?>
</main>
<div class="toast-container position-fixed bottom-0 start-50 translate-middle-x p-3">
  <div id="toast" class="toast text-bg-dark border-0" role="status" aria-live="polite">
    <div class="toast-body fw-semibold"></div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.15/dist/hls.min.js"></script>
<script>
const toastEl = document.getElementById('toast'), toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 3000 });
const q = document.getElementById('q'), g = document.getElementById('g');
function show(t) { toastEl.querySelector('.toast-body').textContent = t; toast.show(); }
function filter() {
  const s = q.value.trim().toLowerCase(), grp = g.value;
  document.querySelectorAll('section').forEach(sec => {
    sec.hidden = grp && sec.dataset.group !== grp;
    sec.querySelectorAll('.ch').forEach(b => b.classList.toggle('d-none', !!s && !b.dataset.n.includes(s)));
  });
}
q.addEventListener('input', filter);
g.addEventListener('change', () => { filter(); document.getElementById('list').scrollTop = 0; });
// "TV": play in Kodi on the Sharp
document.querySelectorAll('.ch .tv').forEach(b => b.addEventListener('click', async () => {
  const row = b.closest('.ch');
  if (b.disabled) return;
  b.disabled = true; show('… ' + row.querySelector('.name').textContent);
  try {
    const r = await fetch(location.pathname + location.search, { method: 'POST', body: new URLSearchParams({ i: row.dataset.i }) });
    const j = await r.json();
    if (j.ok) document.querySelectorAll('.ch').forEach(x => x.classList.toggle('active', x.dataset.i === String(j.i)));
    show(j.msg);
  } catch (e) { show('Fehler · error'); }
  b.disabled = false;
}));
// "Browser": play here (HLS via hls.js, Safari natively)
let hls = null, playingId = '';
const video = document.getElementById('v'), player = document.getElementById('player');
const EPG = <?= json_encode($epg, JSON_UNESCAPED_UNICODE) ?>;
const epgline = document.getElementById('epgline'), ccBtn = document.getElementById('cc');
const hhmm = t => new Date(t * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
function showEpg() {
  const list = EPG[playingId] || [], now = Date.now() / 1000;
  const cur = list.find(p => p[0] <= now && now < p[1]), next = list.find(p => p[0] >= now);
  const t = p => p[2] + (p[3] ? ` (EN: ${p[3]})` : '');
  epgline.textContent = cur ? `Jetzt · now: ${t(cur)} · bis ${hhmm(cur[1])}` + (next ? `  ·  danach: ${t(next)}` : '') : '';
  epgline.classList.toggle('d-none', !cur);
}
setInterval(showEpg, 60000);
// closed captions (CEA-608 in the video): hls.js exposes them as text tracks
function captionTracks() { return [...video.textTracks].filter(t => t.kind === 'captions' || t.kind === 'subtitles'); }
video.textTracks.addEventListener('addtrack', () => ccBtn.classList.toggle('d-none', captionTracks().length === 0));
ccBtn.addEventListener('click', () => {
  const tr = captionTracks(); if (!tr.length) return;
  const on = tr[0].mode !== 'showing';
  tr.forEach((t, k) => t.mode = (on && k === 0) ? 'showing' : 'hidden');
  ccBtn.classList.toggle('btn-light', on); ccBtn.classList.toggle('btn-dark', !on);
});
document.querySelectorAll('.ch .web').forEach(b => b.addEventListener('click', () => {
  const row = b.closest('.ch'), url = b.dataset.url, name = row.querySelector('.name').firstChild.textContent.trim();
  playingId = row.dataset.id; showEpg(); ccBtn.classList.add('d-none');
  player.classList.remove('d-none');
  if (hls) { hls.destroy(); hls = null; }
  if (window.Hls && Hls.isSupported()) {
    // long-haul relay: start 3 segments behind live and keep a big buffer so jitter does not cut the audio
    hls = new Hls({ liveSyncDurationCount: 3, liveMaxLatencyDurationCount: 10, maxBufferLength: 60, maxMaxBufferLength: 120 });
    hls.on(Hls.Events.ERROR, (e, d) => { if (d.fatal) show('Stream-Fehler · stream error'); });
    hls.loadSource(url); hls.attachMedia(video);
  } else {
    video.src = url;
  }
  video.play().catch(() => {});
  show('▶ ' + name);
}));
</script>
</body>
</html>
