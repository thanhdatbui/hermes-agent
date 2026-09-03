---
name: shopclone7-shop-ops
description: Edit, fix, and deploy the SHOPCLONE7 (CMSNT PHP) shop site — locate the live vs source copies, respect the VPS deployment boundary, and find the exact files for product-visibility and Telegram-bot-notification edits.
---

# SHOPCLONE7 Shop Operations

SHOPCLONE7 = CMSNT PHP shop (brand "Doravo"). The live site is served from a **remote Ubuntu VPS**; the Windows dev machine holds the SOURCE only.

## Deployment topology (READ FIRST)
- **Edit source here:** `D:\Taadaa\site ban hang clone\SHOPCLONE7` — make code changes here.
- **OneDrive mirror is PARTIAL:** `D:\OneDrive\site ban hang clone\SHOPCLONE7` has only `config.php` + `.env` locally; `cron/`, `libs/`, etc. are OneDrive Files-On-Demand placeholders NOT downloaded. Do not use it for editing or "is this live?" checks.
- **Live web root (VPS):** `/var/www/shopclone7/current` → symlink to `releases/<id>`. Ubuntu + nginx/Apache + PHP-FPM 7.4 + MariaDB. DB on the VPS (`localhost`).
- **Deploy flow:** build `SHOPCLONE7.zip` from source → upload to `/var/www/shopclone7/backups/source/` → run `scripts/deploy_shopclone7.sh` on the VPS (dry-run first; real needs `CONFIRM_REAL_RUN=stage-shopclone7-release`; activate with `ACTIVATE_RELEASE=1 CONFIRM_ACTIVATE=activate-shopclone7-current`). See `DEPLOY_STRUCTURE.md` / `DEPLOY_HANDOFF.md` in repo root.

## Pitfalls
- **Editing `D:\Taadaa\...` does NOT change the live site** — you must deploy to the VPS. Before editing, confirm which copy is live: compare the new-product alert body text in Telegram against `libs/stock_alert.php` (they match the live copy).
- **Execution boundary:** from the Windows dev machine you usually cannot execute on the VPS — no SSH key in this environment and the VPS MySQL is firewalled (remote 3306 refused/timeout). DB mutations and code deploys run **on the VPS**. Either get SSH access or hand the user exact SQL / @BotFather steps.
- **Bot rename = user action:** rename the Telegram bot via @BotFather `/setname` (pick bot → type `doravo bot`). No code/DB needed. (Or call Telegram `setMyName` with the token from `settings.telegram_token`.)
- No `php` CLI on the dev machine → can't `php -l` locally; edits are string swaps (low risk).

## Common edit map
- **New API product auto-visible (not hidden):** `cron/suppliers/xscr.php`, `shopclone7.php`, `shopmail.php`. Line appears TWICE per file:
  `$product_status = (isset($supplier['isAutoShow']) && $supplier['isAutoShow'] == 1) ? 1 : 0;`
  → replace with `$product_status = 1;` to force new API products visible.
- **Telegram bot notification text/language:** `libs/stock_alert.php`, 4 functions invoked from `cron/cron.php`:
  - `stockAlertCheck` → `⚠️ CẢNH BÁO TỒN KHO THẤP`
  - `sourcePriceAlertCheck` → `🔔 ĐỔI GIÁ NGUỒN CLONEFBIG`
  - `newApiProductAlertCheck` → `🆕 SẢN PHẨM API MỚI`
  - `supplierBalanceAlertCheck` → `⚠️ SỐ DƯ API THẤP`
  Original strings were un-accented Vietnamese (`San pham`, `Ten`, `Gia nguon`, `Ton kho`, `Trang thai`, `Hien thi`/`An`) — fix to proper Vietnamese (`Sản phẩm`, `Tên`, `Giá nguồn`, `Tồn kho`, `Trạng thái`, `Hiển thị`/`Ẩn`).
  - Alert visibility flag: `$visible = ((int)$product['status'] === 1 && (int)$product['hide_in_shop'] === 0);`

## Bulk-unhide existing API products (run on VPS DB)
```sql
SELECT COUNT(*) FROM products WHERE supplier_id>0 AND api_id<>'' AND status=0;
UPDATE products SET status=1 WHERE supplier_id>0 AND api_id<>'' AND status=0;
```

See `references/deploy-topology.md` for file-by-file detail and secret-safe `.env` handling.
