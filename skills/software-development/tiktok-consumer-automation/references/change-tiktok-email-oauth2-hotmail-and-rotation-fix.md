# Quy trình Đổi Email TikTok sang Hotmail (XOAUTH2 IMAP OTP) & Quy chuẩn Khóa Xoay / Check Live

## 1. Cơ chế Bảo mật Đổi Email TikTok trên Thiết bị Đang Đăng Nhập
* **Đổi Email không cần Mật khẩu cũ / OTP Mail cũ**:
  * Khi thiết bị đã đăng nhập sẵn TikTok, vào `Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Thông tin tài khoản` -> `Email` -> `Thay đổi email`.
  * TikTok chỉ yêu cầu:
    1. Nhập địa chỉ Email mới (`Hotmail`).
    2. Nhập mã xác minh 6 số gửi về chính **Email mới**.
  * Không đòi hỏi mật khẩu TikTok hiện tại hay xác nhận từ Gmail cũ (rất hữu ích khi Gmail liên kết cũ bị quét die / dính Captcha bot).
* **Quy tắc an toàn 24 giờ sau khi đổi Email**:
  * Sau khi đổi email thành công, hệ thống Risk Engine của TikTok giám sát chặt chẽ.
  * **CẤM** đổi mật khẩu ngay lập tức trong vòng 24 giờ để tránh bị kích hoạt checkpoint bất thường hoặc khóa tính năng bảo mật.

## 2. Giải mã và Đọc OTP Hotmail tự động qua Microsoft OAuth2 IMAP
* **Lấy Access Token từ Refresh Token**:
  * Token Endpoint: `https://login.microsoftonline.com/common/oauth2/v2.0/token`
  * Scopes: `https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/POP.AccessAsUser.All offline_access`
* **Xác thực IMAP XOAUTH2**:
  * Host: `outlook.office365.com`, Port: `993` (SSL).
  * Chuỗi xác thực: `user=<email>\x01auth=Bearer <access_token>\x01\x01`
  * Dùng `imap.authenticate('XOAUTH2', ...)` để đọc hộp thư đến `INBOX` và lọc mã OTP 6 số từ `TikTok <register@account.tiktok.com>`.
* **Script mẫu thực thi chuẩn**: `D:\Taadaa\tiktok-log-in\scripts\change_tiktok_email_flow.py` (điều hướng bằng ATX XML-First, port 7912).

## 3. Quy chuẩn Khóa Màn Hình Dọc (Force Portrait)
* Trên máy Samsung Galaxy (S7), chỉ dùng `settings put system accelerometer_rotation 0` là không đủ vì khi mở app / bật bàn phím IME thì cảm biến vẫn có thể tự xoay ngang (`mCurrentRotation=1`).
* **Bộ lệnh bắt buộc phải chạy đồng thời**:
  ```bash
  settings put system accelerometer_rotation 0
  settings put system user_rotation 0
  content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
  content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
  ```

## 4. Xử lý khi Check Live Gmail dính Captcha Bot
* Nếu tài khoản Google/Gmail trên máy báo lỗi đồng bộ (`Sync failed`) và hiện màn hình *"Xác minh danh tính của bạn - Xác nhận bạn không phải là rô-bốt"*:
  1. Xóa tài khoản Gmail lỗi khỏi máy: `android.settings.SYNC_SETTINGS` -> Chọn Gmail -> Bấm `XÓA TÀI KHOẢN`.
  2. Xóa dòng Gmail lỗi khỏi `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  3. Cập nhật tài khoản thay thế (Hotmail mới) vào `taikhoan_dat_v2_updated .xlsx` và `gmail_clean_v2.xlsx`.
