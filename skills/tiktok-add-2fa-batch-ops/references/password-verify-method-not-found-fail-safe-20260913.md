# Case 55: Password Verify Method Not Found Fail-Safe (2026-09-13)

## 1. Triệu chứng & Bối cảnh
- **Alert Farm:** `Phase 3 (Add 2FA TikTok) thất bại (exit_code=4): 46 | 362 | t************ | failed | PASSWORD_VERIFY_METHOD_NOT_FOUND`
- **Bối cảnh:** Trong quy trình bật 2FA (`run_batch_live_2fa.py` / `run_capture_phase_b.py`), sau khi đã bật thành công Authenticator, ghi Secret Key vào cột E workbook và tắt Email 2FA (state `EMAIL_DISABLED` trong Journal DPAPI), runner gọi bước phụ trợ `ensure_account_password_saved()` để rotate mật khẩu legacy farm (`xxx@Ks` hoặc `Ten+số+@`).
- **Hiện tượng:** TikTok chặn lại ở màn hình "Xác minh danh tính" (*Verify your identity* / *Verify it's you*). Ở một số tài khoản reg bằng Gmail mà chưa từng đặt mật khẩu trong phiên, màn hình này chỉ hiển thị **DUY NHẤT 1 phương thức gửi mã OTP qua Gmail**, không có dòng "Mật khẩu" (*Password*).

## 2. Root Cause
- Code cũ trong `python_runner/core/live_phase_b_adapter.py`:
  ```python
  method_rows = [
      element for element in iter_elements(parse_xml(current))
      if element.center is not None and _matches(element, "Mật khẩu", prefix=False)
  ]
  if not method_rows:
      raise LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")
  ```
- Khi không thấy dòng "Mật khẩu", adapter lập tức ném `LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")`.
- Ngoại lệ này không được bắt fail-safe ở tầng runner con, dẫn đến tiến trình Phase B crash với `exit_code=4`. Toàn bộ kết quả 2FA Authenticator đã bật thành công trước đó bị đánh dấu thất bại trong batch report của Chuỗi Đêm.

## 3. Khắc phục chuẩn (Fail-safe Soft Return)
- Chuyển `raise LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")` thành `return` sớm:
  ```python
  if not method_rows:
      # Fail-safe: Màn "Xác minh danh tính" chỉ có OTP email/SMS, không có lựa chọn Mật khẩu.
      # Soft-return để bảo vệ trạng thái 2FA đã bật thành công và mật khẩu hiện tại trong workbook.
      return
  ```
- **Nguyên tắc thiết kế:** Bước rotate mật khẩu chỉ là bước phụ trợ gia tăng độ an toàn. Nếu gặp màn hình yêu cầu OTP email/SMS mà chưa có luồng tự động xử lý, script phải soft-return để bảo toàn 100% Secret Key 2FA đã ghi vào Workbook và không làm sập pipeline Chuỗi Đêm.
- **Unit Test:** Thêm test case `test_ensure_account_password_saved_soft_returns_when_verify_method_not_found` trong `python_runner/tests/test_live_phase_b_adapter.py`.
