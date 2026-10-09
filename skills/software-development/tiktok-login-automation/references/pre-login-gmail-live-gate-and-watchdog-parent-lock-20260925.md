# Pre-login Gmail Live Gate & Watchdog Parent-Lock Inheritance (2026-09-25)

## 1. Pre-login Gmail Live Gate (Bắt buộc kiểm tra Live trước khi Login)
- **Bối cảnh**: Khi nạp/khôi phục tài khoản TikTok bằng luồng Gmail OTP (`--otp-only` hoặc tài khoản chưa có password), nếu tài khoản Gmail đã DIE / bị Google khóa xác minh ("Cảnh báo" trong Gmail app), script mở app và cố lấy OTP sẽ bị kẹt 150s rồi fail vô ích, làm tốn tài nguyên và kẹt máy.
- **Quy tắc bất biến**:
  1. Trước khi mở app TikTok và bắt đầu form đăng nhập trong `tiktok_login_v1.py`, nếu tài khoản là Gmail (`@gmail.com` hoặc dùng `--otp-only`), BẮT BUỘC gọi hàm kiểm tra live trước (`check_gmail_is_live(email)` từ `D:/Taadaa/tools/check_gmail_live_fast.py`).
  2. Nếu xác nhận Gmail DIE (`is_live is False`): BẮT BUỘC Fail-fast ngay từ đầu (`[gmail-live-gate] BLOCKED`), ghi log rõ ràng, không mở app và không chiếm màn hình thiết bị.
  3. Chỉ khi Gmail LIVE (hoặc check fallback True): Tiếp tục quy trình đăng nhập TikTok bình thường.

## 2. Bẫy Device Lock khi Watchdog gọi Sub-process (`--allow-parent-lock`)
- **Triệu chứng**: Watchdog chạy nạp nick trả về `Login result exit=2` chỉ trong < 5–9 giây mà không thấy thao tác nào trên app.
- **Nguyên nhân**:
  - Script Watchdog cấp cao đã chiếm `device_lock` của máy (`acquire_device_lock(machine=N, serial=DEV, project="...")`).
  - Khi watchdog gọi sub-process `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py N ...`, sub-process cố acquire lock mới và gặp conflict.
  - Do watchdog **không truyền cờ `--allow-parent-lock`** (hoặc project name của watchdog không nằm trong whitelist `PARENT_LOCK_PROJECTS`), `tiktok_login_v1.py` bị chặn tại `DeviceLockNeedsUserDecision` và exit code 2.
- **Giải pháp**:
  - Mọi runner / watchdog khi gọi sub-process login BẮT BUỘC thêm cờ `--allow-parent-lock`.
  - Project name trong lock của parent BẮT BUỘC đăng ký trong `PARENT_LOCK_PROJECTS` (hoặc đặt prefix chuẩn như `tiktok-luot nuoi acc`, `tiktok-feed`, `tiktok-login-restore`).

## 3. Kỷ luật Báo cáo Hiện trường & Tránh Ngụy biện Môi trường
- **Cấm đổ lỗi sai**: Tuyệt đối CẤM Agent viện cớ "công cụ adb không có trong PATH" làm blocker khi hệ thống farm luôn có ADB tĩnh tại `C:\Program Files (x86)\xiaowei\tools\adb.exe` hoặc inspect machine script chuyên dụng.
- **Direct Log Inspection**: Đọc trực tiếp `social_reg_log.txt` hoặc stdout/stderr của sub-process để tìm chính xác exception/exit code trước khi đưa ra kết luận cho User.
