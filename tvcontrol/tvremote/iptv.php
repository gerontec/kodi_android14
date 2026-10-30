<?php
// de.heissa.de: IPTV / cable channel list for guests; tapping plays the channel in Kodi on the TV.
// List: /var/lib/tvremote/iptv_de.m3u (make_country_m3u.py), playback: sudo -u pi kodi_play.py <index>.
require __DIR__ . '/lib.php';
$ip = require_allowed();

$items = [];
$name = null; $group = '';
foreach (@file(DATA . '/iptv_de.m3u', FILE_IGNORE_NEW_LINES) ?: [] as $line) {
    if (str_starts_with($line, '#EXTINF')) {
        $name = trim(substr($line, strrpos($line, ',') + 1));
        $group = preg_match('/group-title="([^"]*)"/', $line, $m) ? $m[1] : '';
    } elseif ($line !== '' && $line[0] !== '#' && $name !== null) {
        $items[] = ['name' => $name, 'group' => $group];
        $name = null;
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['i'])) {
    header('Content-Type: application/json');
    $i = (string)$_POST['i'];
    if (!ctype_digit($i) || (int)$i >= count($items)) {
        echo json_encode(['ok' => false, 'msg' => 'unknown channel']);
        exit;
    }
    $out = []; $rc = 0;
    exec('sudo -n -u pi /home/pi/tvrestore/kodi_play.py ' . escapeshellarg($i) . ' 2>&1', $out, $rc);
    error_log("iptv $ip -> $i rc=$rc");
    echo json_encode(['ok' => $rc === 0, 'i' => (int)$i,
                      'msg' => $rc === 0 ? '▶ ' . $items[(int)$i]['name'] : 'Fehler · error: ' . implode(' ', $out)]);
    exit;
}

$groups = [];
foreach ($items as $i => $c) $groups[$c['group']][] = [$i, $c['name']];
?>
<!doctype html>
<html lang="de" data-bs-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Kabel &amp; IPTV</title>
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
  <h1 class="h5 mb-2">Kabel &amp; IPTV · Cable &amp; IPTV <small class="text-body-secondary">(Kodi)</small></h1>
  <select id="g" class="form-select mb-2">
    <option value="">Alle Gruppen · all groups</option>
    <?php foreach (array_keys($groups) as $g): ?>
      <option><?= htmlspecialchars($g) ?></option>
    <?php endforeach; ?>
  </select>
  <input type="search" id="q" class="form-control form-control-lg" placeholder="Suchen · search"
         autocomplete="off" enterkeyhint="search">
</header>
<main id="list" class="px-2 px-sm-3 pb-5">
<?php foreach ($groups as $g => $list): ?>
  <section data-group="<?= htmlspecialchars($g) ?>">
  <h2 class="h6 text-uppercase text-body-secondary mt-3 mb-2 ms-1"><?= htmlspecialchars($g) ?></h2>
  <div class="list-group">
  <?php foreach ($list as [$i, $n]): ?>
    <button type="button" class="ch list-group-item list-group-item-action" value="<?= $i ?>"
      data-n="<?= htmlspecialchars(strtolower($n)) ?>"><?= htmlspecialchars($n) ?></button>
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
document.querySelectorAll('.ch').forEach(b => b.addEventListener('click', async () => {
  if (b.classList.contains('busy')) return;
  b.classList.add('busy'); show('… ' + b.textContent);
  try {
    const r = await fetch(location.pathname, { method: 'POST', body: new URLSearchParams({ i: b.value }) });
    const j = await r.json();
    if (j.ok) document.querySelectorAll('.ch').forEach(x => x.classList.toggle('active', x.value === String(j.i)));
    show(j.msg);
  } catch (e) { show('Fehler · error'); }
  b.classList.remove('busy');
}));
</script>
</body>
</html>
