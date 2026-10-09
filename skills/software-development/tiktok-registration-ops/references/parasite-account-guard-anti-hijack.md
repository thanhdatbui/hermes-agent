# Parasite Account Guard & Anti-Hijack Policy (Tiktok_Reg)

## Bối cảnh & Nguy cơ
Trong quá trình vận hành batch đăng ký (`social_reg_v1.py`), khi thử nhập email vào form đăng ký của TikTok, nếu email đó đã có tài khoản trên hệ thống:
- TikTok sẽ hiển thị thông báo "Email đã được đăng ký" kèm màn nhập password hoặc chuyển ngay sang màn hình xác minh mã OTP (`registered_otp`).
- **Nguy cơ trước đây:** Luồng code cũ có logic tái sử dụng email này bằng cách `return em, pw, dob` để chuyển hướng sang luồng đăng nhập (`flow login/OTP`). Điều này dẫn đến nguy cơ nghiêm trọng: tài khoản của máy khác (hoặc tài khoản ký sinh không rõ nguồn gốc) bị đăng nhập trái phép đè lên máy hiện tại, phá vỡ mapping thiết bị và gây sai lệch kho tài khoản.

## Quy tắc thực thi bắt buộc (Anti-Hijack & Guard Binding)

1. **Tuyệt đối cấm Hijack từ luồng Reg sang Login:**
   - Khi phát hiện `result == "registered_otp"` hoặc `result == "registered"`:
     - Ghi log cảnh báo nghiêm ngặt: `✗ {em}: DA CO TikTok va dang o OTP/verify → ABORT email nay tren luong reg, CAM login len!`
     - Lưu UI XML để audit: `save_ui_xml(device_id, f"fail_{stt}_email_already_registered_otp_{idx}")`
     - Nhấn phím `BACK` (`keyevent 4`), chờ dismiss màn hình và `continue` thử email tiếp theo.
     - Tuyệt đối KHÔNG trả về `return em, pw, dob` để tiếp tục login.

2. **Xử lý unknown fallback:**
   - Trong nhánh fallback nhận diện màn hình OTP hoặc text password/đã đăng ký (`otp_fallback`, `reg_fallback`):
     - Không được giữ lại email để login.
     - Nhấn `BACK` (`keyevent 4`), chờ 2.0s và `continue` bỏ qua email.

3. **Gắn chặt Device Serial khi giữ slot Reg:**
   - Khi gọi `reserve_machine_reg_slot`:
     - Bắt buộc truyền `serial=device_id`: `res_token = reserve_machine_reg_slot(stt, serial=device_id)`.
     - Ngăn ngừa tình trạng STT bị nhầm lẫn giữa các thiết bị hoặc cướp slot trái phép.

4. **Khai thác ParasiteAccountGuard trong luồng Login:**
   - Mọi thao tác login (`tiktok_login_v1.py`) phải đi qua `ParasiteAccountGuard` để kiểm tra email/username đó có được phân bổ cho đúng serial/STT hiện tại hay không trước khi tiến hành điền credentials vào thiết bị.
