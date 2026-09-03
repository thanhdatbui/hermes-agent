# Duplicate ID Collision Prevention & Stale Profile Capture (2026-08-27)

## Bối cảnh sự cố
- Khi chạy đăng ký tài khoản TikTok mới trên các máy đã có sẵn tài khoản đăng nhập từ trước, nếu bước mở Account Switcher để tạo tài khoản mới bị trượt hoặc văng về Home feed:
  1. `wait_login_success()` nhận diện các từ khóa generic ("Trang chủ", "Hồ sơ", "Bạn bè", "Đề xuất") của nick cũ đang mở trên máy -> kết luận nhầm là đăng ký thành công (`return True`).
  2. `ensure_profile_completed_and_track()` sau đó vào Profile đọc `@handle` hiện tại trên màn hình (ID của nick cũ) và lưu đè ID đó vào hàng của email mới trong `taikhoan_dat_v2_updated .xlsx`.
  3. Hệ quả: Tạo ra nhiều hàng trùng ID TikTok trên cùng một máy (17 hàng trùng được phát hiện và xử lý).

## Cơ chế phòng ngừa & Chốt chặn an toàn (Đã vá trong `social_reg_v1.py`)
1. **Chuẩn hóa ID & Email (`_normalize_id`, `_normalize_email`):**
   - Loại bỏ ký tự `@` ở đầu, strip whitespace, chuyển lowercase, chuẩn hóa Unicode NFC.
2. **Tầng đọc Profile (`ensure_profile_completed_and_track`):**
   - Trước khi ghi nhận, đối chiếu `@handle` vừa đọc với toàn bộ ID đã có trong file tracking master.
   - Nếu `@handle` trùng với một email khác đã tồn tại trong file -> Lập tức fail-closed với lỗi `BLOCKED_DUPLICATE_HANDLE_DETECTED`, chụp ảnh màn hình và dừng, không ghi nhận đè.
3. **Tầng ghi Workbook dưới Exclusive Lock (`upsert_tracking_account`):**
   - Quét toàn bộ sheet master ngay trước khi ghi (bên trong `_acquire_tracking_write_phase` lock), từ chối ghi (`DUPLICATE_TIKTOK_ID_REJECTED`) nếu ID thuộc về email khác.
4. **Quy tắc dọn dẹp hàng trùng (User Directive):**
   - Khi xóa các hàng trùng do lỗi reg, **xóa sạch toàn bộ thông tin tài khoản ở các cột 3..9 (ID, PASS, 2FA, GMAIL, PASS MAIL, DOB, CREATED)**.
   - Giữ nguyên Cột 1 (`Máy`), Cột 2 (`Folder Video`), Cột 10 (`device ID`) để bảo toàn cấu trúc 8 slot vật lý/máy.
   - Đồng bộ ngay sang `taikhoan_run_safe.xlsx`.
