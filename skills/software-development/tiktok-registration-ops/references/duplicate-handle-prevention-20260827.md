# Duplicate Handle & False Positive Registration Prevention (2026-08-27)

## 1. Triệu chứng & Nguyên nhân
- **Hiện tượng:** Nhiều email khác nhau trên cùng một máy bị ghi nhận cùng một ID TikTok trong `taikhoan_dat_v2_updated .xlsx`.
- **Nguyên nhân gốc:**
  1. Khi chạy flow đăng ký nick mới trên máy đã có nick đăng nhập từ trước: Nếu bước mở Account Switcher để vào luồng đăng ký thất bại hoặc TikTok văng về Home Feed / Profile root của nick cũ, hàm `wait_login_success` thấy các marker `"Trang chủ"`, `"Hồ sơ"` nên tưởng lầm là đăng ký thành công (`return True`).
  2. Hàm `ensure_profile_completed_and_track` vào Profile đọc `@handle` hiện tại trên màn hình (chính là ID của nick cũ đang mở) và ghi nhận ID đó vào dòng của email mới.

## 2. Bản vá & Cơ chế bảo vệ
1. **Chuẩn hóa ID & Email:**
   - `_normalize_id(value)`: loại bỏ `@` ở đầu, strip khoảng trắng, lowercase, Unicode NFC.
   - `_normalize_email(value)`: strip khoảng trắng, lowercase.
2. **Kiểm tra tại Profile Verification (`ensure_profile_completed_and_track`):**
   - Đọc `@handle` từ XML và đối chiếu với toàn bộ ID đang có trong `taikhoan_dat_v2`.
   - Nếu `@handle` trùng với một dòng có email khác, lập tức ném lỗi `BLOCKED_DUPLICATE_HANDLE_DETECTED`, chụp ảnh màn hình hiện trường và dừng phiên fail-closed.
3. **Kiểm tra tuần tự hóa dưới khóa độc quyền (`upsert_tracking_account`):**
   - Trước khi lưu vào workbook dưới lock `_acquire_tracking_write_phase`, quét lại toàn bộ sheet.
   - Nếu ID đã thuộc về email khác, ném `DUPLICATE_TIKTOK_ID_REJECTED`.

## 3. Quy trình dọn dẹp hàng trùng
- Xác định nick chuẩn (có Pass TikTok, 2FA, đúng Mail).
- Với các hàng trùng thừa: Xóa sạch thông tin tài khoản (Cột 3..9: ID, PASS, 2FA, GMAIL, PASS MAIL, DOB, CREATED). Giữ nguyên Cột 1 (Máy), Cột 2 (Folder Video), Cột 10 (Device ID) để bảo toàn cấu trúc 8 slot/máy.
- Đồng bộ lại sang `taikhoan_run_safe.xlsx`.
