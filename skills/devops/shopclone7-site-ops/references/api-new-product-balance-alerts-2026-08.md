# API new-product + supplier-balance Telegram alerts (deployed 2026-08-11)

Session record: two new `*AlertCheck` functions added to `libs/stock_alert.php` and
hooked in `cron/cron.php` (after `sourcePriceAlertCheck`), reusing the existing bot
(`sendMessTelegram`, same telegram_status/token/chat_id settings). No new bot/token.

## Functions (libs/stock_alert.php)

### newApiProductAlertCheck($CMSNT) — alert new API products synced into Doravo
- State row: `api_new_product_alert_state`; keys = `supplier_id:api_id` (re-sync of
  existing product never alerts); value = `{id, name}` metadata map.
- **First run is a SILENT baseline** — implemented via `$isFirstRun = !$stateRow` flag
  gating the alert condition (`!$isFirstRun && !array_key_exists(...)`). The naive
  `$previous = []` empty map makes every product look new → baseline would alert.
- Scope: `products p JOIN suppliers s ON s.id = p.supplier_id AND s.status = 1`
  WHERE `p.supplier_id > 0 AND p.api_id IS NOT NULL AND p.api_id <> ''` — i.e. ALL
  active API suppliers (clonefbig id1, taikhoan295 id2, XSCR id4 = 53 products), not
  just the named one.
- Disappeared products dropped from baseline (state rebuilt from query each run);
  reappearing counts as new again.
- Alert fields: supplier domain+type, SP ID, API ID, name (truncated 120, HTML-escaped),
  cost/price/stock, visibility (`status=1 && hide_in_shop=0` → "Hien thi" else "An").
- Header `🆕 <b>SẢN PHẨM API MỚI</b>`; chunked at 3300 bytes; state advances only when
  no alerts or every chunk `ok:true` (failed send retries next cron run).

### supplierBalanceAlertCheck($CMSNT) — alert low API balance
- State row: `supplier_balance_alert_state_vnd`; map supplier id → `{below: 0|1, last_balance_vnd}`.
- Scope: every active supplier row matching `status = 1 AND id > 0`; this is the live
  API-linked scope, currently id 1 `clonefbig.com`, id 2 `taikhoan295.com`, and id 4
  `xscr.us`. Do not keep a hardcoded `[1,4]` allowlist when the user asks for all
  connected APIs. Before deployment, enumerate each row's `type/domain` and confirm
  its connector/cron really updates balance; exclude any non-API row explicitly.
  Threshold is `400000` VND, strict `<` (below).
- **First run alerts IMMEDIATELY for any active API supplier already below** (XSCR was
  below → one alert); afterwards only on not-below → below transition; no repeat while
  below; recovery updates state silently (so a later drop alerts again). Invalid
  price → skip, keep prior state; inactive rows are removed from state.
- Reads **stored `suppliers.price`** (updated every 5 min by supplier crons) — does
  NOT call `balance_API_*` itself. Alert: supplier domain+type, `~N.NNN VND`, threshold.

### convertStoredPriceToBaseVnd($price, $currencyRow) — helper
- `suppliers.price` is a **formatted display string** (e.g. `$115.64`) from
  `format_currency()`, or a raw error string on API failure. Default currency row
  (`currencies WHERE default_currency = 1`, currently USD/Dollar rate 26500,
  decimal_currency 2, symbol_left `$`, seperator dot) converts back:
  strip `symbol_left` prefix → regex `^[0-9][0-9.,]*\.[0-9]{N}$` (N = decimal_currency;
  last dot is the decimal separator even with dot thousands grouping) → strip all
  non-digits → `(float)digits / 10^N * rate`. Returns null for empty/error/JSON/curl
  text or missing/invalid currency metadata.
- Sanity values: `$115.64` → 3,064,460 VND; `$0.38` → 10,070 VND.

## Verified (TDD RED→GREEN, no live DB/Telegram touched during tests)
- Static probe 39 checks (markers, guard-before-state-read, chunk ≤4096, no
  `UPDATE products`, no token-shaped literal, brace/paren balance) GREEN.
