# Checklive Cron cuối cùng (2026-08-20) — script `daily_manual_stock_checklive.py`

Script chạy 07:00 daily (`cronjob` `daily-manual-stock-checklive`, `0 7 * * *` — user đổi từ 03:00 sang 07:00 2026-08-20).
Python ở `C:\Users\Kibe\AppData\Local\hermes\scripts\daily_manual_stock_checklive.py`, CHẠY BẰNG venv-core024
(`D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`) vì cần camoufox + playwright.

## Cấu trúc script (3 khối)

1. **SP 40 TikTok (15 acc):** `check_tiktok()` — lấy cookies từ `khommo_get_cookies.py` (Camoufox headful + proxy
   dict tách, profile khommo_profile) nếu file `khommo_cookies.txt` > 6h, rồi POST `api/tiktok_check.php`
   `{"username": X}` qua proxy farm (mỗi acc retry 3, xoay proxy). Quirk: ~50% acc farm trả `success:false`
   (khommo247 bất ổn) → fail list đó giữ nguyên kho, KHÔNG dọn.
2. **SP 57 IG (1108 acc):** `check_ig()` — viết items ra `clonefbig_items.json` → chạy `ig_check_cdp.py`
   (Playwright `connect_over_cdp("http://127.0.0.1:9222")` Chrome Hermes đang chạy, chia **batch 400**,
   `#inputArea` + `startCheck()`, đọc `#liveOutput`/`#dieOutput`) → đọc `clonefbig_result.json` → dọn die.
3. **Báo cáo:** load `checklive_state.json` (prev stock) → in tổng stock + `(hôm qua N → ±delta)` + live/die/fail
   hôm nay + die tích lũy (`product_die` count) — **kể cả SP = 0** (38/39/60/61). State key = STRING `"40"`/`"57"`.

## Phụ thuộc vận hành (quan trọng)

- **IG cần Chrome Hermes CDP 9222 ĐANG MỞ** (session khác giữ `browser_profile`). Chrome tắt → fail toàn bộ IG.
  Nếu cron fail IG, bước đầu tiên kiểm tra `curl -s http://127.0.0.1:9222/json/version`.
- **khommo247 API cần cf_clearance ràng buộc IP**: refresh cookies qua proxy nào → gọi API qua CÙNG proxy;
  cookies hết hạn ~vài giờ → script tự refresh qua Camoufox (máy nhà) khi cần.

## Kết quả verify 2026-08-20

- IG 1108 acc: **100% phân loại** (1108 live, 0 die, 0 fail) — batch 400 qua CDP là chuẩn, KHÔNG nhét cả 1100 acc vào 1 lần (fail hết vì quá tải web + thiếu CF token fresh).
- TikTok 15 acc: 7 live, 1 die (dọn), 7 fail — khommo247 bất ổn với acc farm, không dùng làm nguồn duy nhất; VPS direct check (retry, statusCode 10221) là nguồn chính xác đã verify 8/8.
- Lệnh chạy: `cd %LOCALAPPDATA%\hermes\scripts && D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe daily_manual_stock_checklive.py`

## Lưu ý git-bash

- Script chạy full kho > 600s → luôn `background=true` + `notify_on_complete=true`, không foreground (timeout 600s).
- `python3` mặc định (hermes venv) KHÔNG có camoufox/playwright playwright mới — dùng venv-core024.