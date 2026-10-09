# GPM Login Session Cookie vs OAuth Pipeline & Multi-Tier Account Candidate Selection

## 1. Bản chất phân biệt: Login Google Thành Công vs Hoàn Tất OAuth OmniRoute

### A. Hiện tượng Session Cookie còn sống nhưng chưa OAuth
- Một tài khoản có thể **đã đăng nhập Google thành công vào trình duyệt GPM** (Chromium lưu session cookie: `SID`, `SSID`, `HSID`, `SAPISID` trong `Default/Network/Cookies` hoặc `Default/Cookies`).
- Tuy nhiên, tài khoản đó vẫn **CHƯA có trên OmniRoute (`:20129`)** do ở bước cuối (`/api/oauth/antigravity/authorize`) bị timeout 180s, nghẽn mạng proxy đa luồng, hoặc chưa kịp click nút *"Tiếp tục / Cho phép"* để đổi `code` lấy `connection_id`.
- **Cơ hội bứt phá:** Khi mở lại các profile này, Google sẽ hiện ngay màn hình **Account Chooser (Chọn tài khoản)** mà **KHÔNG hỏi mật khẩu, KHÔNG đòi 2FA và KHÔNG kích hoạt Checkpoint**. Click chọn tên là lấy được mã OAuth ngay lập tức trong 5-10 giây!

### B. Single Source of Truth cho OmniRoute Pool
- CẤM chỉ tin vào file log cục bộ cũ `oauth_pipeline_status.json` (thường bị outdated nếu có batch nạp thủ công hoặc qua API khác).
- BẮT BUỘC truy vấn trực tiếp server OmniRoute qua API:
  `http://127.0.0.1:20129/api/providers` (lọc `provider == 'antigravity'`) để lấy danh sách live connections thực tế làm chuẩn tuyệt đối trước khi lọc candidates.

---

## 2. Phân tách rành mạch trách nhiệm: Sync Lifecycle vs Login Watchdog

- **Cron `sync_gpm_lifecycle.py` (07:15 - 08:45):**
  - Chịu trách nhiệm tạo mới Profile GPM cho các Gmail LIVE mới từ `master_gmail_manager.xlsx`.
  - Dọn dẹp/xóa các Profile GPM của Gmail bị DIE / BAN.
- **Watchdog ca tối `post_evening_gpm_login_watchdog.py`:**
  - **TUYỆT ĐỐI KHÔNG ôm đồm việc tạo profile mới**.
  - CHỈ tập trung vào việc **Login và OAuth** cho các profile đã tồn tại trên GPM.

---

## 3. Kiến trúc 3 tầng ưu tiên (3-Tier Priority Selection) khi lọc Candidates

Khi watchdog ca tối chuẩn bị danh sách chạy:
1. **Tier 1 (Ưu tiên số 1 - Sẵn Cookie):**
   - Các Profile GPM đã có cookie Google Session nhưng chưa nạp vào OmniRoute `:20129`.
   - Nhóm này chạy đơn lẻ hoặc với worker thấp sẽ thành công 100% với tốc độ cực nhanh.
2. **Tier 2 (Ưu tiên số 2 - Acc mới đã bồi Trust):**
   - Các Profile GPM chưa login, nhưng Gmail trên S7 đã có cờ `CHATGPT_READY` (đã có lịch sử nhận email OTP trên thiết bị thật để bồi Trust Score).
3. **Tier 3 (Ưu tiên số 3 - Acc Fail trước đó đã Cooldown đủ):**
   - Các Profile GPM từng đăng nhập thất bại ở các ca trước.
   - **Quy tắc Cooldown:** Chỉ bốc lại khi đã qua thời gian giãn cách an toàn ($\ge 24\text{h}$) kể từ lần thử gần nhất (`last_attempt`).
   - Tuyệt đối không retry ngay trong cùng một ca tối để tránh cháy hạn mức proxy (`proxy_limit <= 2 acc/port/ngày`) và tránh Google gắn cờ spam.

---

## 4. Trần an toàn Concurrency
- `MAX_WORKERS = 2` là trần an toàn tối đa cho Playwright chạy qua proxy 4G/nội bộ farm.
- Chạy `MAX_WORKERS >= 5` gây tranh chấp tiến trình, nghẽn mạng proxy và làm tăng Fraud Score của Google, dẫn đến timeout oan ở bước redirect OAuth.
