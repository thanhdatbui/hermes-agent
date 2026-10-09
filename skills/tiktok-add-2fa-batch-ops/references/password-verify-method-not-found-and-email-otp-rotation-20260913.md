# Pitfall & Quy trình xử lý lỗi PASSWORD_VERIFY_METHOD_NOT_FOUND và Luồng Đổi Pass OTP Mail (13/09/2026)

## 1. Bản chất lỗi & Bối cảnh phát sinh
- **Trigger**: Sau khi bật 2FA Authenticator thành công trong runner Phase B (`run_capture_phase_b.py`), hàm `ensure_account_password_saved()` được gọi để rotate mật khẩu cũ thuộc dạng legacy farm (`Ten@Ks`, `Ten+chuso+@` như `Anhhoang3009@`, hoặc pass trống) sang mật khẩu random mạnh.
- **Hiện tượng**: TikTok chặn màn hình **"Xác minh danh tính" (Verify your identity)** trước khi vào form đổi pass. Với các nick reg Gmail chưa từng lưu credential trong phiên, TikTok hiện **biến thể OTP-only** (chỉ có duy nhất row gửi mã về Email masked `l***0@gmail.com`, không có nút/lựa chọn `Mật khẩu`).
- **Lỗi code cũ**: Code chỉ tìm kiếm text `Mật khẩu` trên màn hình. Khi không thấy, nó ném `LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")` dẫn tới exit code 4 làm sập toàn bộ runner Phase 3 ca đêm (alert farm).

## 2. Giải pháp 2 tầng đã triển khai

### Tầng 1: Fail-safe bảo vệ trạng thái 2FA
- Khi gặp màn hình Xác minh danh tính mà không thể xử lý được hoặc không đọc được OTP mail, adapter thực hiện **soft-return** thay vì ném Exception.
- Giữ nguyên mật khẩu hiện tại trong Excel, bảo toàn 100% kết quả Secret 2FA đã được lưu an toàn trước đó, không làm crash pipeline chuỗi đêm.

### Tầng 2: Luồng đọc OTP Mail tự động để đổi pass mới
1. **Trích xuất Email mục tiêu**:
   - `core/workbook.py` bổ sung `read_email_value(workbook_path, target)` đọc cột `GMAIL` (hoặc `EMAIL`, `MAIL`, `HOTMAIL`).
   - `run_capture_phase_b.py` truyền `account_email` vào `LivePhaseBAdapter`.
2. **Kích hoạt gửi mã**:
   - Tap chọn row Email (nếu chưa chọn) và tap nút `Tiếp` (`prefix=True`) để TikTok gửi OTP 6 số.
3. **Đọc OTP trên thiết bị**:
   - Phân loại theo domain:
     + Với Gmail (`@gmail.com`): Gọi `_try_get_otp_gmail_app(serial, email)` từ `D:\Taadaa\Tiktok_Reg\social_reg_v1.py`.
     + Với Hotmail/Outlook (`@hotmail.com`, `@outlook.com`): Gọi `read_tiktok_otp_from_outlook_app(...)` từ `D:\Taadaa\Hotmail\flows\hotmail_login.py`.
   - Sau khi đọc xong, bắt buộc gọi `am force-stop` đối với package app mail tương ứng để đưa app TikTok quay lại foreground.
4. **Nhập OTP & Hoàn tất**:
   - Gõ 6 số OTP qua `input_otp_digits(self.adb, otp_code)`.
   - Bấm `Tiếp` để tiến vào màn "Thay đổi mật khẩu".
   - Gọi `_complete_password_setup()` nhập mật khẩu mới và ghi đè vào cột D của workbook.

## 3. Pitfall trong `_gmail_mailbox_state` (Gmail Conversation View)
- **Triệu chứng**: `_try_get_otp_gmail_app` switch account thành công nhưng báo `reason=no_inbox_marker` và timeout "Van khong ve duoc Gmail mailbox".
- **Root cause**: Khi switch account, Gmail có thể mở thẳng vào một email đã đọc trước đó (`conversation view`). Bộ lọc marker cũ trong `social_reg_v1.py` chỉ quét các marker ngoài danh sách hộp thư (`open_search`, `thread_list_view`, `Primary`, `Soạn thư`). Khi ở trong màn đọc thư chi tiết, các ID này không tồn tại.
- **Khắc phục**: Mở rộng danh sách marker trong `_gmail_mailbox_state` để nhận diện cả conversation view qua các resource-id:
  + `"sender_name" in rid`
  + `"recipient_summary" in rid`
  + `"subject_and_folder_view" in rid`
