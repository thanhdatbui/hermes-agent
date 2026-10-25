# Pitfall: Dual-Provider (Antigravity vs Codex) Session Desync in GPM Login Watchdog

## Triệu chứng
- Cron `chatgpt-web-pool-healer-watchdog` báo tài khoản Codex bị lỗi `Timeout OAuth sau 90s` (hoặc `OAuth token revoked / Google SID missing`).
- Kiểm tra cookie trong GPM Profile (`Default/Network/Cookies`) thấy đã mất sạch session Google (`SID`, `SSID`, `HSID`).
- Tuy nhiên, cron `post_evening_gpm_login_watchdog.py` hoàn toàn **KHÔNG** đưa tài khoản này vào danh sách candidate để re-login vào các ca rảnh.

## Nguyên nhân cốt lõi (Giao thoa giữa 2 hệ thống)
1. **Lệch trạng thái giữa Antigravity và Codex:**
   - Cùng một Gmail (ví dụ: `lamngocdiep030420000304@gmail.com`) được nạp cả 2 provider trên OmniRoute: Antigravity (Google AI Pro) và Codex (OpenAI via Google SSO).
   - Antigravity lưu token OAuth/API riêng trên OmniRoute và vẫn đang `is_active: 1`.
   - Trong khi đó, phiên đăng nhập Google trong trình duyệt GPM đã bị văng, khiến Codex không thể re-auth qua "Continue with Google".
2. **Bộ lọc loại trừ của GPM Login Watchdog (`omniroute_success`):**
   - Trong `post_evening_gpm_login_watchdog.py`:
     ```python
     omniroute_success = _get_live_omniroute_antigravity_emails()
     ...
     if em_l in omniroute_success and not is_lost_session:
         continue
     ```
   - Watchdog kiểm tra `:20129/api/providers` thấy Antigravity vẫn đang `active`, nên tự động xếp email này vào `omniroute_success` và bỏ qua.
3. **Cờ `is_lost_session` không được kích hoạt:**
   - Cờ này phụ thuộc vào `gpm_gmail_nurture_state.json` (do `cron_gpm_gmail_nurture.py` gắn cờ `status == "NEEDS_LOGIN"`).
   - Nếu profile GPM nằm ở Group mặc định (`GroupId: 1` - All) thay vì nhóm nuôi (`GroupId: 10` - Google_Live_Ready), cron nuôi sẽ không bao giờ mở profile này ra để kiểm tra cookie, dẫn đến `NEEDS_LOGIN` không bao giờ được set.

## Biện pháp khắc phục & Quy trình xử lý
1. **Khắc phục tức thì:**
   - Chạy login thủ công chỉ định profile đó hoặc tạm thời nạp email vào `gpm_gmail_nurture_state.json` với `status: "NEEDS_LOGIN"`.
   - Hoặc gán profile vào `GroupId: 10` để cron nuôi tự động phát hiện mất session.
2. **Quy tắc thiết kế tương lai cho Watchdog:**
   - Khi kiểm tra `omniroute_success`, nếu acc có connection Codex bị fail/inactive hoặc `chatgpt_web_pool_telemetry.json` báo `TIMEOUT`/`OAuth token revoked`, không được dùng Antigravity live để chặn re-login.
