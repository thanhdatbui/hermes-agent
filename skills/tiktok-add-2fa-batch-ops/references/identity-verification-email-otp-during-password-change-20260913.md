# Case 55: Identity Verification via Email OTP during Password Change (2026-09-13)

## 1. Triệu chứng & Bối cảnh
- **Pipeline:** Chuỗi Ban Đêm Reg & 2FA (`run_night_chain_pipeline.py` / `run_batch_live_2fa.py`).
- **Lỗi ban đầu:** `Phase 3 (Add 2FA TikTok) thất bại (exit_code=4): 46 | 362 | t************ | failed | PASSWORD_VERIFY_METHOD_NOT_FOUND`.
- **Màn hình:** TikTok hiện gate *"Xác minh danh tính"* khi vào đổi pass phụ (`ensure_account_password_saved()`), nhưng biến thể này **chỉ có phương thức gửi mã qua Email/SMS** (OTP-only, không có lựa chọn *"Mật khẩu"*).
- **Hệ quả của code cũ:** Không tìm thấy dòng Mật khẩu ➔ ném `LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")` ➔ thoát exit code 4 làm sập toàn bộ runner Phase 3 dù 2FA Authenticator của tài khoản đã được bật thành công và ghi nhận vào workbook.

## 2. Quy tắc nghiệp vụ đổi pass trong luồng 2FA (User Directive 13/09/2026)
1. **Lý do phải đổi pass:**
   - Mật khẩu hiện tại của các nick trên farm thuộc dạng **legacy farm lặp lại/yếu** (dạng `Ten@Ks` hoặc `Ten+chuso+@` như `Linhle1505@Ks`, `Anhhoang3009@`) hoặc đang trống.
   - Bắt buộc phải rotate sang mật khẩu ngẫu nhiên mạnh (12-16 ký tự, đa dạng ký tự). Pass mạnh đã có sẵn thì giữ nguyên.
2. **Xử lý khi gặp màn "Xác minh danh tính" (biến thể OTP qua Email):**
   - **CẤM** ném lỗi làm sập runner hoặc dừng flow nếu chưa cố gắng lấy mã.
   - **Quy trình chuẩn:**
     1. Nhận diện màn hình xác minh danh tính có row Email (vd `l***0@gmail.com`).
     2. Bấm nút **"Tiếp"** để TikTok gửi mã OTP 6 số về hộp thư.
     3. Đọc mã OTP từ app trên chính thiết bị đó:
        - Với Gmail: gọi `_try_get_otp_gmail_app(serial, email, not_before=...)` từ `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (mở Gmail app, switch account, lấy mã, force-stop Gmail để TikTok quay lại foreground).
        - Với Hotmail/Outlook: gọi `read_tiktok_otp_from_outlook_app(adb, serial, email, ...)` từ `D:\Taadaa\Hotmail\flows\hotmail_login.py`.
     4. Nhập 6 số OTP vào TikTok qua ADB keyevent hoặc AdbKeyboard broadcast.
     5. Bấm **"Tiếp"** tiến vào form *"Thay đổi mật khẩu"*.
     6. Nhập mật khẩu ngẫu nhiên mới và flush cập nhật vào cột D (PASS) của file Excel.
   - **Fail-safe fallback:** Nếu quá trình lấy OTP bị lỗi hoặc timeout, soft-return bỏ qua bước đổi pass phụ để bảo toàn 100% kết quả 2FA Authenticator đã bật thành công, không ném exception làm crash batch runner.
