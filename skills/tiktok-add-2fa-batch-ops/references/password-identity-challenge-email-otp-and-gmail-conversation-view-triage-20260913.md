# Case 55: Password Identity Challenge OTP-Only & Gmail Conversation View Handling (2026-09-13)

## 1. Triệu chứng & Bối cảnh
- **Bối cảnh:** Chạy chuỗi đêm Phase 3 (`Add 2FA TikTok` / `run_batch_live_2fa.py`) sau khi bật 2FA thành công, runner bước vào khâu phụ `ensure_account_password_saved()` để rotate các mật khẩu dạng legacy farm (`*@Ks`, `Ten+chuso+@`).
- **Triệu chứng lỗi:** Runner Phase B ném ngoại lệ `LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")` và crash exit code 4 trên Máy 46 (Row 362 - acc `thy.linh.l199`).

## 2. Root Cause kép
1. **TikTok Identity Challenge dạng OTP-Only:**
   - Trên các tài khoản reg bằng Email mà chưa từng thiết lập credential đầy đủ, TikTok không hiển thị mục "Mật khẩu" trên màn hình "Xác minh danh tính" mà chỉ hiển thị duy nhất 1 phương thức nhận mã OTP qua Email (`l***0@gmail.com`).
   - `live_phase_b_adapter.py` trước đây chỉ quét method row `_matches(element, "Mật khẩu", prefix=False)` nên khi không thấy thì raise error làm crash toàn bộ phiên add 2FA đã thành công.
2. **Gmail Conversation View Trap (`no_inbox_marker`):**
   - Khi `_try_get_otp_gmail_app` mở Gmail và switch sang account target, nếu account đó đang mở sẵn ở màn hình đọc chi tiết một email (`conversation view` có `subject_and_folder_view`), hàm `_gmail_mailbox_state()` không nhận diện được inbox markers (`open_search`, `thread_list_view`...) ➔ Trả về `reason="no_inbox_marker"`, loop retry 3 lần và báo `Van khong ve duoc Gmail mailbox`.

## 3. Bản vá & Kiến trúc xử lý chuẩn

### A. Tầng `live_phase_b_adapter.py` & `run_capture_phase_b.py`:
1. **Nạp Email Target từ Workbook:**
   - Bổ sung `read_email_value(workbook_path, target)` trong `core/workbook.py` đọc cột `GMAIL` / `EMAIL`.
   - Truyền `account_email` vào `LivePhaseBAdapter`.
2. **Luồng xử lý biến thể OTP-Only:**
   - Khi không có `method_rows` mật khẩu nhưng có `account_email`:
     + Tap dòng email và bấm "Tiếp" để TikTok gửi OTP.
     + Gọi `self.email_otp_reader(serial, email)` đọc mã từ ứng dụng mailbox trên máy (Gmail qua `social_reg_v1._try_get_otp_gmail_app`, Hotmail/Outlook qua `hotmail_login.read_tiktok_otp_from_outlook_app`).
     + Nhập OTP 6 số bằng `input_otp_digits(self.adb, otp_code)`.
     + Force-stop app mail và tiến vào form đổi mật khẩu mới.
   - Nếu không đọc được OTP hoặc email trống: soft-return (fail-safe) để bảo toàn 100% kết quả 2FA Authenticator đã bật thành công trong Excel.

### B. Tầng `social_reg_v1.py` (`_try_get_otp_gmail_app`):
1. **Mở rộng Inbox Marker:**
   - Bổ sung các resource ID của conversation view vào `_gmail_mailbox_state()`:
     ```python
     or "sender_name" in rid
     or "recipient_summary" in rid
     or "subject_and_folder_view" in rid
     ```
2. **Tự động BACK về danh sách Inbox:**
   - Ngay sau khi switch account và verify mailbox, nếu phát hiện đang ở conversation view (`conversation_header`, `subject_and_folder_view`, `sender_name`, `inside_conversation_unread`):
     ```python
     shell(device_id, "input", "keyevent", "4")  # BACK
     time.sleep(1.5)
     xml_mailbox = _ensure_gmail_mailbox("after back from conversation", save_proof=True)
     ```
   - Thao tác này đưa Gmail về danh sách hộp thư chính để thực hiện pull-to-refresh và tìm thư chứa mã OTP TikTok mới nhất.

## 4. Kỷ luật vận hành Canary khi User yêu cầu
- Khi user yêu cầu: *"triển khai canary trên máy hôm qua lỗi"*, Coordinator BẮT BUỘC kiểm tra kỹ acc nào là acc lỗi ở bước đổi pass (`password_needs_rotation == True`), CẤM nhầm sang acc khác cùng máy mà pass đã random mạnh (`needs_rotation == False` ➔ runner bỏ qua bước đổi pass).
