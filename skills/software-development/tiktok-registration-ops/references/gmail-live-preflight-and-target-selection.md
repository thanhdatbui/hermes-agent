# Pitfalls: Preflight Live Check & Target Selection in TikTok Reg

## 1. Cơ chế Preflight Live Check (`scripts/gmail_preflight_filter.py`)
- Khi chạy batch qua `_run_all_targets.py`, preflight filter `filter_live_gmail_targets()` kiểm tra live status qua `checkmail.live` (sử dụng `check_gmail_live_batch()` từ `D:/Taadaa/tools/check_gmail_live_fast.py`).
- Mail được xác định DIE (`live_map.get(email) is False`):
  1. Loại ngay khỏi danh sách targets của batch (`[DIE-SKIP]`).
  2. Tự động xóa khỏi workbook nguồn `gmail_clean_v2.xlsx` qua `remove_captcha_dead_email_from_source(email)`.
  3. Tự động gọi `remove_device_account_fast(device, email)` để gỡ tài khoản Google DIE khỏi thiết bị Android qua UI automator.

## 2. Điểm mù và Pitfalls phát hiện (2026-09-18)
- **Tĩnh hóa Targets trước khi Preflight:**
  - `_detect_clean.py` chỉ đối soát tĩnh trong workbook (xem mail đã có trong sheet `Tài Khoản` của tracking workbook hay chưa) và xuất ra `tiktok_reg_clean_targets.json`.
  - Nếu `_run_all_targets.py` bị truyền cờ `--skip-live-check` hoặc chạy một runner trung gian bypass filter, các mail Gmail đã DIE hoặc checkpoint sẽ vẫn lọt vào device và gây lỗi `BLOCKED_GMAIL_OTP_TIMEOUT` do không thể nhận mã xác thực từ TikTok.
- **Quyết sách vận hành khi Gmail nghẽn/chết hàng loạt:**
  - Khi Gmail liên tục bị dính checkpoint hoặc timeout OTP, tạm thời ngắt domain `@gmail.com` trong bộ lọc chọn target reg TikTok, chuyển 100% sang nguồn **Hotmail OAuth2** (`ensure_row_accounts.py` kết hợp `buy_hotmail.py` tự động mua và nạp mail vào máy).
  - Hotmail OAuth2 kết hợp IMAP lấy mã OTP trực tiếp từ server, giảm thiểu 100% rủi ro checkpoint trên app và giải phóng thiết bị khỏi việc phải add Google account vào Android Settings.
