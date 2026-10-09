# Password Rotation via Email OTP Identity Verification Flow (Case 55 - 2026-09-13)

## 1. Bối cảnh & Hiện tượng
Khi chạy Add 2FA TikTok (Phase B) trong chuỗi đêm, sau khi bật thành công Trình xác thực (Authenticator) và ghi nhận Secret Key, script thực hiện bước phụ `ensure_account_password_saved()` để rotate các mật khẩu dạng legacy farm (`Ten@Ks`, `Ten+chữ số+@`, hoặc pass trống) sang mật khẩu ngẫu nhiên mạnh.

Tại màn hình Cài đặt (`Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Mật khẩu`), TikTok thường chặn bằng cổng "Xác minh danh tính" (Verify your identity).
- Nếu có phương thức "Mật khẩu": script nhập pass hiện tại để qua gate.
- **Biến thể OTP-Only (Không có phương thức Mật khẩu):** TikTok chỉ hiển thị duy nhất lựa chọn gửi mã OTP 6 số qua email liên kết (ví dụ `l***0@gmail.com`). Code cũ không tìm thấy dòng "Mật khẩu" nên ném ngoại lệ `LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")` làm sập toàn bộ phiên Phase B (exit code 4).

## 2. Chỉ đạo dứt khoát của Operator (13/09/2026)
- **Không được bỏ qua (soft-return) pass rotation một cách thụ động:** Pass cũ trên máy là dạng yếu/lặp lại (`@Ks`, `Tên+ngày sinh+@`), bắt buộc phải đổi sang pass mạnh để bảo vệ nick.
- **Phải lấy OTP từ hộp thư trên máy để đổi pass luôn:** Tận dụng app Gmail / Outlook đã đăng nhập sẵn trên thiết bị để lấy mã OTP 6 số và hoàn tất luồng đổi mật khẩu.

## 3. Quy trình thực thi chuẩn (4 bước)
1. **Kích hoạt gửi mã OTP:**
   - Trên màn hình "Xác minh danh tính", tap vào phương thức Email (hoặc tap nút "Tiếp") để TikTok phát mã 6 chữ số về hộp thư.
   - Chờ chuyển sang màn hình "Nhập mã gồm 6 chữ số".
2. **Đọc mã OTP từ ứng dụng Email trên máy:**
   - Đọc cột F (`GMAIL`) từ workbook `taikhoan_dat_v2_updated .xlsx` qua `read_email_value(workbook_path, target)`.
   - **Với Gmail (`@gmail.com`):** Gọi `_try_get_otp_gmail_app(serial, email, not_before=...)` từ `D:\Taadaa\Tiktok_Reg\social_reg_v1.py`. Mở app Gmail, lấy mã mới nhất, sau đó `am force-stop com.google.android.gm` để đưa TikTok trở lại foreground.
   - **Với Hotmail/Outlook (`@hotmail.com` / `@outlook.com`):** Gọi `read_tiktok_otp_from_outlook_app(...)` từ `D:\Taadaa\Hotmail\flows\hotmail_login.py`, sau đó `am force-stop com.microsoft.office.outlook`.
3. **Nhập mã OTP vào TikTok:**
   - Sử dụng `input_otp_digits(adb, otp)` (gửi từng keyevent số NUM_0 .. NUM_9) để nhập 6 chữ số vào WebView TikTok.
   - Tap "Tiếp" / "Tiếp tục" nếu cần.
4. **Đổi mật khẩu & Đồng bộ Workbook:**
   - TikTok nhảy vào màn hình "Thay đổi mật khẩu" / "Đặt mật khẩu".
   - Nhập mật khẩu ngẫu nhiên mới (`self.account_password`).
   - Xác nhận lưu và gọi callback `on_password_created(password)` để ghi pass mới vào cột D (PASS) của file Excel.
   - Fail-safe: Nếu mailbox không đọc được OTP hoặc email trống, ghi log cảnh báo và giữ nguyên mật khẩu cũ trong workbook mà không làm crash phiên 2FA đã thành công.
