# Chính sách Mail & Preflight Live Check khi Reg TikTok

## 1. Bối cảnh & Chính sách Mail (Gmail vs Hotmail OAuth2)
- **Tạm thời tắt @gmail.com khi reg TikTok:**
  - Gmail thường xuyên bị nghẽn nhận mã OTP từ TikTok, checkpoint danh tính hoặc die đột ngột giữa ca chạy, gây ra lỗi diện rộng `[7c][BLOCKED_GMAIL_OTP_TIMEOUT]`.
  - Cấu hình chuẩn hiện tại:
    - Trong `D:/Taadaa/Tiktok_Reg/scripts/tiktok_target_eligibility.py`:
      ```python
      SUPPORTED_DOMAINS = ("@hotmail.com", "@outlook.com", "@live.com")
      ```
    - Trong `D:/Taadaa/tools/ensure_row_accounts.py`: Bỏ qua các dòng có đuôi `@gmail.com` khi duyệt mail có sẵn.

## 2. Preflight Live Check 2 lớp cho Gmail (Khi bật lại Gmail)
- **Vấn đề đã xử lý:** Trước đây `_detect_clean.py` chỉ đối soát tĩnh trong workbook và tạo file `tiktok_reg_clean_targets.json` từ trước mà không gọi live check, dẫn đến việc `_run_all_targets.py` bốc phải mail Gmail đã DIE từ lâu.
- **Cơ chế 2 lớp chuẩn:**
  1. `_detect_clean.py` BẮT BUỘC gọi `filter_live_gmail_targets()` qua API `checkmail.live` ngay từ bước phát hiện target.
  2. Khi phát hiện Gmail DIE (`False`):
     - Loại bỏ ngay khỏi danh sách targets.
     - Tự động xóa mail DIE khỏi file nguồn `gmail_clean_v2.xlsx` (kèm backup tự động `workbook-backups/`).
     - Tự động gọi `remove_device_account_fast()` gỡ sạch tài khoản Google trên máy thật qua ADB UI/dumpsys.

## 3. Quy trình Tự động Cấp bù Hotmail OAuth2 cho Máy thiếu Mail
- Khi chuyển đổi từ Gmail sang Hotmail, các máy chỉ có Gmail trong kho sẽ bị thiếu mail hợp lệ.
- Lệnh mua và nạp tự động qua tool `buy_hotmail.py`:
  ```bash
  python D:/Taadaa/tools/buy_hotmail.py --append-kibe <N> --target-machines "3,8,20,..."
  ```
- **Nhà cung cấp:** Ưu tiên `boxtaikhoan`, tự động fallback sang `clonefbig`.
- **Verify tự động:** Bắt buộc verify access token Microsoft Graph API LIVE trước khi append vào workbook.
- Sau khi append, chạy lại `_detect_clean.py` để xác nhận 100% targets là `provider=hotmail`.
