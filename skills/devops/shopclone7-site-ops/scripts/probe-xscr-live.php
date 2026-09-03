<?php
// Probe XSCR (supplier id=4) live API: list products filtered by keyword(s).
// Usage on VPS:  php7.4 /tmp/probe_xscr.php [keyword1 keyword2 ...]
//   (no args = all products; e.g. "php7.4 /tmp/probe_xscr.php twitter search")
// Output TSV: category \t api_id \t price \t stock \t name
// Upload from local:  ssh ... 'cat > /tmp/probe_xscr.php' < probe_xscr.php
define("IN_SITE", true);
require_once('/var/www/shopclone7/current/libs/db.php');
require_once('/var/www/shopclone7/current/config.php');
require_once('/var/www/shopclone7/current/libs/lang.php');
require_once('/var/www/shopclone7/current/libs/helper.php');
require_once('/var/www/shopclone7/current/libs/suppliers.php');
$CMSNT = new DB();
$s = $CMSNT->get_row("SELECT * FROM suppliers WHERE id=4");
if (!$s) { echo "NO SUPPLIER 4\n"; exit(1); }
$raw = listProduct_API_XSCR($s['domain'], $s['api_key'], $s['proxy'], true);
$r = json_decode($raw, true);
if (!$r || (isset($r['status']) && $r['status']=='error')) {
    echo "API ERROR: " . (is_array($r) ? (isset($r['msg']) ? $r['msg'] : json_encode($r)) : substr($raw, 0, 300)) . "\n";
    exit(1);
}
$keywords = array_slice($argv, 1);
foreach ($r['categories'] as $cat) {
    foreach ($cat['products'] as $p) {
        $hay = strtolower($p['name']);
        if ($keywords) {
            $keep = false;
            foreach ($keywords as $k) { if (strpos($hay, strtolower($k)) !== false) { $keep = true; break; } }
            if (!$keep) continue;
        }
        echo $cat['name'] . "\t" . $p['id'] . "\t" . $p['price'] . "\t" . $p['amount'] . "\t" . $p['name'] . "\n";
    }
}
