# Case 55: Password Identity Challenge OTP-Only & Rotation Integration (13/09/2026)

## 1. Triệu chứng & Nguyên nhân
- **Triệu chứng:** Pipeline Chuỗi Đêm (Phase 3 Add 2FA TikTok) văng lỗi:
  `46 | 362 | t************ | failed | PASSWORD_VERIFY_METHOD_NOT_FOUND` (exit code 4).
- **Root Cause:**
  1. Sau khi hoàn tất nạp 2FA Authenticator thành công (đã ghi Secret Key vào cột 2FA của Excel), runner Phase B chạy bước phụ trợ `ensure_account_password_saved()` để đổi mật khẩu legacy farm (`*@Ks`, `Ten+số+@`).
  2. TikTok hiển thị màn hình "Xác minh danh tính" (Verify your identity) dạng **OTP-Only**: hoàn toàn không có lựa chọn "Mật khẩu" mà chỉ có dòng Email masked (`l***@gmail.com`).
  3. Runner cũ chỉ quét tìm method "Mật khẩu" ➔ Không tìm thấy ➔ Ném ngoại lệ `LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")` làm sập toàn bộ runner Phase 3.

## 2. Bản vá kiến trúc (commit 0aa666c)
- **Đọc email từ Workbook:** Bổ sung `read_email_value(workbook_path, target)` trong `core/workbook.py` (cột F `GMAIL`/`EMAIL`). Truyền `account_email` vào `LivePhaseBAdapter` qua `run_capture_phase_b.py`.
- **Luồng xử lý biến thể OTP-Only:**
  1. Khi `method_rows` không có "Mật khẩu", kiểm tra `account_email`. Nếu không có email: soft-return để fail-safe.
  2. Chọn dòng Email trên màn hình ➔ Bấm "Tiếp" để TikTok gửi OTP 6 số về mailbox.
  3. Gọi `email_otp_reader(serial, email)`:
     - Gmail (`@gmail.com`): Mở app Gmail trên máy bằng `_try_get_otp_gmail_app()`, đọc OTP, sau đó `am force-stop com.google.android.gm` để TikTok quay lại foreground.
     - Hotmail/Outlook (`@hotmail.com`, `@outlook.com`): Gọi `read_tiktok_otp_from_outlook_app()` từ `Hotmail/flows/hotmail_login.py`, sau đó `am force-stop com.microsoft.office.outlook`.
  4. Nhập 6 số OTP vào TikTok bằng `input_otp_digits(self.adb, otp)` ➔ Bấm "Tiếp" để tiến vào form đặt mật khẩu mới `_complete_password_setup()`.
  5. Đổi mật khẩu thành công và lưu vào cột D (PASS) của Excel.

## 3. Pitfall Canary Selection (User Correction)
- Khi user yêu cầu "triển khai canary trên máy hôm qua lỗi", phải chạy trên **đúng target/row đã bị fail ở bước đó** (ở đây là Row 362 - `thy.linh.l199` có pass legacy `Linhle1505@Ks`), **TUYỆT ĐỐI KHÔNG** tự ý nhảy sang target tiếp theo chưa bật 2FA nhưng có pass mạnh sẵn (như Row 364 `hectornwrigh45` có pass `t3dHpmg7I@d9`), vì target đó sẽ bỏ qua bước đổi pass và không kiểm chứng được bản vá flow lỗi.
