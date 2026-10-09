# Triage & Giải pháp: Hỗ trợ Đọc OTP Mail khi Đổi Mật khẩu TikTok (13/09/2026)

## Bối cảnh Sự cố (Máy 46 / Row 362)
- **Chuông báo động Farm Alert:**
  ```text
  Phase 3 (Add 2FA TikTok) thất bại (exit_code=4): 46 | 362 | t************ | failed | PASSWORD_VERIFY_METHOD_NOT_FOUND
  ```
- **Hiện trường thực tế:**
  + Máy 46 (serial `ce0916092531413504`).
  + Tài khoản: `thy.linh.l199` (Row 362) và `trieutruc0505` (Row 363).
  + Kiểm tra ô E362, E363 Excel: Đã có Secret 2FA kích hoạt thành công.
  + Mật khẩu ban đầu là legacy farm (`Linhle1505@Ks`, `Trieutruc05051997@Ks`), thuộc diện cần rotate theo `password_needs_rotation()`.

## Nguyên nhân Gốc rễ (Root Cause)
1. Khi vào màn hình `Thay đổi mật khẩu`, TikTok bắt buộc phải qua cổng **"Xác minh danh tính" (Verify your identity)**.
2. Với các tài khoản reg qua mail chưa từng set pass trong phiên hoặc chưa verify mật khẩu gần đây, TikTok chỉ hiện DUY NHẤT 1 phương thức: gửi mã OTP 6 số về Gmail/Hotmail (biến thể OTP-Only, không hề có dòng lựa chọn nhập *"Mật khẩu"*).
3. Code cũ trong `ensure_account_password_saved()` chỉ tìm text/desc *"Mật khẩu"*. Khi không tìm thấy method row này, nó ném:
   ```python
   raise LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")
   ```
   làm sập toàn bộ runner Phase B (exit code 4), biến kết quả 2FA đã thành công thành thất bại.

## Chỉ đạo của Operator & Giải pháp Hoàn chỉnh (13/09/2026)
- **Chỉ đạo:** Không bỏ qua (không soft-return bỏ mặc pass cũ), mà phải **lấy OTP từ mailbox trên chính máy để đổi pass luôn** vì các mật khẩu cũ dạng `Ten+số+@` / `@Ks` là mật khẩu yếu, dễ đoán, cần rotate triệt để sang mật khẩu random mạnh.
- **Quy trình triển khai:**
  1. Trong `core/workbook.py`: Thêm `read_email_value(workbook_path, target)` để đọc cột F (`GMAIL`) của row tương ứng.
  2. Trong `core/live_phase_b_adapter.py`:
     - Nhận diện màn "Xác minh danh tính" biến thể OTP-only.
     - Bấm nút **"Tiếp"** để TikTok phát mã 6 số về hòm thư.
     - Phân loại email:
       * `@gmail.com`: Gọi `_try_get_otp_gmail_app(serial, email)` từ `social_reg_v1.py`, đọc mã xong `am force-stop com.google.android.gm` để trả TikTok về foreground.
       * `@hotmail.com` / `@outlook.com`: Gọi `read_tiktok_otp_from_outlook_app(...)` từ `Hotmail/flows/hotmail_login.py`, đọc mã xong `am force-stop com.microsoft.office.outlook`.
     - Nhập 6 số OTP vào TikTok bằng `input_otp_digits(self.adb, otp_code)`.
     - Bấm "Tiếp" để tiến vào form đặt mật khẩu mới `_complete_password_setup()`.
     - Lưu mật khẩu mới vào cột D (PASS) của file Excel qua callback `on_password_created`.
  3. **Fail-safe fallback:** Nếu không đọc được OTP hoặc email trống/lỗi, soft-return giữ nguyên pass hiện tại trong workbook thay vì crash batch, bảo toàn kết quả 2FA.
