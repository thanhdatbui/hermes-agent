# PASSWORD_CHANGE_SCREEN_NOT_REACHED Fail-Safe Triage & Fix (Case 54)

## Ngữ cảnh & Triệu chứng
- Khi chạy Add 2FA trong chuỗi đêm (`run_night_chain_pipeline.py`) hoặc chạy lẻ (`run_capture_phase_b.py`), tài khoản máy (ví dụ Máy 43, row 338) đã hoàn tất bật 2FA Authenticator thành công (cột E đã ghi Secret Key 32 ký tự, DPAPI journal đạt state `EMAIL_DISABLED`).
- Tiếp theo, runner gọi bước bổ trợ `ensure_account_password_saved()` để rotate mật khẩu cũ (`Chaudang1112@`) nếu mật khẩu trong Excel là dạng legacy farm hoặc trống.
- Trên máy thật, TikTok đổi nhánh UI hoặc yêu cầu xác minh danh tính qua OTP email (không có ô nhập mật khẩu), hoặc 8 lần gửi phím Back (`KEYCODE_BACK`) không thể đưa view về form "Thay đổi mật khẩu".
- Code cũ ném ngoại lệ cứng `LiveAdapterError("PASSWORD_CHANGE_SCREEN_NOT_REACHED")`, làm tiến trình Phase B thoát exit code 4 và kích hoạt Farm Alert đỏ, phá hủy kết quả 2FA hợp lệ vừa đạt được.

## Nguyên tắc thiết kế & Bản vá chuẩn
1. **Bảo toàn kết quả 2FA:** Bước đổi mật khẩu chỉ là bước phụ đi kèm nhân tiện đang mở menu Cài đặt & Bảo mật. Tuyệt đối không được phép đánh sập flow khi 2FA Authenticator đã được kích hoạt thành công.
2. **Fail-safe `return` trong `live_phase_b_adapter.py`:**
   - Tại dòng 815 trong `ensure_account_password_saved()`: thay vì `raise LiveAdapterError("PASSWORD_CHANGE_SCREEN_NOT_REACHED")` khi hết 8 vòng lặp điều hướng, chuyển thành `return`.
   - Giữ nguyên mật khẩu hiện tại trong workbook (`taikhoan_dat_v2_updated .xlsx`), đảm bảo không làm corrupt hay lệch sheet.
3. **Focused Verification:** Chạy bộ test focused `pytest python_runner/tests/test_live_phase_b_adapter.py` (16 passed).
