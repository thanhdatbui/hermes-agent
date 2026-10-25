# TikTok Missing Account Recovery: Automation Core Popup Solver & Graph Token OTP (2026-10-25)

## 1. Bản chất sự cố & Bài học từ hiện trường M211
Khi hệ thống phát hiện máy thiếu nick (`ACCOUNT_MISSING`) và kích hoạt `login_recovery.py` -> `tiktok_login_v1.py <STT> --all`:
- **Bottom-sheet "Thêm số điện thoại của bạn...":**
  * TikTok xuất hiện popup yêu cầu thêm số điện thoại để bảo mật ngay tại form nhập Email/ID đăng nhập.
  * **Giải pháp chuẩn:** BẮT BUỘC gọi bộ solver chuẩn `automation_core.tiktok_popup` (`_detect_tiktok_popup`, `_find_button`, `TIKTOK_POPUP_RULES`).
  * Nút đóng: `content-desc="Đóng"`, bounds `[936,861][1056,993]`, center `(996, 927)`. Tuyệt đối không tự viết xpath/regex ad-hoc ngoài core.

## 2. Xử lý Lỗi "Mật khẩu sai" qua Microsoft Graph API Token (`--otp-only`)
- **Nguyên nhân gốc rễ:** Nhiều tài khoản TikTok tạo bằng Hotmail/Outlook trước đây qua flow email OTP không hề có mật khẩu trong server ByteDance (hoặc mật khẩu trong tracking bị lệch/tạo không thành công).
- **Phòng vệ chống khóa tài khoản:** Khi TikTok trả thông báo đỏ `⚠️ Mật khẩu sai`, script kích hoạt `[AUTH_BLOCKED]` để dừng ngay, CẤM thử lại password dồn dập.
- **Quy trình gỡ tự động qua Token:**
  1. Kiểm tra kho mail `gmail_clean_v2.xlsx`: nếu mailbox có `refresh_token` + `client_id` (cột 9 & 10) -> chạy `tiktok_login_v1.py <STT> --email <mail> --otp-only`.
  2. **Thay đổi UI TikTok:** Trên màn hình nhập mật khẩu, TikTok đã đổi nút "Quên mật khẩu?" thành `"Bạn cần trợ giúp đăng nhập?"`. Bấm vào dòng này để mở tùy chọn gửi mã xác thực về email.
  3. **Lấy mã PC-side:** Hệ thống gọi `read_tiktok_otp_from_graph_token` (trong `hotmail_provider.py`) để lấy mã OTP 6 số trực tiếp từ Microsoft Graph API trên PC chỉ trong 1-2 giây. **TUYỆT ĐỐI CẤM mở app Outlook trên thiết bị**.

## 3. Quản lý Tiến trình Nền trên Windows OpenSSH (CREATE_BREAKAWAY_FROM_JOB)
- Khi dispatch lệnh detached qua SSH (`admin_ssh.py`), OpenSSH Server trên Windows sẽ tự động terminate mọi process con ngay khi kết nối SSH ngắt.
- Để script tiếp tục chạy ngầm an toàn và không bị gián đoạn, bắt buộc truyền:
  `creationflags = 0x01000008` (`subprocess.CREATE_BREAKAWAY_FROM_JOB | subprocess.DETACHED_PROCESS`).
