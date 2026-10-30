<?php
require __DIR__ . '/lib.php';
// Guest TV remote for the Sharp TV: shows the channel list and switches Live TV over adb.
// Allowed: home LAN (IPv4 192.168.178.0/24 and 192.168.5.0/24 = free5G_EXT, the home IPv6 prefixes, the home public IPv4)
// and VPN 10.8.0.0/24. Requests proxied by heissa (10.8.0.1) are judged by X-Forwarded-For.

$ip = require_allowed();

$channels = json_decode(@file_get_contents(DATA . '/channels.json') ?: '[]', true) ?: [];
$msg = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['ch'])) {
    $ch = (string)$_POST['ch'];
    $valid = array_filter($channels, fn($c) => (string)$c['num'] === $ch);
    if (!$valid) {
        $msg = 'Unbekannter Sender · unknown channel';
    } else {
        // rate limit: one switch every 3 s for everybody
        $last = (int)@filemtime(DATA . '/current');
        if (time() - $last < 3) usleep(3000000);
        $out = []; $rc = 0;
        exec('sudo -n -u pi /home/pi/tvrestore/tv_tune.sh ' . escapeshellarg($ch) . ' 2>&1', $out, $rc);
        $name = array_values($valid)[0]['name'];
        $msg = $rc === 0 ? "▶ $ch $name" : 'Fehler · error: ' . htmlspecialchars(implode(' ', $out));
        error_log("tvremote $ip -> $ch rc=$rc");
    }
}
$current = trim(@file_get_contents(DATA . '/current') ?: '');
if (($_SERVER['HTTP_X_REQUESTED_WITH'] ?? '') === 'fetch') {
    header('Content-Type: application/json');
    echo json_encode(['msg' => $msg, 'current' => $current, 'ok' => !str_starts_with($msg, 'Fehler')]);
    exit;
}
$groups = ['Radio' => [], 'TV' => []];
foreach ($channels as $c) $groups[$c['radio'] ? 'Radio' : 'TV'][] = $c;
?>
<!doctype html>
<html lang="de" data-bs-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>TV Senderwahl</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script>
  // follow the phone's light/dark setting
  if (matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.dataset.bsTheme = 'dark';
</script>
<style>
  html, body { height:100%; }
  body { display:flex; flex-direction:column; }
  #list { flex:1 1 auto; overflow-y:auto; -webkit-overflow-scrolling:touch; overscroll-behavior:contain; }
  .ch { min-height:52px; font-size:1.05rem; }
  .ch .num { width:3em; text-align:right; font-variant-numeric:tabular-nums; opacity:.6; }
  .ch.busy { opacity:.5; }
  .nav-pills .nav-link { min-height:44px; }
</style>
</head>
<body>
<header class="border-bottom bg-body p-3 pb-2">
  <h1 class="h5 mb-2">Senderwahl · Channels</h1>
  <ul class="nav nav-pills nav-fill mb-2">
    <li class="nav-item"><button type="button" class="nav-link active" data-tab="TV">TV</button></li>
    <li class="nav-item"><button type="button" class="nav-link" data-tab="Radio">Radio</button></li>
  </ul>
  <input type="search" id="q" class="form-control form-control-lg" placeholder="Suchen · search"
         autocomplete="off" enterkeyhint="search">
</header>
<main id="list" class="px-2 px-sm-3 pb-5">
<?php foreach ($groups as $g => $list): if (!$list) continue; ?>
  <section data-group="<?= $g ?>">
  <h2 class="h6 text-uppercase text-body-secondary mt-3 mb-2 ms-1"><?= $g ?></h2>
  <form method="post" class="list-group">
  <?php foreach ($list as $c): ?>
    <button class="ch list-group-item list-group-item-action d-flex align-items-center gap-3<?= (string)$c['num'] === $current ? ' active' : '' ?>"
      name="ch" value="<?= (int)$c['num'] ?>" data-n="<?= htmlspecialchars(strtolower($c['name'])) ?>">
      <span class="num"><?= (int)$c['num'] ?></span><span class="name<?= !empty($c['default']) ? ' fw-bold' : '' ?>"><?= htmlspecialchars($c['name']) ?></span>
      <?php if (!empty($c['default'])): ?><span class="badge text-bg-secondary ms-auto">Standard</span><?php endif; ?></button>
  <?php endforeach; ?>
  </form>
  </section>
<?php endforeach; ?>
</main>
<div class="toast-container position-fixed bottom-0 start-50 translate-middle-x p-3">
  <div id="toast" class="toast align-items-center text-bg-dark border-0" role="status" aria-live="polite">
    <div class="toast-body fw-semibold"><?= htmlspecialchars($msg) ?></div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
const toastEl = document.getElementById('toast'), toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 2500 });
const q = document.getElementById('q'), list = document.getElementById('list');
let tab = 'TV';
try { tab = localStorage.getItem('tab') || 'TV'; } catch (e) {}
function show(text) { toastEl.querySelector('.toast-body').textContent = text; toast.show(); }
if (toastEl.querySelector('.toast-body').textContent.trim()) toast.show();
function filter() {
  const s = q.value.trim().toLowerCase();
  document.querySelectorAll('section').forEach(sec => {
    // while searching show both groups, otherwise only the selected tab
    sec.hidden = !s && sec.dataset.group !== tab;
    sec.querySelectorAll('.ch').forEach(b => b.classList.toggle('d-none', !!s && !b.dataset.n.includes(s)));
  });
  document.querySelectorAll('[data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
}
document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => {
  tab = b.dataset.tab; try { localStorage.setItem('tab', tab); } catch (e) {}
  q.value = ''; filter(); list.scrollTop = 0;
});
q.addEventListener('input', filter);
// switch without reloading, so the list keeps its scroll position
document.querySelectorAll('.ch').forEach(b => b.addEventListener('click', async e => {
  e.preventDefault();
  if (b.classList.contains('busy')) return;
  b.classList.add('busy'); show('… ' + b.querySelector('.name').textContent);
  try {
    const r = await fetch(location.pathname, { method: 'POST', headers: { 'X-Requested-With': 'fetch' },
                                               body: new URLSearchParams({ ch: b.value }) });
    const j = await r.json();
    if (j.ok) document.querySelectorAll('.ch').forEach(x => x.classList.toggle('active', x.value === j.current));
    show(j.msg || 'OK');
  } catch (err) { show('Fehler · error'); }
  b.classList.remove('busy');
}));
// bring the current channel into view on load
filter();
document.querySelector('.ch.active:not(.d-none)')?.scrollIntoView({ block: 'center' });
</script>
</body>
</html>
