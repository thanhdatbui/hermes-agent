# API_31 catalog, pricing, and source-price alerts

Session-derived operational reference for SHOPCLONE7 live operations. Keep credentials, API keys, cron keys, and account contents out of this file.

## Product provenance and catalog exports

Use the live DB, not the local source tree, as the catalog source of truth:

```sql
-- API-linked products
SELECT id, api_id, name, slug, status, category_id, price, cost, api_stock
FROM products
WHERE supplier_id = 1
ORDER BY id;

-- Manually uploaded products
SELECT id, name, slug, status, category_id, price, cost, api_stock
FROM products
WHERE supplier_id = 0
ORDER BY id;
```

- `supplier_id > 0` plus a non-empty `api_id` = supplier/API-linked product.
- `supplier_id = 0` = manually uploaded stock.
- Build review links as `https://doravo.net/product/<slug>`; verify every URL returns HTTP 200.
- A useful authenticated admin filter is `?module=admin&action=products&supplier_id=1&limit=100`; use `supplier_id=none` for manual products. Do not expose admin pages that render API keys or cron keys.
- Report current counts and explicitly say whether the list includes newly enabled products.

## API_31 price behavior

For source price `api_price` and supplier markup `discount`:

```text
cost = api_price
if update_price == ON:
    price = api_price + api_price * discount / 100
if update_price == OFF:
    existing price is preserved
```

- API_31 does not multiply by stored `rate`; do not describe `rate=1` as the active multiplier without reading the connector.
- `update_price=ON` overwrites existing per-product `products.price` at the next supplier sync.
- `update_price=OFF` still permits normal sync of `cost`, `api_stock`, and `api_time_update`, while preserving manually set `products.price`.
- Before toggling `update_price`, back up supplier safe fields and a product pricing snapshot. Use a conditional, identity-checked update on the one supplier row; verify the flag, unchanged `discount/rate`, unchanged product price rows, and unchanged other suppliers.
- Do not manually trigger a supplier sync merely to prove the flag; a scheduled sync is sufficient unless the user explicitly requests an immediate sync.

## Telegram source-price alert pattern

Existing flow: `cron/cron.php` includes `libs/stock_alert.php` and calls the low-stock check every minute; `sendMessTelegram()` uses the already configured Telegram recipient. Extend this flow rather than creating another bot/token.

Required behavior for an API source-price watcher:

1. Gate on configured Telegram settings; if disabled/missing, return without creating or mutating the baseline.
2. Read a dedicated `settings` state row (for example `source_price_alert_state_clonefbig`). On first run, silently store the current `products.cost` map keyed by product ID.
3. On later runs, compare `products.cost` for the exact supplier/API-linked products; detect both increases and decreases.
4. Alert with product ID/API ID/name, old source price, new source price, and current local selling price. Escape HTML and chunk below Telegram's message limit.
5. Advance the state only when there are no changes or every Telegram chunk returns success; failed sends must retry the same change on the next cron run.
6. Never mutate `products.price`, call a buy endpoint, or include secrets in alert text.

Verification: PHP 7.4 lint the changed live files, run a static invariant probe, confirm the cron call and function marker, then wait for a cron cycle and verify only non-secret state metadata (`JSON_VALID`, JSON length, product count). Do not claim a real price-change notification was delivered unless a real source-price transition was observed; baseline creation proves installation only.

## Live-write evidence

- A worker report is not completion proof. Independently check the final DB flag, product rows, backup path, live markers, PHP lint, and site HTTP status.
- Supplier sync may concurrently change `api_stock`, `cost`, or `api_time_update`; separate that drift from the requested mutation.
- If local and live files differ because of CRLF/LF, compare normalized content before diagnosing semantic drift; preserve each file's original EOL when editing.

## Deploy/backup/verify playbook (proven 2026-08-11, source-price alert)

1. **Static probe RED→GREEN (no local PHP needed):** python text-invariant assertions on the two files — function exists, state-name literal, telegram-guard BEFORE state-read (first-run silent), baseline `'{}'` insert, SELECT shape (`supplier_id = ? AND api_id IS NOT NULL` incl. `cost`), numeric old/new compare, `if (!$alerts || $sent)` gating, no `UPDATE products`, chunk limit, cron call after `stockAlertCheck($CMSNT);`, no bot-token-shaped literal (`\b\d{8,10}:[A-Za-z0-9_-]{30,}\b`), brace balance. Run on unmodified files first (expect FAIL on new-feature invariants), then GREEN after edit.
2. **Behavioral harness on VPS php7.4** (fake DB + fake `sendMessTelegram`, never touching live DB/Telegram): silent first baseline, increase AND decrease, HTML escaping, new product silent, send-fail → state NOT advanced → retry, chunking (each ≤4096), one-chunk-fail → nothing advances, telegram-off → return false + no state mutation, no product-table mutation. Starter: `templates/cmsnt-cron-function-harness.php` in `php-verification-without-runtime`.
3. **Backup before deploy:** `mkdir -p /var/www/shopclone7/backups/pre-<feature>-deploy/<UTC ts>`; `cp -p` the live originals; `MANIFEST.txt` with per-file sha256, `readlink -f current`, state-row-absence note, restore example; `chmod 750` dir / `640` files, `chown -R deploy:www-data`. Verify the recorded sha256 matches known deployed hashes (e.g. HANDOFF) before trusting the backup.
4. **Deploy artifact:** convert EOL to the live file's convention (live `cron/cron.php` CRLF; check with python byte counts). No local PHP on the Windows host — lint is remote-only: `scp` to `/tmp`, `php -l`, then atomic install per file: `install -o deploy -g www-data -m 644 /tmp/x "$CUR/dir/.x.new" && mv -f "$CUR/dir/.x.new" "$CUR/dir/x"` (same-dir rename). No php-fpm reload needed.
5. **Post-deploy:** `php -l` live files; `sha256sum` live == local artifact; grep function/state-name/call markers; no `.new` temps left; `systemctl is-active nginx php7.4-fpm mariadb`; homepage HTTP 200.
6. **Baseline proof:** wait ≥1 real cron cycle (cron.php every minute — crontab dump masks keys). Read-only DB check: state row exists, `LENGTH(value)`, `JSON_VALID(value)=1`, `JSON_LENGTH(value)` == product count for the scope; `check_time_cron_cron` age <60s proves the cron actually ran. Do NOT claim a Telegram delivery without observing a real cost transition; baseline creation is the evidence.
