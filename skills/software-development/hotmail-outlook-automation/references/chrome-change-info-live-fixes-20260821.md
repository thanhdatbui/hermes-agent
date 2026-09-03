# Chrome Change-Info Pipeline Pitfalls, Fixes & Verification (2026-08-21)

## 1. Kiến trúc Change-Info: Chrome vs Outlook App
- **Lý do bắt buộc chạy trên Chrome:** App Outlook chỉ là mail client (không có native form đổi pass/2FA/logout devices). Microsoft bắt buộc các thao tác quản trị bảo mật sâu phải qua web (`account.microsoft.com/security` hoặc `account.live.com/password/Change`).
- **Pipeline:** `flows/hotmail_change_info.py` điều khiển Chrome trên từng máy Android (qua IP proxy riêng của máy) để đăng nhập, đổi pass, đăng xuất mọi thiết bị và gắn mail khôi phục.

## 2. Các Pitfalls & Fixes đã kiểm chứng (Live Run Máy 30 & 54)

### A. Lỗi nuốt/gõ sai ký tự email trên Chrome (`type_text` in `flows/hotmail_login.py`)
- **Triệu chứng:** Khi dùng `adb input text`, bàn phím ảo Samsung/Chrome bị delay hoặc autocorrect làm thừa ký tự (ví dụ đuôi `.com` bị gõ thành `.come` -> Microsoft báo "Tài khoản Microsoft đó không tồn tại").
- **Fix:** Nâng cấp `type_text` ưu tiên 100% sử dụng `AdbKeyboard` broadcast chuỗi mã hóa base64 (`ADB_KEYBOARD_SET_TEXT`). Không gửi từng ký tự rời rạc.

### B. Màn hình xác minh danh tính ("Sắp hoàn thành" / "Xác minh email của bạn")
- **Layout mới của Microsoft tiếng Việt:**
  - Tiêu đề: *"Sắp hoàn thành"* / *"Xác minh email của bạn"*.
  - Tùy chọn gửi mã: *"Gửi mã đến th\*\*\*\*\*@gmail.com"* (thay vì *"Gửi email đến"*).
  - Nút bấm: *"Gửi mã"* (nhãn resource `proof-confirmation-email-input`).
- **Fix trong `flows/hotmail_security.py`:**
  - Bổ sung `_IDENTITY_VERIFICATION_MARKERS`: `"sắp hoàn thành"`, `"sap hoan thanh"`, `"almost there"`.
  - Bổ sung send labels: `"Gửi mã đến"`, `"Gui ma den"`, `"Send code to"`.
  - Thêm điều kiện tách biệt: `_has_identity_verification_screen` trả `False` khi `_has_email_proof_screen` đang mở (tránh nhầm giữa màn chọn phương thức và màn nhập email khôi phục).

### C. Pop-up "Sử dụng mật khẩu đã lưu?" che khuất nút "Gửi mã"
- **Triệu chứng:** Sau khi gõ email khôi phục và ẩn IME, Chrome bật pop-up quản lý mật khẩu từ dưới lên, che mất nút "Gửi mã" -> script báo `security_email_proof_screen_lost_before_submit` hoặc `send_code_not_verified`.
- **Fix:** Trong `_complete_email_proof`, sau khi type email và `ime hide`, lập tức kiểm tra và dismiss `_has_password_manager_prompt` / `_has_password_accessory_sheet` trước khi tap "Gửi mã".

### D. Bấm nút "Lưu" đổi mật khẩu trên trang Microsoft Online
- **Triệu chứng:** Form đổi mật khẩu Microsoft (`UpdatePasswordAction`) có nút "Lưu" nằm ở `[54,1770][354,1863]`. Gửi `tap_text("Save", "Luu")` có thể trượt do chữ "Lưu" có dấu hoặc WebView delay.
- **Fix:** Tìm trực tiếp `_resource_node(xml, "UpdatePasswordAction")` và click vào tâm node, fallback tap text và retry khi Chrome accessory sheet xuất hiện.

### E. Bấm nút "Có" (Duy trì đăng nhập / Stay signed in)
- **Triệu chứng:** Nút "Có" (`[72,1572][1008,1686]`) trên Chrome WebView đôi khi bị nuốt tap đầu tiên.
- **Fix:** `tap_keep_signed_in_yes` hỗ trợ cả chữ `'Có'` (precomposed) và `'Có'` (combining acute), retry 3 lần và fallback tap trực tiếp vào tọa độ tâm `(540, 1630)`.

### F. Xác thực avatar trong Account Manager Drawer (`_verify_target_identity_before_logout`)
- **Triệu chứng:** Nút avatar góc trên phải của trang Account đổi từ `O365_MainLink_Me` sang `mectrl_main_trigger` ("Trình quản lý tài khoản cho...").
- **Fix:** Kiểm tra cả `O365_MainLink_Me` và `mectrl_main_trigger`.

## 3. Khôi phục và Đọc OTP qua Gmail (`thanhdatbui1995@gmail.com`)
- Khi Microsoft yêu cầu OTP gửi về email khôi phục `thanhdatbui1995@gmail.com`, script sử dụng `flows.hotmail_recovery.poll_latest_otp` (kết nối IMAP Gmail qua `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD` đã export trong environment) để lấy mã 6 số tự động trong 20-40s.
