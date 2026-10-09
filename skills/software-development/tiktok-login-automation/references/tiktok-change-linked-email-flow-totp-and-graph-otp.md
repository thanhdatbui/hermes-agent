# Quy trình đổi Email liên kết TikTok sang Hotmail mới & Đọc OTP Graph API (2026-09-18)

## 1. Mục tiêu & Bối cảnh
- Các tài khoản TikTok dính líu đến email cũ / email khoalee không truy cập được cần được đổi sang Hotmail mới mua qua API.
- Tự động hóa hoàn toàn từ: Cấp phát Hotmail có OAuth2 $\rightarrow$ Xác minh danh tính qua TOTP Secret Key $\rightarrow$ Đổi email trên TikTok UI $\rightarrow$ Đọc mã OTP 6 số qua Graph API $\rightarrow$ Cập nhật Excel.

## 2. Các bước triển khai chuẩn E2E

### Bước 1: Mua Hotmail mới có Graph OAuth2 Token
- Gọi tool mua tự động:
  ```bash
  "D:/Taadaa/python-envs/automation/Scripts/python.exe" D:/Taadaa/tools/buy_hotmail.py --buy 1 --target-file <path_to_mail_txt>
  ```
- Tool tự động ưu tiên `boxtaikhoan` và fallback sang `clonefbig`.
- Định dạng xuất chuẩn: `email|password|refresh_token|client_id|recovery_mail`.
- Access Token Graph OAuth2 được verify LIVE ngay khi mua.

### Bước 2: Đọc mã OTP qua Microsoft Graph API
- Flow đổi token và đọc thư:
  1. Đổi `refresh_token` $\rightarrow$ `access_token`:
     - Endpoint: `https://login.microsoftonline.com/common/oauth2/v2.0/token`
     - Params: `client_id`, `grant_type=refresh_token`, `refresh_token`, `scope="https://graph.microsoft.com/Mail.Read offline_access"`
  2. Lấy danh sách thư mới nhất:
     - Endpoint: `https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,from,receivedDateTime&$orderby=receivedDateTime desc`
     - Header: `Authorization: Bearer <access_token>`
  3. Trích xuất mã OTP 6 số: Regex `\b\d{6}\b` trong Subject hoặc Body thư của TikTok (`no-reply@tiktok.com` / `TikTok`).
- Đã có sẵn script kiểm tra độc lập: `D:\Taadaa\Hotmail\scripts\test_graph_token.py`.

### Bước 3: Điều hướng TikTok UI
- Mở TikTok: `com.ss.android.ugc.trill` (`MainActivity`).
- Vào tab `Hồ sơ` (Profile).
- Bấm Menu 3 gạch (`Menu hồ sơ` / Top-right overflow).
- Chọn `Cài đặt và quyền riêng tư` $\rightarrow$ `Tài khoản` $\rightarrow$ `Thông tin người dùng` $\rightarrow$ `Email`.
- Chọn `Thay đổi email` (Change Email).

### Bước 4: Vượt Gate Xác minh Danh tính bằng 2FA TOTP
- Khi TikTok yêu cầu xác minh chủ sở hữu tài khoản:
  - Sử dụng TOTP Secret Key 32 ký tự (Cột E trong Excel).
  - Tạo mã xác minh 6 số:
    ```python
    import pyotp
    code = pyotp.TOTP(secret_2fa.strip()).now()
    ```
  - Nhập mã vào ô xác minh trên app TikTok. Tuyệt đối không chọn phương thức gửi OTP về email cũ để tránh bẫy kẹt mail khoalee.

### Bước 5: Điền Hotmail mới & Đọc OTP điền vào TikTok
- Nhập địa chỉ Hotmail mới mua.
- Bấm `Gửi mã`.
- Chờ 3-5s, gọi Graph API đọc mã OTP 6 số.
- Nhập mã vào TikTok và bấm hoàn tất.

### Bước 6: Cập nhật Excel & Chụp ảnh minh chứng
- Cập nhật dòng tương ứng trong file `taikhoan_dat_v2_updated .xlsx`:
  - Cột F (Email): Hotmail mới.
  - Cột G (Pass Mail): Mật khẩu Hotmail mới.
- Chụp ảnh màn hình thiết bị xác nhận đã đổi thành công lưu tại `D:\Taadaa\m<machine>_after_email.png`.

## 3. Pitfalls kỹ thuật cần nhớ
- **Windows ADB Path trong MSYS/Bash**: Binary `adb.exe` là Win32 PE binary. Khi chạy lệnh `adb pull` hoặc `adb push` từ môi trường bash (Git Bash/MSYS), đường dẫn đích/nguồn trên máy tính phải dùng format Windows (`D:/Taadaa/...` hoặc `D:\Taadaa\...`). Nếu truyền format POSIX `/d/Taadaa/...`, ADB sẽ báo lỗi `cannot create file/directory ... No such file or directory`.
- **Scope Graph API**: Token của Hotmail mua qua API chỉ có scope `Mail.Read`, không có `User.Read` hay `Mail.Send`. Tránh gọi `/v1.0/me` vì sẽ bị `401 UnknownError`. Chỉ gọi trực tiếp `/v1.0/me/messages`.
