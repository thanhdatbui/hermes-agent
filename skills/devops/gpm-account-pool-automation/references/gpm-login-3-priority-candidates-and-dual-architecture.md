# 3-Priority GPM Login Candidates & Dual Architecture (Antigravity vs ChatGPT-Web)

## 1. Phân vai kiến trúc giữa On-boarding (Ca Tối) vs Self-Healing (05:00 AM)

### A. Phân định ranh giới Lifecycle & Login
- **Tạo / Xóa Profile GPM (`sync_gpm_lifecycle.py`):** Đã có cron riêng chạy `07:15 - 08:45` quét Excel tự động tạo profile cho Gmail LIVE mới và xóa profile DIE.
- **TUYỆT ĐỐI KHÔNG** để watchdog ca tối (`post_evening_gpm_login_watchdog.py`) tự ý gọi sinh profile. Watchdog ca tối chỉ tập trung đúng một nhiệm vụ: **Login Google & Cấp quyền OAuth**.
- **Self-healing (`cron_chatgpt_web_pool_watchdog.py`):** Chạy lúc `05:00 AM`, chỉ quét các connection **đã có** trong OmniRoute (`:20129`) nhưng bị inactive/mất phiên để hồi sinh. Không chồng chéo với ca tối.

---

## 2. Tiêu chuẩn 3 Nhóm Ưu Tiên Lọc Candidates (Post Evening GPM Login)

Nguồn xác thực tài khoản thành công (Single Source of Truth) **bắt buộc** phải gọi live API OmniRoute:
`GET http://127.0.0.1:20129/api/providers` (lấy danh sách `connections` có `provider == 'antigravity'`). Tuyệt đối không chỉ dựa vào file json log tĩnh cũ.

### 3 Nhóm Ưu Tiên:
1. **ƯU TIÊN 1 (`priority=1`, reason: `has_google_session_ready_oauth`):**
   - Profile GPM trong database `profile_data.db` đã có sẵn Session Cookie Google (`SID, SSID, HSID, SAPISID` trong `Default/Network/Cookies`) nhưng chưa có connection trên OmniRoute `:20129`.
   - **Đặc điểm:** Tài khoản đã login Google từ trước nhưng bị nghẽn mạng/timeout ở bước bắt callback code.
   - **Xử lý:** Chạy là ăn ngay trong 10 giây qua Account Chooser, không hỏi mật khẩu, không checkpoint.
2. **ƯU TIÊN 2 (`priority=2`, reason: `chatgpt_ready_priority`):**
   - Tài khoản chưa login GPM nhưng đã được bồi trust ban ngày (có cờ `CHATGPT_READY` trên Excel hoặc state qua luồng Direct Email OTP trên điện thoại Samsung S7).
3. **ƯU TIÊN 3 (`priority=3`, reason: `ready_gpm_oauth` hoặc `cooldown_24h_retry`):**
   - Các tài khoản còn lại chưa nạp OmniRoute.
   - Nếu tài khoản từng login thất bại trong ca tối trước đó: Bắt buộc phải **cooldown đủ $\ge 24\text{h}$** mới được bốc lại chạy tiếp để tránh spam làm nát tài khoản.

---

## 3. Bản chất Google Checkpoint: Trust Score > 2FA

- **Hiểu lầm tai hại:** "Phải có 2FA mới login được GPM".
- **Sự thật hiện trường:** Google đánh giá dựa trên **Account Trust Score** và độ sạch của môi trường mạng:
  - Tài khoản có trust cao (như `cecilssimpson...`), ngâm đủ ngày và có lịch sử hòm thư: Google cho vào thẳng 100% chỉ với Email + Password, không đòi hỏi 2FA.
  - Chạy đồng thời `MAX_WORKERS = 5` làm nghẽn proxy nội bộ và kích hoạt Google Risk Engine chặn hàng loạt bằng **Hard Phone Checkpoint (`challenge/iap`)**.
- **Quy tắc an toàn:**
  - Luôn clamp `MAX_WORKERS <= 2` cho pipeline login GPM đêm.
  - Tuân thủ trần proxy $\le 2$ acc/port/ngày và máy $\le 1$ acc/ngày.
  - Báo cáo tổng kết phải bao gồm: Kết quả ca, số lượng live trên OmniRoute pool `:20129`, và số lượng profile sẵn session chờ OAuth.