- php7.4 behavioral harness (FakeDB + fake `sendMessTelegram`) 67 checks GREEN:
  converter edge cases, silent baseline, new-row alert, escape HTML, disappear/reappear,
  send-fail retry, chunking + one-chunk-fail gating, telegram-off no-mutation,
  first-low alert, dedup, recovery/re-alert, invalid-price skip, inactive removal.
- Initial deploy hashes: live `libs/stock_alert.php` sha256
  `646c8330693594759e87648fabc582f64bd81cc93be9457f698cbdc24fcd077a` and live
  `cron/cron.php` sha256 `8ca265462066803dc4ee1c1f35b7f7e525854b3ad96c08919fd25c1083fb6924`;
  owner/mode `deploy:www-data 644`; no php-fpm reload needed.
- Initial backup: `/var/www/shopclone7/backups/pre-api-product-balance-alert/20260811T115654Z/`.
- After the later all-active-supplier scope expansion, live `libs/stock_alert.php`
  sha256 is `a85f3f0306705a5a87ba5e1d938e4b050b6d4e45b2d352792033753867dc0484`
  (CRLF 18076B); backup is
  `/var/www/shopclone7/backups/pre-api-balance-all-suppliers/20260811T121953Z/`.
  `cron/cron.php` hook remains lint-clean and unchanged by that scope-only deploy.
- Post-expansion real cron cycle: `api_new_product_alert_state` JSON_VALID=1, 53 items;
  `supplier_balance_alert_state_vnd` JSON_VALID=1, 3 items with keys `1,2,4`;
  id1 below=0 (~2.93M VND), id2 below=0 (~4.88M VND), id4 below=1 (~10k VND).
  `source_price_alert_state_clonefbig` remains valid with 19 items (prior feature unharmed).
- Data unchanged: products per supplier 0:6, 1:19, 2:23, 4:11; supplier config
  (discount/rate/update_price/isAutoShow); currency default USD 26500.

## Pitfalls hit
- **`\r?\n` in probe regexes**: CRLF files make `\n}\n` match nothing → all body-sliced
  checks false-FAIL. Use `re.search(r"function NAME\(.*?\r?\n\}\r?\n", src, re.S)`.
- **Harness seeding**: chunking/transition scenarios must run the silent baseline FIRST
  (fresh `$stateStore = []` + N products makes run #1 the baseline → "0 messages" FAIL).
- **Guard-position assertion**: compare guard against the state READ
  (`$stateRow = $CMSNT->get_row_safe`), not the state-name literal (which sits at the
  top of the function).
- **EOL**: local `cron/cron.php` LF, live CRLF → convert artifact (python byte counts)
  before deploy so post-deploy diff is minimal.
- **Scope expansion**: when the user says “all sites/API đang connect”, first enumerate
  live `suppliers` rows and inspect each `id + type + domain + status` plus its
  supplier cron/connector. `id > 0` is a candidate scope, not proof by itself that
  every future row is an API balance connector. Use the generic `status=1 AND id>0`
  query only after the current rows are verified; otherwise use an explicit connector
  allowlist. After widening an existing watcher, verify the state map gains the new
  supplier without resetting prior below/above transition state.
- **Remote shell quoting**: backticks inside a locally double-quoted `ssh "..."`
  command can be evaluated by the local shell and corrupt SQL, grep, or manifests.
  Prefer `ssh ... 'bash -s' <<'REMOTE'` (or positional arguments) for commands
  containing backticks, SQL, `awk`, or heredocs. If a deploy command exits non-zero,
  do not call it verified until a separate read-back checks live hash, lint, owner/mode,
  backup manifest, state rows, and HTTP status.
- **Alert delivery claim**: `below=1`, a valid state row, or a successful cron cycle
  proves detection/state advancement only—not that Telegram delivered a message.
  Claim a real alert was delivered only when the send response/log or a user-visible
  Telegram receipt is independently observed; otherwise report “condition detected,
  alert path installed/baseline active”.
