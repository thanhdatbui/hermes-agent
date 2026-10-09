# Quy Chuẩn Check Live Gmail Bằng checkmail.live & Xử Lý Mail DIE (Tiktok_Reg)

## 1. Vấn Đề On-Device Health Check Cũ
- Khi Google khóa/vô hiệu hóa tài khoản ngầm, app Gmail trên Android không văng thông báo rõ ràng.
- `check_google_account_health_from_gmail` kết luận nhầm là tài khoản LIVE và quy lỗi cho TikTok không gửi OTP.

## 2. Chuẩn Hóa Mới (checkmail.live)
- Khi OTP không về ở Bước 7c: Script gọi `check_gmail_is_live(email)` từ `D:/Taadaa/tools/check_gmail_live_fast.py` (Playwright + mobile proxy kết nối `checkmail.live`).
- Nếu kết quả là DIE:
  1. Gọi `remove_captcha_dead_email_from_source(email)` xóa ngay dòng khỏi `gmail_clean_v2.xlsx`.
  2. Ghi nhận cách ly vào sheet `Audit Pending` trong `taikhoan_dat_v2_updated .xlsx`.
  3. Ghi nhận máy vào danh sách cần dọn tài khoản Google qua `preflight_s7_rolling_cleanup.py`.
  4. Dừng flow đăng ký ngay lập tức để chuyển target.
