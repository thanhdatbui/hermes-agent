# 2FA Authenticator Priority & GPM Hotmail OTP Fallback

## 1. Ưu tiên 2FA Authenticator Trước, Fallback Email OTP Sau
- **Nguyên tắc**: Khi TikTok hiển thị màn hình `Xác minh 2 bước`, mặc định TikTok có thể hiển thị gửi mã về Email (`a***6@gmail.com`).
- **Xử lý**:
  - Không điền nhầm TOTP vào ô Email OTP.
  - Bắt buộc kiểm tra và bấm nút `Sử dụng phương thức khác >` (`Use another method`).
  - Chọn `Trình xác thực` / `Ứng dụng xác thực` (`Authenticator app`).
  - Điền mã TOTP 6 số sinh từ khóa secret Base32 đã lưu trong database.
  - Chỉ khi tài khoản thực sự không có 2FA Authenticator hoặc không đổi được phương thức mới chuyển sang đọc Email OTP.

## 2. Xử lý màn hình sau Auth (Post-Auth Bio Screen)
- Sau khi xác thực 2FA/Password, TikTok có thể bung màn hình `Tiểu sử` (`Bio screen`: *"Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào"*).
- Bắt buộc bấm `Hủy` / `Bỏ qua` (tọa độ fallback `(95, 138)`) để thoát màn hình Tiểu sử và vào thẳng Profile/Feed, tránh kẹt timeout ở bước post-auth.

## 3. Kiến trúc Đọc OTP Hotmail 3 Tầng
Khi tài khoản cần đọc mã OTP từ Hotmail:
1. **Tầng 1 (Ưu tiên số 1 - O(1))**: `read_tiktok_otp_from_graph_token` sử dụng Microsoft Graph API token trên PC.
2. **Tầng 2 (Dự phòng Web CDP)**: `read_tiktok_otp_from_gpm_profile` (tại `D:/Taadaa/Hotmail/scripts/read_otp_gpm.py`) kết nối Profile GPM-Login qua Playwright CDP để đọc trực tiếp hòm thư Outlook trên web, có `try...finally` đóng profile đảm bảo không leak RAM.
3. **Tầng 3 (Dự phòng di động)**: `read_tiktok_otp_from_outlook_app` mở ứng dụng Outlook trên thiết bị Android.
