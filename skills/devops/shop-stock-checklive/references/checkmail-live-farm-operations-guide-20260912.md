# Checkmail.live Integration for Gmail Farm Operations & Registration (2026-09-12)

## 1. Nguồn gốc & Phạm vi ứng dụng
- **Công cụ:** `checkmail.live` (sử dụng Playwright Chromium headless/headful qua Farm Mobile Proxy `test.taadaa.click:5101`, auth `mobi1:TaadaaMobi#2026!`).
- **Mục đích:** Thay thế hoàn toàn cơ chế on-device Google Health check (`check_google_account_health_from_gmail`) trong các script tự động hóa nông trại (`Tiktok_Reg`, `register gmail`, kiểm kho).
- **Vị trí script tái sử dụng:** 
  - Canonical Batch Runner chuẩn (tự login, tự tạo account ephemeral, parse kết quả): `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`.
  - Single-account helper: `D:/Taadaa/tools/check_gmail_live_fast.py` (hàm `check_gmail_is_live(email)`).
  - **Lưu ý thực thi sống còn:** Trang `checkmail.live` yêu cầu session đăng nhập có `api-key` trên DOM. CẤM tự ý mở browser chay submit form mà không login vì nút Check sẽ trơ ra hoặc báo alert `You are not logged in`. Luôn gọi hàm `ensure_logged_in_page()` và `check_emails_live_batch()` từ `run_checkmail_kibe_farm.py`.

## 2. Bài học từ sự cố False-Positive on-device Google Health (2026-09-12)
- Khi app TikTok gửi OTP nhưng hộp thư Gmail trống không có mail:
  - Cơ chế on-device cũ chỉ kiểm tra xem app Google Account có hiện popup giải CAPTCHA hay không.
  - Khi Google khóa/disable tài khoản ngầm từ backend, app không nhảy CAPTCHA mà chỉ ngừng nhận mail -> on-device check ngộ nhận tài khoản "vẫn LIVE" và kết luận sai lệch do TikTok rate-limit.
  - Thực tế quét độc lập qua `checkmail.live`: **16/17 mail fail OTP đều đã DIE (`[die]`)**.

## 3. Tỷ lệ suy hao (DIE) của Gmail mới reg sau ngâm & Quy tắc khắc phục
- Các tài khoản Gmail mới reg qua quy trình tự động trong vòng 3–7 ngày có tỷ lệ bị Google quét khóa sau ngâm lên tới **70%** (14/20 mail trong tháng 9/2026).
- Việc định kỳ quét dọn (batch purge) toàn bộ kho `gmail_clean_v2.xlsx` qua `checkmail.live` giúp loại bỏ triệt để tài khoản DIE, tránh lãng phí thời gian mở app chờ OTP trên thiết bị farm.

## 4. Quy trình dọn dẹp Gmail DIE trên thiết bị Android
- Khi xóa Gmail DIE khỏi Excel, **BẮT BUỘC phải xóa tài khoản DIE đó khỏi máy Android** trước khi bắt đầu ca reg tiếp theo:
  - Đọc danh sách Gmail DIE đã phân loại theo máy từ `D:/Taadaa/runtime/kibe/gmail_die_by_machine.json`.
  - Sử dụng module `preflight_s7_rolling_cleanup.py` (hàm `remove_account_adb()`) mở `android.settings.SYNC_SETTINGS` -> gỡ tài khoản Google tương ứng.
  - Sau khi dọn sạch slot chết, thiết bị mới được phép tiếp nhận lượt tạo tài khoản mới.

## 5. Chiến lược chống Google quét khóa khi Reg Gmail
1. **Bật 2FA (Google Authenticator) thay vì dùng chung Mail khôi phục:**
   - Dùng chung 1 mail khôi phục khiến các máy tranh nhau lấy OTP, gây nghẽn và chuỗi tài khoản bị liên đới khóa hàng loạt.
   - Bật 2FA sinh Secret Key Base32 độc lập cho từng tài khoản, nâng cấp profile lên mức High Security Trust.
2. **Quy tắc điều phối 15 máy:**
   - CẤM đổi IP trước khi reg.
   - Pick 15 máy thuộc các cổng proxy KHÁC NHAU để đảm bảo 15 request ra từ 15 IP độc lập.
   - Tăng cường random hóa họ, tên đệm (1-2 từ), tên chính, từ ngữ tự nhiên và hậu tố nghiệp vụ kèm salt 3-5 ký tự để triệt tiêu bot pattern.
