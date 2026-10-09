# Hotmail Recovery via Gmail thanhdatbui1995 & Web Legacy Chrome Flow (2026-09-17)

## 1. Vấn Đề App Outlook Android Kẹt Màn Hình
- Trên một số máy Samsung S7 mới hoặc WebView cũ, app Outlook Android (`com.microsoft.office.outlook`) khi nhập email hotmail cũ thường bị redirect nhầm sang màn hình tạo tài khoản mới: `Tạo tài khoản Microsoft của bạn (@outlook.com.vn)`.
- Khi thử login trực tiếp qua app, Microsoft báo `Mật khẩu đó không đúng với tài khoản Microsoft của bạn` do tài khoản đã qua đợt đổi thông tin định kỳ hoặc sign-out thiết bị.

## 2. Luồng Canonical Web Legacy Qua Chrome Android
- Thay vì dùng app Outlook, chuyển sang dùng Google Chrome Android (`com.android.chrome`):
  `https://login.live.com/login.srf` hoặc hàm `login_web_legacy` trong `flows/hotmail_login.py`.
- **Quan trọng:** File mapping `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (sheet `Accounts`) phải được cập nhật đúng Device ID/Serial mới của máy, tránh bị chặn bởi `MACHINE_SERIAL_MISMATCH`.

## 3. Khôi Phục Hotmail Qua Email Khôi Phục thanhdatbui1995@gmail.com
1. Khi form Microsoft báo sai pass, trên màn hình hiện link:
   `Gửi mã đến th*****@gmail.com`
2. Tap vào link đó -> Màn hình chuyển sang form:
   `Xác minh email của bạn: Chúng tôi sẽ gửi mã đến th*****@gmail.com`
3. Nhập đầy đủ email: `thanhdatbui1995@gmail.com` -> Bấm `Gửi mã`.
4. Gọi IMAP Gmail bắt mã OTP Microsoft:
   - IMAP host: `imap.gmail.com:993`
   - User: `thanhdatbui1995@gmail.com` (biến môi trường `OTP_MAIL_USER`)
   - Password: App password (biến môi trường `OTP_MAIL_APP_PASSWORD`)
   - Subject: `Mã dùng một lần của bạn` từ `account-security-noreply@accountprotection.microsoft.com`
   - OTP gồm 6 chữ số (ví dụ: `755030`).
5. Điền 6 chữ số vào 6 ô input trên web Microsoft (mỗi ô cách nhau ~144px).
6. Khi hiện popup Passkey: Bấm Android Back (`keyevent 4`) 1 lần để bỏ qua.
7. Màn hình hiện `Duy trì đăng nhập?`: Bấm vào nút `Có` (tọa độ tâm khoảng `(540, 1629)`).
8. Trình duyệt chuyển thẳng vào `https://outlook.live.com/mail/0/inbox` -> Đăng nhập thành công và đọc được toàn bộ email/OTP của TikTok.
