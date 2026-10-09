# Kiến trúc điều phối GPM Login & On-boarding ChatGPT-Web Pool

## 1. Bản chất phân vai giữa các Cronjob (Không chồng chéo)
- **`sync_gpm_lifecycle.py` (07:15 - 08:45):** CHUYÊN TRÁCH tạo mới Profile GPM cho các Gmail LIVE mới và xóa bỏ Profile của các Gmail DIE/BAN. Watchdog ca tối TUYỆT ĐỐI KHÔNG tự tiện gọi logic sinh profile.
- **`post_evening_gpm_login_watchdog.py` (20:15 - 23:45):** CHUYÊN TRÁCH On-boarding (Đăng nhập Google trên GPM + Cấp quyền OAuth Antigravity). Single source of truth là API `:20129/api/providers` (lọc bỏ các acc đã nạp thành công).
- **`cron_chatgpt_web_pool_watchdog.py` (05:00 AM):** CHUYÊN TRÁCH Self-healing (Hồi sinh) & On-boarding ChatGPT-Web. Kiểm tra các connection `chatgpt-web` và `antigravity` bị inactive để mở GPM refresh session.

---

## 2. Logic 3 Nhóm Ưu tiên trong GPM Login Ca tối
1. **ƯU TIÊN 1 (`has_google_session_ready_oauth`):**
   - Các Profile GPM đã có sẵn Google Session Cookie (`SID, SSID, HSID, SAPISID`) trong thư mục Chromium `Default/Network/Cookies`.
   - Đặc điểm: Google Account Chooser hiện sẵn, click là cấp mã OAuth ngay trong vài giây, 100% không bị Checkpoint đòi SĐT.
2. **ƯU TIÊN 2 (`chatgpt_ready_priority`):**
   - Các acc chưa đăng nhập GPM nhưng ban ngày đã được bồi Trust tự nhiên trên điện thoại S7 (có cờ `CHATGPT_READY` trên Excel). Đã có lịch sử nhận mail OTP thật trên thiết bị gốc nên Google Risk Engine hạ thấp fraud score.
3. **ƯU TIÊN 3 (`new_gpm_login` / `cooldown_24h_retry`):**
   - Các acc chưa nạp OmniRoute còn lại. Nếu từng fail trong ngày, bắt buộc tuân thủ Cooldown $\ge 24\text{h}$ trước khi retry.
   - Luôn khóa trần an toàn: `MAX_WORKERS = 2` và `MAX_LOGINS_PER_PROXY = 2`.

---

## 3. Quy tắc On-boarding ChatGPT-Web: CẤM Google SSO, BẮT BUỘC Direct Password
- **Bối cảnh:** Trên điện thoại Samsung S7, các tài khoản được liên kết ChatGPT qua luồng **Direct Email OTP + Password `Taadaa@2026#`** (tuyệt đối không chạy Google SSO để tránh rủi ro bị khóa nick diện rộng).
- **Hệ quả trên GPM PC:**
  - CẤM Playwright click nút "Continue with Google" (Google SSO). Bấm Google SSO sẽ gây lệch phương thức xác thực hoặc tạo tài khoản trùng lặp.
  - Luồng chuẩn: Truy cập `https://chatgpt.com/auth/login` $\rightarrow$ Điền Email $\rightarrow$ Điền Mật khẩu `Taadaa@2026#` $\rightarrow$ Đăng nhập thẳng Dashboard và trích xuất:
    1. Cookie `__Secure-next-auth.session-token` (nạp cho `chatgpt-web`).
    2. API `/api/auth/session` -> `accessToken` (nạp cho `codex`).
  - Gửi POST lên `http://127.0.0.1:20129/api/providers` để kích hoạt connection.
