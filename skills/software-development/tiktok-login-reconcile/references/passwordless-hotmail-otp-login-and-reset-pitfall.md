# Passwordless Hotmail OTP Login & Multi-Account Reset Pitfall (2026-09-02)

## 1. Bản chất tài khoản TikTok Reg qua Hotmail Passwordless
- Các tài khoản TikTok đăng ký qua luồng Hotmail (tháng 8/2026) sử dụng cơ chế **OTP / Magic Link** không qua bước tạo mật khẩu tĩnh ban đầu.
- Dù trên bảng Excel master (`taikhoan_dat_v2_updated .xlsx`) có thể đã sinh chuỗi mật khẩu ngẫu nhiên để đồng bộ dữ liệu, server TikTok chưa từng lưu mật khẩu này.
- Khi đăng nhập bằng mật khẩu từ Excel, TikTok sẽ báo lỗi `Mật khẩu sai`.

---

## 2. Quy trình Đăng nhập Chuẩn qua XOAUTH2 IMAP
1. **Khởi động luồng đăng nhập:**
   - Chọn *Đăng nhập bằng Email/Tên người dùng* trên app TikTok.
   - Nhập trực tiếp địa chỉ email Hotmail (ví dụ: `LyndiaSchlesinger2198@hotmail.com`).
   - TikTok tự động nhận diện tài khoản passwordless và chuyển sang màn hình *"Xác minh email: Nhập mã được gửi đến..."*.
2. **Tự động đọc OTP qua Microsoft XOAUTH2:**
   - Lấy `refresh_token` và `client_id` từ `gmail_clean_v2.xlsx` (hoặc backup).
   - Gửi request lấy `access_token` từ Microsoft OAuth2:
     ```python
     POST https://login.microsoftonline.com/common/oauth2/v2.0/token
     grant_type=refresh_token&scope=https://outlook.office.com/IMAP.AccessAsUser.All offline_access
     ```
   - Kết nối IMAP `outlook.office365.com:993`, authenticate bằng `XOAUTH2`:
     ```python
     auth_string = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
     mail.authenticate("XOAUTH2", lambda x: auth_string.encode())
     ```
   - Lấy mã OTP 6 số mới nhất từ Subject hoặc Body mail gửi từ `register@account.tiktok.com`.
3. **Hoàn tất đăng nhập:**
   - Nhập OTP vào app để hoàn tất nạp session lên switcher.

---

## 3. Luồng "Đặt lại mật khẩu" (Forgot Password) & Cơ chế Xác minh Danh tính Chéo
- **Quy trình user hướng dẫn để tạo pass mới cho tài khoản passwordless:**
  1. Vào *Thêm tài khoản* > *Đăng nhập bằng Email/ID* > Nhập ID nick cần tạo pass.
  2. Tại màn hình mật khẩu, bấm *"Bạn cần trợ giúp đăng nhập?"* > Chọn *"Đặt lại mật khẩu bằng email"*.
  3. Nhập email của nick > Lấy mã OTP 6 số qua XOAUTH2 IMAP và nhập vào app.
  4. TikTok hiển thị màn hình webview *"Xác minh danh tính: Xác minh đó là bạn"*.
  5. Chọn phương thức xác minh (thường là email liên kết/tài khoản khác đang lưu trên cùng máy, ví dụ `d***r@hotmail.com` hoặc `l***3@gmail.com`) > Bấm "Tiếp".
  6. Lấy mã OTP của email thứ 2 đó nhập vào app để hoàn tất xác minh danh tính.
  7. TikTok sẽ chuyển sang màn hình **"Đặt lại mật khẩu"** để nhập mật khẩu mới cố định.

- **Cạm bẫy & Lưu ý thực tế trên Farm:**
  - **Lệ thuộc vào trạng thái tài khoản thứ 2:** Nếu email thứ 2 được yêu cầu xác minh là tài khoản Gmail trên máy nhưng dịch vụ Google Play đang bị hết phiên (`Yêu cầu đăng nhập`), Gmail sẽ không tự sync mã OTP về notification/inbox.
  - **Khuyến nghị:** Đối với hệ thống farm tự động, ưu tiên đăng nhập trực tiếp bằng luồng Email OTP qua XOAUTH2 (không cần tạo pass tĩnh), vừa tránh kích hoạt checkpoint danh tính chéo giữa các nick, vừa tương thích 100% với runner tự động.
