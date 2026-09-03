# CMSNT / SHOPCLONE7 — Adding a Supplier API Type (condensed)

Repo family: `D:\taadaa\site ban hang clone` (SHOPCLONE7). Source of truth for the SHOPMAIL job:
`SHOPMAIL_INTEGRATION_PLAN.md` in-repo (acceptance matrix + audit hardening). This file is the
condensed, reusable pattern for adding ANY new supplier type (`API_1`…`API_32`, `XSCR`, `SHOPMAIL`).

## The template: XSCR

`XSCR` (xscr.us) is the modern-JSON template. A new type clones it at **6 integration points**
(XSCR itself misses #6 — don't repeat that mistake):

1. `SHOPCLONE7/libs/suppliers.php` — 3 adapters + 1 request helper, placed after the XSCR block:
   - `_<type>_request($method,$url,$api_key,$body,$proxy)` → returns `{body, http_code, json}`
   - `balance_API_<TYPE>` → `{status:'success', data:{money:N}}` or `{status:'error',msg}`
   - `listProduct_API_<TYPE>` → `{status:'success', categories:[{id,name,products:[{id,name,description,amount,price}]}]}` (flat non-child shape)
   - `buy_API_<TYPE>($domain,$coupon,$api_key,$id_api,$amount,$proxy)` → `{status, msg, trans_id, data:[account strings], http_code}`
2. `SHOPCLONE7/ajaxs/client/product.php` — buy branch `if($supplier['type'] == '<TYPE>')` cloned from XSCR (~line 345 onward).
3. `SHOPCLONE7/cron/suppliers/<type>.php` — new cron file: type filter, anti-spam settings row name (`time_cron_suppliers_<type>`), adapter calls, create/update/delete loop + image cleanup.
4. `SHOPCLONE7/views/admin/product-api-add.php` + `product-api-edit.php` — each: validate branch, dropdown `<option>`, JS field-toggle entry.
5. Crontab on VPS: `*/5 * * * * curl -fsS "https://<domain>/cron/suppliers/<type>.php?key=<KEY>"`.
6. `config.php` `$cron_suppliers` — register `'<TYPE>' => '<file>'` (~line 114) or the admin page won't show the cron warning / version.php won't list it (XSCR bug: missing).

## Hardening checklist (from the SHOPMAIL audit — apply to any new type)

- **Buy success = strict**: only `array_key_exists('ok',$json) && $json['ok']===true` AND normalized
  items non-empty. NO "HTTP 2xx and no error" fallback. Success-but-broken-items → error (money
  was charged at source; needs manual reconciliation, don't fake success).
- **List success = strict**: HTTP 2xx + JSON + products/items array present (empty array is VALID).
  Validate EACH item: id has value, name non-empty, price numeric ≥ 0, stock integer ≥ 0 — drop bad
  items, never default them to 0. Return `valid_count` metadata so the cron can gate cleanup.
- **Cleanup gate (cron)**: only delete stale products/categories when response valid AND
  `valid_count > 0`. A single API glitch/empty-catalog must NOT wipe the store.
- **Request hardening**: https-only URL scheme, `CURLOPT_SSL_VERIFYPEER=true`,
  `CURLOPT_SSL_VERIFYHOST=2`, `CURLOPT_FOLLOWLOCATION=false`, `curl_exec()===false` → fail
  (http_code 0, json null). Check HTTP 2xx on balance too (HTTP 500 + balance field = error).
- **Cron fail-closed**: `key_cron_job` empty → `die` (no sync, no cleanup).
- **Admin alert injection**: put supplier's msg into `alert()` via `json_encode($msg)` — never
  string-concatenate API-controlled text into `<script>alert("...")`.
- **402 heuristic**: prefer real HTTP 402; only map `insufficient balance|funds` message → 402;
  cast msg to string before `preg_match`.
- **Coupon**: only send it if the API contract includes it. SHOPMAIL contract is
  `api_key/product_id/quantity` only — coupon body field removed, JS hides coupon field for the type.
- **Buy branch guards**: check `is_array($data)` after `json_decode` BEFORE reading
  `$data['http_code']` (XSCR inherits this warning bug — don't copy it).
- **Category match**: by `name` AND `supplier_id` (name-only collides with other sources;
  `listProduct` flattens to one shared category name).
- **Partial delivery (money-critical)**: `delivered` = insert-success count ONLY. Validate each
  account (`A|B|C`-ish: ≥3 `|`-parts, parts non-empty), dedupe, cap at purchased `$amount`
  (no over-delivery). `delivered==0` → full refund, no order. `0<delivered<amount` → partial refund
  `REFUNDPART_<trans_id>` at unit-price × shortage, and only adjust `$amount/$pay/$money` AFTER
  `RefundCredits()` returns true; refund false → log + admin noti + error die (reconciliation).
- **Credentials storage**: keep `check_string()` escaped like every other type (stored-XSS safe;
  textarea/HTML attributes auto-decode; txt/email paths `htmlspecialchars_decode` first).

## Money-path invariants (shared, do NOT touch)

`RemoveCredits` happens BEFORE fetching; order created only when `$isValue > 0`; `dongtien.transid`
unique guards double refunds. Orphan state (product_sold inserted, product_order insert fails) is a
shared-architecture concern — out of scope for a single-type integration.

## Worktree hygiene for this repo

- Worktree is chronically dirty (views EOL noise, AGENTS.md, untracked txt). Never blanket
  `git checkout`/`restore` — you'll nuke others' in-progress work. Revert per-hunk only.
- All scope files are LF in worktree; keep them LF (patch tool preserves; verify byte-level).
- NEVER commit/push/deploy without explicit user instruction (this repo: "không commit/push/deploy").
- User-facing reports in Vietnamese.