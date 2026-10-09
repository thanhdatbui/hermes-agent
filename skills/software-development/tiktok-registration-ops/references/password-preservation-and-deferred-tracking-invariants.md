# Invariant Bảo Toàn Mật Khẩu TikTok & Chống Ghi Đè Pass Ảo

## 1. Bản Chất Sự Cố (Root Cause Investigation)
- **Hiện tượng**: Tài khoản TikTok bị báo "Mật khẩu sai" khi chạy login/runner, mặc dù người dùng không đổi pass.
- **Nguyên nhân gốc rễ**:
  1. Khi một tài khoản đăng ký/đăng nhập lại qua luồng OTP hoặc magic link mà không xuất hiện màn hình nhập mật khẩu (`password = ""` hoặc `None`):
     - Trong code cũ (`social_reg_v1.py`), hàm `ensure_profile_completed_and_track` có fallback nguy hiểm: `make_tiktok_password(mail_pw)` tự sinh mật khẩu ngẫu nhiên mới rồi lưu vào kết quả run, sau đó ghi đè vào Excel.
     - Trong `deferred_tracking_writer.py`, hàm `apply_deferred_result` ghi `result.get("password") or None` đè thẳng lên ô mật khẩu hiện có trong workbook tracking, xóa trắng mật khẩu thật.
  2. Khi runner lấy mật khẩu ảo/rác từ Excel điền vào TikTok, server TikTok báo đỏ `Mật khẩu sai`.

## 2. Invariants Bắt Buộc Khi Sửa & Vận Hành (Prevention Rules)
1. **Bảo toàn existing_pass trong Deferred Tracking**:
   - Trong `scripts/deferred_tracking_writer.py`, khi chuẩn bị values ghi vào sheet:
     ```python
     resolved_pass = result.get("password") or existing_pass or None
     ```
   - TUYỆT ĐỐI CẤM ghi `None` hoặc chuỗi rỗng vào cột PASS nếu ô đó đã có `existing_pass`.

2. **Bảo toàn existing_pass trong Direct Upsert Tracking**:
   - Trong `social_reg_v1.py` (`upsert_tracking_account`):
     ```python
     ex_pass = ws.cell(target_row, 4).value
     if not tiktok_pw and ex_pass:
         tiktok_pw = str(ex_pass).strip()
     ```
   - Trong `ensure_profile_completed_and_track`: nếu `not tiktok_pw`, đọc lại từ `get_tracking_account_meta(email)` để bảo toàn.

3. **CẤM Tự Sinh Pass Ảo Khi Account Đã Tồn Tại**:
   - Khi `detect_after_continue == "registered"`:
     - Nếu tracking không có password, để `tiktok_pw = ""`.
     - TUYỆT ĐỐI CẤM gọi `make_tiktok_password()` khi tài khoản đã tồn tại.

4. **Khôi Phục Pass Thật Khi Bị Lệch**:
   - Kiểm tra artifact ban đầu trong `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/<first-run>/stt_N/tracking_result_sttN_*.json`.
   - Tìm giá trị `password` ở lần chạy thành công đầu tiên (run lúc tạo tài khoản) để khôi phục lại vào `taikhoan_dat_v2_updated .xlsx`.
