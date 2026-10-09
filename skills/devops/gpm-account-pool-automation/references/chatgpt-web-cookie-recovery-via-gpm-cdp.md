# ChatGPT-Web Cookie Recovery & OmniRoute Auto-Heal Playbook

## 1. Bản Chất Kỹ Thuật (502 Web vs Proxy Liveness)
- **Hiện tượng:** Tài khoản ChatGPT-Web trên OmniRoute (:20129) liên tục gặp lỗi `HTTP 502 Bad Gateway` (hoặc `403 Forbidden`).
- **Nguyên nhân gốc:** Cổng proxy di động (ví dụ port 5105) **hoàn toàn bình thường**, nhưng cookie phiên của tài khoản trên `chatgpt.com` (`__Secure-next-auth.session-token` hoặc `cf_clearance`) đã bị Cloudflare Turnstile đánh dấu hết hạn / thử thách bot.
- **Hậu quả nếu không có cơ chế cách ly:** OmniRoute tiếp tục dội request vào tài khoản bị lỗi, làm chậm toàn bộ hệ thống và có nguy cơ khiến Cloudflare gắn cờ đen tài khoản vĩnh viễn.

---

## 2. Quy Tắc ModelLockout Cooldown (Chống Dồn Request)
- **Không dùng cooldown quá ngắn (120s):** Thời gian 2 phút không đủ để Cloudflare hạ nhiệt IP hay phiên web.
- **Chuẩn hóa cấu hình Cooldown:**
  - `baseCooldownMs: 600000` (10 phút)
  - `maxCooldownMs: 1800000` (30 phút)
  - `errorCodes: [403, 404, 429, 502, 503, 504]`
  - `useExponentialBackoff: true`
- **Tác dụng:** Khi tài khoản gặp 502/403, router tự động cách ly tài khoản tối thiểu 10 phút, chuyển toàn bộ lưu lượng sang các tài khoản khỏe mạnh khác trong pool.

---

## 3. Quy Trình Auto-Recovery Qua GPM Profile & Playwright CDP

> **NGUYÊN TẮC BẤT BIẾN:** Nick là tài sản, CẤM tắt vĩnh viễn (`isActive: false`) rồi bỏ mặc tài khoản khi gặp lỗi 502. Bắt buộc phải kích hoạt quy trình hồi sinh tự động.

### Pipeline 4 bước:
1. **Khởi động GPM Profile tương ứng:**
   - Gọi GPM Local API: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=0.8`
   - Lấy `remote_debugging_address` (ví dụ `127.0.0.1:xxxxx`).

2. **Vượt Cloudflare Turnstile & Trích xuất Cookie tươi qua CDP:**
   ```python
   from playwright.sync_api import sync_playwright

   with sync_playwright() as pw:
       browser = pw.chromium.connect_over_cdp(f"http://{remote_debugging_address}")
       context = browser.contexts[0]
       page = context.pages[0] if context.pages else context.new_page()
       page.goto("https://chatgpt.com", timeout=45000)
       page.wait_for_timeout(5000)  # Chờ Cloudflare Turnstile xác minh tự động
       
       cookies = context.cookies("https://chatgpt.com")
       cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
       browser.close()
   ```

3. **Dọn dẹp tiến trình:**
   - Gọi `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.

4. **Đồng bộ vào OmniRoute & Nghiệm thu:**
   - Cập nhật connection: `PUT http://127.0.0.1:20129/api/providers/{connection_id}` với payload `{"apiKey": cookie_str, "isActive": true}`.
   - Kiểm tra probe: `POST http://127.0.0.1:20129/api/providers/{connection_id}/test` $\rightarrow$ Xác nhận `valid: true`, `error: null`.

---

## 4. Tự Động Hóa Định Kỳ Bằng Watchdog Cronjob
- Cronjob: `chatgpt-web-pool-healer-watchdog` (Job ID: `fff7f688990d`, script `cron_chatgpt_web_pool_watchdog.py`).
- Lịch chạy chuẩn: `0 * * * *` (Mỗi 1 giờ quét và hồi sinh tự động một lần).
- Đích báo cáo: `telegram:-5373649734` (Farm Alert).
