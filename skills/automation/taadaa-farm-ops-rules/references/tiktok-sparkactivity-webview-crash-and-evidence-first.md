# TikTok v46+ Suspicious Login SparkActivity WebView Crash & Failure Evidence First

## 1. Hiện Tượng SparkActivity Bị Trắng Màn Hình
- Khi đăng nhập tài khoản TikTok trên thiết bị mới hoặc IP lạ, TikTok kích hoạt cơ chế `suspicious_login`:
  ```text
  Activity: com.ss.android.ugc.trill/com.bytedance.hybrid.spark.page.SparkActivity
  URL: https://inapp.tiktokv.com/ucenter_web/idv_inapp/verification?enter_from=suspicious_login...
  ```
- Trên các máy Samsung Galaxy S7 chạy Android 8.0, nhân mặc định của `com.google.android.webview` và `com.android.chrome` là **v70.0.3538.110**.
- Web nội bộ của TikTok sử dụng cú pháp JavaScript ES2020+ (Optional Chaining `?.` hoặc Nullish Coalescing `??`).
- Logcat ghi nhận lỗi JavaScript crash:
  ```text
  Uncaught SyntaxError: Unexpected token ?
  source: https://sf16-website-login.neutral.ttwstatic.com/.../vendor.e60f8a52.js (1)
  ```
- **Hậu quả:** Toàn bộ giao diện JS của TikTok bị crash ngay lúc khởi tạo ➔ Trang web bị **trắng xóa hoàn toàn**, không thể render Captcha hay nút xác nhận để vào tài khoản.

## 2. Giải Pháp Kỹ Thuật
1. **Với Hotmail có OAuth Token**:
   - Sử dụng `hotmail_provider.py` gọi Microsoft Graph API đọc OTP trực tiếp qua `refresh_token + client_id`.
   - KHÔNG bắt máy farm mở app Outlook/Gmail để nhận OTP khi đã có OAuth token.
2. **Cập nhật nhân WebView / Chrome**:
   - Cập nhật Chrome / Android System WebView lên phiên bản tối thiểu v80+ để hỗ trợ cú pháp JS hiện đại của TikTok.

## 3. Quy Tắc Kỷ Luật Bắt Buộc: Failure Evidence First
- **Cấm chụp ảnh sau khi cleanup/về HOME**: Khi gặp lỗi (màn hình trắng, lỗi PIN, captcha, timeout), Agent BẮT BUỘC chụp ảnh screencap TẠI CHỖ ngay millisecond phát hiện lỗi, TRƯỚC KHI chạy bất kỳ lệnh cleanup, force-stop, hay input keyevent 3 về HOME nào.
- **Validation**: Ảnh đính kèm `MEDIA:<path>` trong báo cáo lỗi bắt buộc có `foreground_package` là app xảy ra lỗi (TikTok, Outlook...). Cấm tuyệt đối gửi ảnh launcher HOME làm bằng chứng lỗi.
