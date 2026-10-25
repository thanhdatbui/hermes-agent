# Pitfall & Closed-Loop Architecture: Dual-Provider (Antigravity vs Codex) Session Desync in GPM Login Watchdog

## 1. Triệu chứng & Hiện tượng "Kẹt giữa 2 làn nước"
- Cron `chatgpt-web-pool-healer-watchdog` (job `fff7f688990d`) phát hiện và ghi nhận vào `chatgpt_web_pool_telemetry.json`:
  * Tài khoản Codex lỗi `Timeout OAuth sau 90s. URL: https://accounts.google.com/v3/signin/identifier?...` hoặc `OAuth token revoked / Google SID missing`.
- Kiểm tra cookie trong GPM Profile (`Default/Network/Cookies`) thấy đã mất sạch session Google (`SID`, `SSID`, `HSID`).
- Tuy nhiên:
  * **Cron Login Gmail (`post_evening_gpm_login_watchdog.py`):** Hoàn toàn KHÔNG đưa tài khoản này vào candidates để login lại vào các ca rảnh.
  * **Cron Nuôi Gmail (`cron_gpm_gmail_nurture.py`):** Hoàn toàn KHÔNG nuôi và không kiểm tra liveness của tài khoản này.

---

## 2. Nguyên nhân cốt lõi (3 Điểm mù liên thông / Siloed Crons)
1. **Lệch trạng thái Dual-Provider trên OmniRoute:**
   * Cùng một Gmail (ví dụ: `lamngocdiep030420000304@gmail.com`) được nạp cả 2 provider trên OmniRoute: Antigravity (Google AI Pro, `tier: g1-pro-tier`) và Codex (OpenAI via Google SSO).
   * Antigravity giữ token OAuth riêng và vẫn đang `is_active: 1`.
   * Trình duyệt GPM văng cookie Google khiến Codex không thể re-auth qua "Continue with Google".
2. **Bộ lọc loại trừ của GPM Login Watchdog (`omniroute_success`):**
   * Trong `post_evening_gpm_login_watchdog.py`:
     ```python
     omniroute_success = _get_live_omniroute_antigravity_emails()
     ...
     if em_l in omniroute_success and not is_lost_session:
         continue
     ```
   * Watchdog thấy Antigravity vẫn active trên OmniRoute nên đánh dấu `omniroute_success` và bỏ qua.
   * `is_lost_session` chỉ lắng nghe duy nhất `nurture_needs_login` từ `gpm_gmail_nurture_state.json`.
3. **Rào chắn cứng của Cron Nuôi (`GroupId == 10`):**
   * `cron_gpm_gmail_nurture.py` có rào chắn `DEFAULT_NURTURE_GROUP_ID = 10` (`Google_Live_Ready`).
   * Các profile nằm ở Group 1 ("All") hoặc Group 0 bị `skipped_group += 1` bỏ qua 100%.
   * Vì cron nuôi không mở profile, nó không bao giờ phát hiện mất session để ghi cờ `NEEDS_LOGIN`.
   * Kết quả: Vòng lặp mù chéo — Cron nuôi bỏ qua vì sai GroupId, Cron login bỏ qua vì tưởng đã xong trên OmniRoute.

---

## 3. Kiến trúc sửa đổi khép kín (Closed-Loop Repair Specification)

### A. Mở rộng định nghĩa `is_lost_session` trong `post_evening_gpm_login_watchdog.py`:
Tài khoản kể cả đã có trong `omniroute_success` bắt buộc phải re-login khi thỏa mãn BẤT KỲ điều kiện nào:
1. `em_l in nurture_needs_login` (nguồn nurture truyền thống).
2. **Telemetry Failures Bridge:** Đọc `D:/Taadaa/chatgpt_web_pool_telemetry.json` -> nếu email nằm trong mảng `failures` với lỗi `TIMEOUT` / `accounts.google.com` / `EMPTY_SESSION_TOKEN` / `OAuth token revoked / Google SID missing` -> Đánh dấu `is_lost_session = True`.
3. **Zero-Cookie Audit:** Đã có profile GPM nhưng hàm `_get_gpm_profiles_with_google_session()` trả về `em_l not in session_emails` (thiếu `SID/SSID/HSID` thực tế trên đĩa) -> Đánh dấu `is_lost_session = True`.

### B. Cơ chế Auto-Promotion lên Group 10 (`Google_Live_Ready`):
- Trong chu kỳ kiểm tra profile GPM của `post_evening_gpm_login_watchdog.py` hoặc `sync_gpm_lifecycle.py`:
  * Nếu phát hiện profile có cookie Google sống (`cnt >= 2` cookies `SID`, `SSID`, `HSID`) nhưng vẫn đang ở `GroupId != 10`:
    ```python
    conn.execute("UPDATE profiles SET GroupId = 10 WHERE Id = ?", (pid,))
    ```
  * Tự động bàn giao cho `cron_gpm_gmail_nurture.py` tiếp quản giữ ấm cookie hàng ngày.

### C. Fallback cho Cron Nuôi (`cron_gpm_gmail_nurture.py`):
- Cho phép nuôi bổ sung các profile có email nằm trong danh sách Active của OmniRoute hoặc có session cookie Google sống, không phụ thuộc cứng 100% vào trường `GroupId` tĩnh trong DB.
