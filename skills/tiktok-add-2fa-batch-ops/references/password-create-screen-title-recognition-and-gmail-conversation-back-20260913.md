# Báo Cáo Sự Cố & Kỹ Thuật: Nhận Diện Form "Tạo Mật Khẩu" & Auto-Back Gmail Conversation View (13/09/2026)

## 1. Bối cảnh & Hiện tượng
Khi chạy canary kiểm chứng nhánh đổi mật khẩu trên các tài khoản TikTok có mật khẩu cũ dạng legacy farm (`xxx@Ks`, `Ten+số+@`):
- Tài khoản đã có 2FA Authenticator nhưng cần rotate mật khẩu mạnh theo quy chuẩn farm.
- Khi điều hướng vào mục đổi mật khẩu, TikTok đưa ra thách thức "Xác minh danh tính" (Verify your identity) bằng OTP gửi về Gmail.
- Hai rào cản phát sinh trong quá trình tự động:
  1. Module `_try_get_otp_gmail_app` sau khi switch account Gmail bị kẹt timeout do ứng dụng Gmail đang mở sẵn một email chi tiết (`conversation view`), không nhận diện được inbox list markers.
  2. Sau khi nhập OTP mail thành công, TikTok không hiển thị nhãn "Thay đổi mật khẩu" mà hiển thị tiêu đề "Tạo mật khẩu" (`create password`), khiến bộ nhận diện màn hình bỏ qua và lùi màn hình dẫn đến soft-return mà chưa hoàn tất lưu mật khẩu mới vào workbook.

## 2. Phân tích nguyên nhân gốc rễ (Root Cause)
1. **Gmail Conversation View Trap:**
   - Trong `social_reg_v1.py`, hàm `_gmail_mailbox_state()` chỉ tìm các markers của danh sách hộp thư (`open_search`, `conversation_list`, `thread_list_view`, `Primary`, `Soạn thư`).
   - Khi Gmail đang mở chi tiết 1 email, các thuộc tính này không tồn tại mà chỉ có `subject_and_folder_view`, `sender_name`, `recipient_summary`. Do đó hàm đánh giá `reason=no_inbox_marker` và loop 3 lần rồi fail.
   - Kể cả khi nhận diện `reason=ok`, nếu không bấm `BACK` thoát khỏi email cũ, các thao tác vuốt refresh hoặc tìm tab Promotions ở các bước sau sẽ không hoạt động trên danh sách thư mới.
2. **Title Mismatch trên màn Đặt Pass TikTok:**
   - Trong `live_phase_b_adapter.py`, hàm `ensure_account_password_saved()` chỉ kiểm tra:
     `if "thay đổi mật khẩu" in values or "change password" in values:`
   - Với các tài khoản đăng ký qua Google/Hotmail chưa từng đặt mật khẩu trong phiên, màn hình tiếp theo có tiêu đề là **"Tạo mật khẩu"** (`create password`). Do thiếu từ khóa này, điều kiện bị trượt, script thực hiện `KEYCODE_BACK` lùi ra ngoài và thoát sớm.

## 3. Giải pháp & Triển khai chuẩn
### A. Vá Gmail OTP Reader (`social_reg_v1.py`):
1. Mở rộng `_gmail_mailbox_state()`:
   ```python
   or "sender_name" in rid
   or "recipient_summary" in rid
   or "subject_and_folder_view" in rid
   ```
2. Thêm cơ chế tự động thoát conversation view:
   Ngay sau khi xác nhận mailbox sau account switcher, nếu phát hiện đang ở conversation view (`conversation_header`, `subject_and_folder_view`, `sender_name`, `inside_conversation_unread`), gửi lệnh `keyevent 4` (BACK) và chờ 1.5s để Gmail quay về danh sách Inbox trước khi thực hiện pull-to-refresh.

### B. Mở rộng nhận diện tiêu đề đổi mật khẩu (`live_phase_b_adapter.py`):
Cập nhật điều kiện nhận diện:
```python
if (
    "thay đổi mật khẩu" in values
    or "change password" in values
    or "tạo mật khẩu" in values
    or "create password" in values
):
    self._complete_password_setup(current)
    if self.password_required():
        raise LiveAdapterError("PASSWORD_WORKBOOK_VERIFY_FAILED")
    return
```

### C. Tách riêng nhánh canary đổi pass bằng `--password-only`:
Bổ sung cờ `--password-only` vào `run_capture_phase_b.py` để bypass qua bước kiểm tra 2FA (`already-enabled`) và thực thi trực tiếp `adapter.ensure_account_password_saved()`, đảm bảo kiểm chứng độc lập 100% luồng đổi pass mà không làm xáo trộn trạng thái 2FA đã hoàn thành.

## 4. Kiểm chứng (Verification)
- Unit test suite: `pytest python_runner/tests/test_live_phase_b_adapter.py` (17/17 passed).
- Ad-hoc test: Kiểm chứng AST và regex logic với file XML dump thực tế `fail_gmail_mailbox_wrong_app_*.xml`.
- Canary live test: Chạy thực tế trên Máy 46 (Row 362 - `thy.linh.l199`) xác nhận đọc OTP mail thành công và điều hướng khớp vào form tạo mật khẩu mới.
