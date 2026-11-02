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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
