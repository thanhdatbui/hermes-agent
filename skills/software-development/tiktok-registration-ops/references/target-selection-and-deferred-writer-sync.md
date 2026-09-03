# Target Selection Deduplication & Deferred Writer Data Safety

## 1. Target Selection Deduplication
- **Hiện tượng:** Trong file nguồn (`gmail_clean_v2.xlsx`), một số email có thể vô tình được gán cho nhiều STT máy khác nhau.
- **Nguyên nhân lỗi:** Khi hàm `select_pending_targets` trong `scripts/tiktok_target_eligibility.py` duyệt qua danh sách các máy, nếu không ghi nhận `used.add(email)` ngay khi chọn một email cho máy hiện tại, các máy ở batch tiếp theo sẽ tiếp tục nhặt lại chính email đó.
- **Hậu quả:** Nhiều máy chạy batch với cùng 1 email. Khi máy đầu tiên đăng ký thành công tài khoản TikTok, các máy sau mở ứng dụng với cùng email đó sẽ đăng nhập lại đúng tài khoản vừa tạo (trùng TikTok ID).

## 2. Cơ chế bảo vệ dữ liệu chống gán trùng (`deferred_tracking_writer.py`)
- **Quy tắc an toàn:** Khi chạy merge kết quả deferred từ các batch TikTok reg vào `taikhoan_dat_v2_updated .xlsx`, writer luôn kiểm tra tính duy nhất của email trên toàn bộ sheet (`matching_email_rows`).
- **Xử lý xung đột:**
  - Máy đầu tiên reg thành công sẽ được ghi đúng vào hàng (row) dự kiến.
  - Các máy chạy sau có cùng email sẽ bị chặn bởi gate an toàn: `BLOCKED_DATA_CONFLICT: EMAIL_FOUND_OUTSIDE_EXPECTED_ROW`.
  - Giúp ngăn chặn việc ghi đè hoặc gán 1 tài khoản TikTok cho nhiều máy khác nhau trong sheet quản lý và `taikhoan_run_safe.xlsx`.
