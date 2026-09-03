# Quy tắc Lock & Deferred Tracking Write khi chạy Batch Reg TikTok

## 1. Cơ chế nhả Lock vs Giữ Lock
- **CHỈ nhả lock khi SUCCESS:** Khi máy hoàn thành reg thành công (`VERIFIED_SUCCESS`), runner/script sẽ release lock để máy rảnh cho các tác vụ tiếp theo.
- **Máy FAILED / DỪNG HIỆN TRƯỜNG:** BẮT BUỘC giữ nguyên trạng thái Lock (`status: blocked`, `user_authorized: True`, `DEVICE_LOCK_ENABLED=1`). Không được nhả lock để ngăn các tiến trình cron khác can thiệp, giữ nguyên hiện trường cho người dùng xử lý.

## 2. Áp dụng Deferred Tracking Write
- Runner `_run_all_targets.py` chạy với cờ `--defer-tracking-write` để tránh tranh chấp ghi đồng thời vào file Excel tracking.
- Sau khi batch con hoàn tất, bắt buộc chạy script tổng hợp:
  ```bash
  python scripts/apply_deferred_tracking_results.py D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<run_id>\batch_1\stt_*\tracking_result_*.json
  ```
- Kiểm tra lại các dòng vừa được ghi trong `taikhoan_dat_v2_updated .xlsx` để đảm bảo không bị lỗi format/string type hoặc missing row/tik.

## 3. Nhánh màn hình Password trong TikTok Reg Flow
- **Nhánh có Password:** TikTok hiển thị ô nhập password -> script nhập mật khẩu và lưu vào kết quả.
- **Nhánh OTP / Email-only:** TikTok không hiển thị ô password mà vào thẳng màn profile/home -> script ghi nhận pass ngẫu nhiên đã cấp phát và ghi vào tracking workbook (cột PASS) để đồng bộ quản lý tài khoản.
