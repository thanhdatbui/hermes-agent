# Fast Login Junk Purge, Child Process Email Binding & ATX Recovery (2026-09-01)

## 1. Fast Login ("Tiếp tục với tên @...") & Xóa tài khoản rác
- **Hiện tượng**: Khi vào bước `choose_email_login`, TikTok mở màn hình One-tap login / Fast login hiển thị: `"Tiếp tục với tên @username"`, nút `"Sử dụng tài khoản khác"`, nút menu `"Khác"` (rid `z7o` / bounds `[936,84][1056,216]`).
- **Lỗi**: Nếu đặt `handle_fast_login_screen` sau `wait_for_text(...)`, hàm `wait_for_text` sẽ timeout 20s vì không tìm thấy text `"Đăng nhập"` / `"Email"`, dẫn đến văng lỗi `fail_06_login_methods` trước khi kịp xử lý.
- **Quy tắc chuẩn**:
  - `handle_fast_login_screen(device_id)` **bắt buộc chạy ngay đầu `choose_email_login` (trước `wait_for_text`)**.
  - Đọc handle `@username` trên màn hình và đối chiếu với toàn bộ kho Excel (`Tik1-4`, `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `gmail_clean_v2.xlsx`).
  - Nếu **không có trong kho**: Tap menu `"Khác"` (center `(996, 150)`) -> tap `"Xóa tài khoản"` -> xác nhận `"Xóa"` để dọn sạch session rác khỏi máy -> tap `"Sử dụng tài khoản khác"` để trở về form đăng ký.
  - Nếu **có trong kho**: Bỏ qua xóa, chỉ tap `"Sử dụng tài khoản khác"`.

## 2. Truyền tường minh `--email` vào tiến trình con (`_run_all_targets.py`)
- Khi detector chỉ định email (Hotmail hoặc Gmail target) cho từng máy, `_run_all_targets.py` BẮT BUỘC truyền tham số `--email <email>` và set `SOCIAL_PREFERRED_EMAIL` khi khởi chạy tiến trình con `social_reg_v1.py`.
- Nếu thiếu `--email`, tiến trình con tự ý scan lại toàn bộ `gmail_clean_v2.xlsx` từ đầu và bốc trúng các Gmail cũ (không còn trên máy) rồi mở app Gmail tìm OTP, gây lệch toàn bộ luồng.

## 3. Popup "Tài khoản của bạn đã bị đăng xuất"
- Khi khởi động hoặc điều hướng vào login, nếu gặp dialog hệ thống `"Trạng thái tài khoản: Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại."`, phải tap nút **OK** (`android:id/button1`) hoặc gửi phím BACK để đóng dialog trước khi tiếp tục.

## 4. Đồng bộ cơ chế phục hồi ATX Session trong `social_reg_v1.py`
- Đồng bộ chuẩn với `automation-core` và `tiktok-luot nuoi acc`:
  - Thử capture ATX session 3 lần (`restart_attempts=0`).
  - Nếu thất bại -> gọi `reset_atx_agent(timeout=15)` (kill tiến trình treo + start daemon + monkey kích hoạt stub + poll `ps -A`).
  - Sau reset, retry tiếp 2 lần (`restart_attempts=1`) trong ngân sách `local_deadline` 60s.
  - Fail-closed tuyệt đối, không fallback sang shell `uiautomator dump` để tránh đọc XML stale hoặc OOM-kill (137).
