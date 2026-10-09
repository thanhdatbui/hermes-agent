# Google Authenticator 2FA Provisioning via Android Device UI

## Mục tiêu
Tự động bật 2FA Google Authenticator trên thiết bị Android S7 cho tài khoản Google / Gmail (thường dùng sau khi đăng ký tài khoản mới hoặc bảo mật tài khoản farm).

## Pipeline thực thi

1. **Preflight & Device Lock**:
   - Đảm bảo thiết bị kết nối ADB ổn định (`adb -s <serial> get-state`).
   - Kiểm tra tài khoản tồn tại trên thiết bị: `adb -s <serial> shell dumpsys account | grep com.google`.
   - Tra cứu thông tin tài khoản (password, trạng thái) trong workbook `gmail_clean_v2.xlsx`.

2. **Khởi tạo & Điều hướng UI**:
   - Wakeup & unlock screen: `keyevent 224`, `wm dismiss-keyguard`, `keyevent 82`.
   - Mở Cài đặt Tài khoản hoặc Gmail:
     `am start -a android.settings.SYNC_SETTINGS` hoặc mở Gmail app.
   - Điều hướng tới: Cài đặt Google -> Quản lý Tài khoản Google -> tab **Bảo mật** (Security).
   - Chọn mục **Xác minh 2 bước** (2-Step Verification).

3. **Lấy Secret Key & Xác nhận OTP**:
   - Khi Google hiển thị màn hình thêm ứng dụng Authenticator (QR code):
     - Bấm liên kết *"Không thể quét mã QR?"* / *"Can't scan it?"*.
     - Trích xuất Secret Key (chuỗi base32 16-32 ký tự) hiển thị trên màn hình qua XML dump hoặc copy to clipboard.
   - Dùng `pyotp.TOTP(secret_key).now()` để sinh mã xác minh 6 số tức thì (mã chỉ có hiệu lực 30s).
   - Nhập 6 số vào ô xác thực và bấm Tiếp theo / Xác nhận.
   - Xác minh thông báo thành công: "Đã bật tính năng Xác minh 2 bước".

4. **Lưu trữ & Khóa dữ liệu**:
   - Cập nhật Secret Key vào cột `2FA` của workbook quản lý (`gmail_clean_v2.xlsx`).
   - Phím HOME (`keyevent 3`) để trả máy về màn hình launcher sạch sẽ.

## Xử lý sự cố thường gặp
- **UiAutomator dump trả về code 137 / Killed**:
  - Dùng lệnh giải phóng:
    `adb shell "pkill -9 -f atx-agent; pkill -9 -f com.github.uiautomator.stub.Stub; am force-stop com.github.uiautomator; uiautomator quit"`
  - Nếu vẫn kẹt, khởi chạy `atx-agent server -d` và query dump qua port 7912.
