# Checkmail.live Integration & On-Device Google Health Trap (2026-09-12)

## 1. Cạm bẫy On-Device Google Health False-Positive
Khi đăng ký TikTok bằng Gmail, nếu đợi OTP 150s và bấm "Gửi lại mã" mà hộp thư vẫn trống:
- **Cơ chế cũ (SAI LẦM):** Chạy `check_google_account_health_from_gmail` trên điện thoại Android (mở Google Account Settings xem có bị bắt giải CAPTCHA hay không).
- **Hậu quả:** Google thường vô hiệu hóa / disable tài khoản ngầm từ backend mà **không hiện popup CAPTCHA rõ ràng trên UI app Gmail**. App Gmail chỉ im lặng ngừng sync mail mới. Script trên điện thoại ngộ nhận `reason=target_account_not_verified (Google Account vẫn LIVE, nhưng TikTok không phát OTP)` và đổ thừa cho TikTok rate-limit.
- **Thực tế nghiệm thu (2026-09-12):** Kiểm tra 17 Gmail fail OTP bằng công cụ độc lập thì **16/17 mail đã DIE (`[die]`) trên hệ thống Google**.

## 2. Quy chuẩn Check Live Gmail chuẩn (User chỉ định 2026-09-12)
- **Nguồn chuẩn:** Dùng trang `checkmail.live` đã được tích hợp từ repo `site ban hang clone` (`D:/Taadaa/tools/check_gmail_live_fast.py`).
- **Cấu hình thực thi:** Chạy Playwright Chromium với Farm Mobile Proxy (`http://test.taadaa.click:5101`, auth `mobi1:TaadaaMobi#2026!`) và cờ `--disable-blink-features=AutomationControlled` để vượt Cloudflare Turnstile tự động.
- **Quy trình xử lý khi phát hiện DIE:**
  1. Khi TikTok không phát OTP về hộp thư: Gọi `check_gmail_is_live(email)` từ `D:/Taadaa/tools/check_gmail_live_fast.py`.
  2. Nếu kết quả `[die]`:
     - Xóa ngay dòng mail đó ra khỏi kho `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` (có sao lưu backup timestamp trước khi ghi).
     - Ghi nhận trạng thái vào sheet `Audit Pending` trong `taikhoan_dat_v2_updated .xlsx`.
     - Ném ngoại lệ `RuntimeError(f"[7c][google_captcha_dead_mail] {email} DIE (xác nhận bởi checkmail.live), đã xóa khỏi source")` để kết thúc target và nhả máy.
  3. Chỉ khi `checkmail.live` xác nhận `[live]` thì mới kết luận là lỗi tạm thời từ phía TikTok.

## 3. Thống kê tỷ lệ DIE của Gmail mới reg gần đây
- Gmail mới tạo trong vòng 3–7 ngày (đặc biệt qua chuỗi tự động ban đêm `register gmail`) có tỷ lệ bị Google quét khóa sau ngâm lên tới **~70%** (14/20 mail).
- Trước khi chạy mẻ reg TikTok quy mô lớn, nên quét dọn hàng loạt (batch purge) toàn bộ kho `gmail_clean_v2.xlsx` qua `checkmail.live` để loại bỏ sạch các tài khoản DIE, tránh việc hàng chục máy chạy mở app TikTok chờ OTP vô ích.
