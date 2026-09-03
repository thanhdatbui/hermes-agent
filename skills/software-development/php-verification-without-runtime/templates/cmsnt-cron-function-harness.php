<?php
/**
 * Starter harness: verify a CMSNT/SHOPCLONE7 cron function of the shape
 * function xxxAlertCheck($CMSNT) — deduplicated Telegram alert with settings-row
 * state. Fake DB + fake Telegram; no live DB/network. Run: php harness.php
 *
 * Usage:
 *   1. Copy the libs file under test (e.g. stock_alert.php) next to this file.
 *   2. Adjust `require` + scenarios, run with php on any PHP host (e.g. VPS php7.4).
 *   3. Exit 0 = all PASS; exit 1 = any FAIL. Report as harness evidence, not suite green.
 *
 * Proven 2026-08-11 (source-price alert): baseline silent, +/- detection,
 * HTML escaping, send-fail retry, chunking, telegram-off no-mutation.
 */
$stateStore = [];        // settings name => value (state JSON)
$productsTable = [];     // rows exactly as the real DB returns them (assoc arrays)
$telegramResponses = []; // queue of raw responses; empty => default ok:true
$sentMessages = [];
$failures = 0;

function sendMessTelegram($my_text)
{
    global $sentMessages, $telegramResponses;
    $sentMessages[] = $my_text;
    return $telegramResponses ? array_shift($telegramResponses) : json_encode(['ok' => true]);
}

class FakeDB
{
    public $siteVals = [
        'telegram_status' => '1',
        'telegram_token'   => 'FAKE_TOKEN',
        'telegram_chat_id' => 'FAKE_CHAT',
    ];
    public function site($k)
    {
        return isset($this->siteVals[$k]) ? $this->siteVals[$k] : false;
    }
    public function get_row_safe($sql, $params = [])
    {
        global $stateStore;
        if (strpos($sql, 'FROM `settings`') !== false) {
            $name = $params[0];
            return isset($stateStore[$name]) ? ['value' => $stateStore[$name]] : false;
        }
        return false;
    }
    public function insert($table, $data)
    {
        global $stateStore;
        if ($table === 'settings') {
            $stateStore[$data['name']] = $data['value'];
            return 1;
        }
        return 0;
    }
    public function update($table, $data, $where, $where_params = [])
    {
        global $stateStore;
        if ($table === 'settings' && isset($where_params[0])) {
            $stateStore[$where_params[0]] = $data['value'];
        }
        return 1;
    }
    public function get_list_safe($sql, $params = [])
    {
        global $productsTable;
        return $productsTable;
    }
}

function check($name, $cond, $detail = '')
{
    global $failures;
    echo ($cond ? 'PASS' : 'FAIL') . "  $name" . ($detail !== '' ? ": $detail" : '') . "\n";
    if (!$cond) {
        $failures++;
    }
}

require __DIR__ . '/stock_alert.php'; // file under test

// SNAPSHOT RULES (both bit real sessions — a false FAIL here looks like a code bug):
//  * take $snapshot = $productsTable IMMEDIATELY before each run(); a snapshot from
//    before an intentional mutation will always differ -> false FAIL.
//  * assert against the array you actually mutated. PHP arrays are copy-on-write:
//    foreach ($arr as &$p) { $p['x'] = ...; } mutates $arr, NOT a previously assigned copy.

$db = new FakeDB();

// T1 baseline silent: set $productsTable (incl. one NULL-cost row), $snapshot=$productsTable,
// run, expect 0 messages, state row created with all non-NULL costs, NULL-cost row excluded,
// $productsTable === $snapshot.
// T2 transition: change a cost (decrease), add a brand-new product; run, expect exactly 1
// message containing old/new cost + local price, name HTML-escaped, no line for the new
// product; state advanced (default ok:true).
// T3 increase: change same cost upward; expect 1 message again.
// T4 send failure: $telegramResponses=[json_encode(['ok'=>false,'description'=>'x'])]; run,
// expect state NOT advanced; run again (queue empty => ok) -> retried and advanced.
// T5 telegram off: $db->siteVals['telegram_status']='0'; run; expect false + no state mutation.
// T6 chunking: 40 changed products -> >=2 messages, every strlen <= 4096; with a failed chunk
// in the queue, expect NO cost advanced at all.

echo "\nTOTAL_FAILURES=$failures\n";
exit($failures === 0 ? 0 : 1);
