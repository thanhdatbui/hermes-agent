# PASSWORD_VERIFY_METHOD_NOT_FOUND Triage & Fail-Safe (Case 55 - 2026-09-13)

## Bối Cảnh
- **Pipeline:** Chuỗi Đêm (`run_night_chain_pipeline.py`) -> Phase 3 Add 2FA TikTok (`run_batch_live_2fa.py`).
- **Triệu chứng Alert:**
  `Phase 3 (Add 2FA TikTok) thất bại (exit_code=4): 46 | 362 | t************ | failed | PASSWORD_VERIFY_METHOD_NOT_FOUND`
- **Ảnh hưởng:** Sập runner Phase 3 (exit code 4), kích hoạt Farm Alert và ngắt chuỗi đêm, mặc dù 2FA Authenticator thực tế đã được kích hoạt thành công trên TikTok và ghi vào Journal/Workbook.

## Cơ Chế Gốc Rễ (Root Cause)
1. Trong luồng `run_capture_phase_b.py`, sau khi bật Authenticator thành công (state `AUTHENTICATOR_CONFIRMED` -> `WRITTEN` -> `EMAIL_DISABLED`), Phase B gọi hàm phụ trợ `ensure_account_password_saved()`.
2. Mục đích của bước phụ: nhân tiện đang trong Cài đặt bảo mật, rotate mật khẩu legacy farm (`xxx@Ks` hoặc `Ten+số+@`) cho nick nếu cần.
3. TikTok áp đặt màn hình cổng *"Xác minh danh tính"* ("Verify your identity") trước khi vào form đổi mật khẩu. Có 3 biến thể màn này:
   - Biến thể 1: Nhập mật khẩu hiện tại trực tiếp.
   - Biến thể 2: Danh sách lựa chọn phương thức xác minh có dòng "Mật khẩu".
   - Biến thể 3 (OTP-Only qua Email/SMS): Chỉ có duy nhất 1 phương thức gửi mã OTP tới Email/SMS (ví dụ `l***0@gmail.com`), hoàn toàn không có lựa chọn "Mật khẩu".
4. Code cũ trong `live_phase_b_adapter.py`:
   ```python
   method_rows = [
       element for element in iter_elements(parse_xml(current))
       if element.center is not None and _matches(element, "Mật khẩu", prefix=False)
   ]
   if not method_rows:
       raise LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")
   ```
   Do không tìm thấy dòng "Mật khẩu", code đã ném `LiveAdapterError("PASSWORD_VERIFY_METHOD_NOT_FOUND")` làm crash sập toàn bộ runner Phase B với exit code 4.

## Bản Vá Fail-Safe Chuẩn
Tương tự như bản vá `PASSWORD_CHANGE_SCREEN_NOT_REACHED` (Case 54): bước phụ trợ đổi mật khẩu tuyệt đối không được phép làm hỏng hoặc phủ nhận thành quả của luồng 2FA chính.

Sửa trong `live_phase_b_adapter.py`:
```python
if not method_rows:
    # Fail-safe: Màn "Xác minh danh tính" chỉ có OTP email/SMS, không có lựa chọn Mật khẩu.
    # Soft-return để bảo vệ trạng thái 2FA đã bật thành công và mật khẩu hiện tại trong workbook.
    return
```

## Kiểm Chứng (Verification Contract)
- **Unit Test:** `test_ensure_account_password_saved_soft_returns_when_verify_method_not_found` trong `test_live_phase_b_adapter.py`.
- Lệnh chạy kiểm chứng:
  ```bash
  /d/Taadaa/python-envs/automation/Scripts/pytest.exe D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/tests/test_live_phase_b_adapter.py
  ```
  Yêu cầu: 17/17 passed.
