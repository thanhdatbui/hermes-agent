# Closed-Loop Feedback: Healer Watchdog -> GPM Login -> Nurture Group 10

## Bối cảnh & Vấn đề thực tế
Khi một tài khoản Gmail chạy song song Antigravity (Google) và Codex (OpenAI) trên OmniRoute:
1. **Lệch trạng thái hai nhánh:** Nhánh Antigravity vẫn giữ OAuth access/refresh token sống (`is_active: 1`), nhưng phiên web Google trên profile GPMLogin đã bị văng (mất sạch cookie `SID`, `SSID`, `HSID`).
2. **Kẹt giữa 3 hệ thống không liên thông:**
   - **Pool Healer Watchdog (`cron_chatgpt_web_pool_watchdog.py`):** Phát hiện Codex bị Timeout OAuth tại `accounts.google.com/v3/signin/identifier`, ghi vào `chatgpt_web_pool_telemetry.json` và gửi cảnh báo nhưng không kích hoạt cứu hộ.
   - **Cron Nuôi Gmail (`cron_gpm_gmail_nurture.py`):** Chỉ nuôi các profile thuộc `GroupId == 10` (`Google_Live_Ready`). Profile đang ở Group 1 ("All") bị skip 100%, không bao giờ được mở để nuôi và không thể phát hiện mất session để gắn cờ `NEEDS_LOGIN`.
   - **Cron Login Watchdog (`post_evening_gpm_login_watchdog.py`):** Có bộ lọc `if em_l in omniroute_success and not is_lost_session: continue`. Vì OmniRoute vẫn có Antigravity active nên coi là success, còn `is_lost_session` chỉ nghe từ Cron Nuôi $\rightarrow$ Bỏ qua vĩnh viễn!

## Kiến trúc Closed-Loop chuẩn hóa

### 1. Thu thập Telemetry Failures (`_get_pool_telemetry_failures`)
Đọc trực tiếp `D:/Taadaa/chatgpt_web_pool_telemetry.json` từ Pool Healer để lấy danh sách tài khoản trong mảng `failures` (hỗ trợ cả định dạng string lẫn dict `{"account": "..."}`).

### 2. Mở rộng điều kiện `is_lost_session`
Trong `post_evening_gpm_login_watchdog.py`:
```python
is_lost_session = (
    (em_l in nurture_needs_login) or
    (em_l in pool_failures) or
    (em_l in omniroute_success and em_l in gpm_emails and em_l not in session_emails)
)
```
- Phân loại priority và reason rõ ràng:
  - `nurture_reported_needs_login` (từ Cron Nuôi).
  - `pool_telemetry_reported_needs_login` (từ Healer Watchdog).
  - `omniroute_missing_gpm_session` (OmniRoute active nhưng GPM rỗng cookie Google).

### 3. Tự động thăng hạng Group 10 (`Auto-Promotion to Group 10`)
Trong hàm `_get_gpm_profiles_with_google_session()`:
- Khi kiểm tra cookie trong profile GPM thấy `cnt >= 2` (có đủ cookie Google `SID`, `SSID`, `HSID`...):
- Nếu profile đó chưa thuộc Group 10 (`GroupId != 10`), lập tức cập nhật:
  ```python
  UPDATE profiles SET GroupId = 10 WHERE ProfilePath = ? AND GroupId != 10
  ```
- Việc này tự động bàn giao tài khoản sang cho Cron Nuôi định kỳ hàng ngày, giữ ấm session và ngăn chặn văng cookie tái diễn.
