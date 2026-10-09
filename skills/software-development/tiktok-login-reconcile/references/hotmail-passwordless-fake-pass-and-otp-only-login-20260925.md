# Hotmail Passwordless Placeholder Password Trap & --otp-only Fast Login (2026-09-25)

## 1. Bản chất sự cố "Mật khẩu sai" trên nick Hotmail có PASS trong Excel
- **Nguyên nhân gốc rễ**: Trước ngày 17/09/2026, hàm `ensure_profile_completed_and_track` trong `social_reg_v1.py` có fallback:
  ```python
  tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")
  ```
  Khi tài khoản đăng ký bằng Hotmail qua cơ chế **Magic Link / OTP Hotmail**, TikTok sau khi xác thực email sẽ đưa thẳng vào app mà **hoàn toàn KHÔNG xuất hiện màn hình tạo mật khẩu**. Biến `tiktok_pw` rỗng làm hàm tự sinh mật khẩu ngẫu nhiên và ghi vào **Cột D (PASS)** file Excel `taikhoan_dat_v2_updated .xlsx`.
- **Hệ quả**: Mật khẩu trong Excel là mật khẩu placeholder chưa từng được gửi hay lưu trên máy chủ TikTok.
- **Phân biệt Gmail vs Hotmail**:
  - **Gmail**: Reg form chuẩn trên app TikTok có bước nhập mật khẩu -> Mật khẩu cột D là **MẬT KHẨU THẬT**.
  - **Hotmail / Outlook**: Reg Magic Link / OTP không có màn hình tạo mật khẩu -> Mật khẩu cột D (trước 17/09) là **MẬT KHẨU ẢO/PLACEHOLDER**.

## 2. Bẫy Auto-Login & Nguy cơ Khóa Tài Khoản
- Khi ca nuôi thiếu nick trong Switcher, `tiktok_login_v1.py` đọc Excel thấy có ID + PASS cột D nên mặc định chọn đăng nhập bằng `ID + PASS`.
- TikTok báo lỗi: *"Sai tài khoản hoặc mật khẩu. Còn 1 lần nhập. Hãy thử lại."*
- Nếu tiếp tục retry ID+Pass sẽ bị khóa đăng nhập tạm thời trên thiết bị.

## 3. Giải pháp: Cờ `--otp-only` trong `tiktok_login_v1.py`
Đã cập nhật `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py` hỗ trợ cờ `--otp-only`:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <EMAIL_HOẶC_ID> --otp-only --allow-parent-lock
```
- **Hành vi**:
  1. `login_target` ép sử dụng `login_email` (thay vì ID).
  2. Bỏ qua nhập mật khẩu tĩnh; nếu TikTok mở màn hình nhập mật khẩu, script tự động bấm *"Đăng nhập bằng mã"* / *"Gửi mã"*.
  3. Khi ở màn hình OTP, **CẤM** bấm *"Đăng nhập bằng mật khẩu"* (tránh vòng lặp quay lại pass sai).
  4. Lấy mã OTP 6 số từ Microsoft Graph API hoặc IMAP nạp vào TikTok để đăng nhập thẳng vào Switcher.

## 4. Chuỗi chuẩn hóa sau khi nạp nick
Ngay sau khi đăng nhập thành công vào app bằng OTP:
1. Chạy `tiktok-add-bao-mat-f2a` (Phase B):
   - Kích hoạt 2FA Authenticator (TOTP) -> Lưu Secret Key vào **Cột E**.
   - Vào Cài đặt bảo mật đổi sang mật khẩu ngẫu nhiên mạnh mới -> Cập nhật mật khẩu thật vào **Cột D**.
   - Tắt/hạ các popup sau 2FA ("Thêm điện thoại", "Thiết bị tin cậy").
