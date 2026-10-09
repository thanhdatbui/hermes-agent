# TikTok Registration Mail Eligibility & Preflight Live Check Policy (18/09/2026)

## 1. Tạm thời tắt hẳn `@gmail.com` khi reg TikTok
- **Nguyên nhân**: Kho Gmail cũ dễ bị checkpoint hoặc nghẽn OTP (`BLOCKED_GMAIL_OTP_TIMEOUT`), trong khi Hotmail OAuth2 thành công 100%.
- **Cấu hình**:
  - `D:/Taadaa/Tiktok_Reg/scripts/tiktok_target_eligibility.py`:
    ```python
    SUPPORTED_DOMAINS = ("@hotmail.com", "@outlook.com", "@live.com")
    ```
  - `D:/Taadaa/tools/ensure_row_accounts.py`: Bỏ qua các email kết thúc bằng `@gmail.com` khi tìm mail có sẵn cho máy.

## 2. Preflight Live Check tự động dọn dẹp Gmail DIE 2 tầng
- **Tầng 1 (Detector)**: `_detect_clean.py` gọi `filter_live_gmail_targets(targets, project_root=ROOT)` ngay khi detect.
- **Tầng 2 (Runner)**: `_run_all_targets.py` kiểm tra chốt chặn trước khi fork batch worker.
- **Hành vi an toàn khi phát hiện Gmail DIE qua `checkmail.live`**:
  1. Loại khỏi danh sách target của batch.
  2. Tự động xóa khỏi file nguồn `gmail_clean_v2.xlsx` (có backup timestamped tại `workbook-backups/`).
  3. Gọi `remove_device_account_fast()` gỡ Google account khỏi máy thật để không chiếm tài nguyên.

## 3. Quy trình tự động cấp bù Hotmail OAuth2 cho máy thiếu
- Khi máy thiếu mail:
  ```bash
  python D:/Taadaa/tools/buy_hotmail.py --append-kibe <N> --target-machines "<M1,M2,...>"
  ```
- Tool tự động mua qua provider ưu tiên (boxtaikhoan -> fallback clonefbig), xác thực access_token Microsoft Graph LIVE 100%, nạp vào `gmail_clean_v2.xlsx` và gán đúng máy.
