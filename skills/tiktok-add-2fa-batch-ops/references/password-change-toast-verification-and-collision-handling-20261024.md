# Pitfall & Fix: Password Submit Toast Verification & Collision Detection

## 1. Ngữ cảnh & Triệu chứng
Trong luồng `ensure_account_password_saved` (`live_phase_b_adapter.py`), khi tài khoản TikTok đã từng có mật khẩu cũ hoặc chuyển sang nhánh màn hình **"Thay đổi mật khẩu"**:
- Runner sinh mật khẩu ngẫu nhiên, gõ vào trường `EditText` và bấm nút **"Tiếp tục"**.
- Nếu mật khẩu vừa sinh vô tình trùng với mật khẩu cũ của tài khoản, TikTok sẽ chặn lại và bắn ra thông báo toast màu đỏ:
  `"Mật khẩu mới không thể giống mật khẩu cũ"` (hoặc `"New password cannot be the same as old password"`).
- Nút "Tiếp tục" vẫn còn đó, bàn phím ảo vẫn mở, mật khẩu **chưa hề được lưu trên hệ thống TikTok**.

## 2. Lỗ hổng kiểm chứng cũ (False Positive)
- Hàm `_complete_password_setup` trước đây chỉ dùng `_wait_for` với điều kiện:
  ```python
  lambda xml: (
      "tạo mật khẩu" not in xml.casefold()
      and "create password" not in xml.casefold()
      and "xác nhận mật khẩu" not in xml.casefold()
      and "confirm password" not in xml.casefold()
  )
  ```
- Khi màn hình đích là **"Thay đổi mật khẩu"**, điều kiện trên thỏa mãn ngay lập tức từ vòng lặp đầu tiên, dẫn đến việc adapter gọi `self.on_password_created(...)` và ghi mật khẩu rác/chưa đổi vào Excel rồi báo `exit 0` ảo!

## 3. Quy tắc kiểm chứng bất biến (Hard Invariant)
1. **Bắt buộc kiểm chứng Toast thành công:**
   - Sau khi bấm "Tiếp tục", TikTok hiển thị toast thành công:
     `"Mật khẩu đã được thay đổi"` (hoặc `"Password has been changed"`).
   - Màn hình phải tự động điều hướng thoát khỏi form đổi mật khẩu và quay về trang `Tài khoản` (`com.ss.android.ugc.trill:id/yvg` với tiêu đề "Tài khoản").
2. **Bắt buộc phát hiện Toast va chạm mật khẩu cũ (Collision Handling):**
   - Nếu xuất hiện chuỗi `"không thể giống mật khẩu cũ"` hoặc `"cannot be the same"`:
     + BẮT BUỘC coi là submit thất bại.
     + Nhấn nút "Xóa văn bản" (`com.ss.android.ugc.trill:id/dr4` hoặc tap vị trí nút clear `x`).
     + Tạo mật khẩu mới với biến thể salt khác biệt (đảm bảo đủ 8-20 ký tự, chữ hoa, chữ thường, số, ký tự đặc biệt `@#!?`).
     + Nhập lại và submit lần 2.
3. **Khai báo Writer ID khi gọi Canary độc lập:**
   - Khi chạy canary qua `run_capture_phase_b.py` đơn lẻ ngoài pool `run_batch_live_2fa.py`, bắt buộc phải set biến môi trường:
     ```python
     env["TIKTOK_ADD_EXPECTED_WRITER_ID"] = "tiktok_tracking_writer"
     env["TIKTOK_ADD_WRITER_ID"] = "tiktok_tracking_writer"
     ```
   - Nếu thiếu 2 biến này, `automation_core.workbook.assert_writer_identity` sẽ ném `WorkbookError("BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking")` làm crash toàn bộ tiến trình ghi kết quả sau khi đã 2FA thành công.
