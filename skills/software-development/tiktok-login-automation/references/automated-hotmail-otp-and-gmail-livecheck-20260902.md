# Quy Trình Đọc OTP Hotmail Tự Động & Check Live Gmail Khi Đăng Nhập TikTok (2026-09-02)

## 1. Cơ Chế Đọc OTP Hotmail Tự Động (CẤM HỎI USER)
Khi TikTok yêu cầu xác minh thiết bị mới gửi OTP 6 số về `@hotmail.com` (ví dụ `LyndiaSchlesinger2198@hotmail.com` trên Máy 10):
- **Cơ chế 1: Đọc qua Outlook App trên máy Android:**
  - Package: `com.microsoft.office.outlook`.
  - Gọi hàm: `read_tiktok_otp_from_outlook_app(device_id, email, stt)` trong `D:\Taadaa\Tiktok_Reg\hotmail_provider.py`.
  - Runner tự động switch sang app Outlook trên máy, mở email mới nhất từ TikTok, trích xuất OTP 6 số và chuyển lại TikTok để điền qua ADB.
- **Cơ chế 2: Đọc qua Graph API / XOAUTH2 Token:**
  - File token: `gmail_clean_v2.xlsx` hoặc `D:\Taadaa\Hotmail\tokens\`.
  - Gọi hàm: `read_tiktok_otp_from_graph_token(device_id, email, token=rt, client_id=cid, stt=stt)`.
- **Quy tắc tuyệt đối:** CẤM dừng tiến trình để hỏi user xin mã OTP khi tài khoản là Hotmail đã có trong hệ thống Outlook / Graph API.

---

## 2. Quy Trình Xử Lý Timeout OTP Gmail (`BLOCKED_GMAIL_OTP_TIMEOUT`)
Khi đăng nhập TikTok yêu cầu OTP Gmail và runner bị timeout không thấy mail mới về:
1. **Kiểm tra Live Gmail siêu tốc:**
   - Sử dụng Chrome CDP port 9222 (`C:\Users\Kibe\AppData\Local\hermes\browser_profile`) chạy probe qua `checkmail.live` trong 1-2 giây.
   - Hoặc gọi `run_google_live_check` từ `automation_core.google_health` / `add mail khoi phuc`.
2. **Phân nhánh hành động:**
   - **Nếu Gmail LIVE:** Không dừng lại và không tự ý kết luận mail die. Thực hiện pull-to-refresh (F5 vuốt xuống) trên app Gmail (`com.google.android.gm`) để ép Android đồng bộ kéo mail mới về, sau đó đọc lại mã.
   - **Nếu Gmail DIE / CAPTCHA:** Chụp ảnh màn hình hiện trường, báo cáo user và tiến hành dọn dẹp theo quy trình.

---

## 3. Wi-Fi Proxy Router (MikroTik / Singbox) Thay Thế Hoàn Toàn ViChanger
- Farm 160 máy đã chuyển 100% sang Wi-Fi Proxy Router.
- Không còn cài đặt / bật app ViChanger VPN trên điện thoại.
- Mọi script kiểm tra `require_android_vpn` trên Android phải được bypass để tránh lỗi giả `VICHANGER_VPN_NOT_CONNECTED`.
