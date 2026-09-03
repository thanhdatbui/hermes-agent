# Check Live Vận Hành Hàng Up Tay (Manual Products Stock Checklive)

## 1. Danh sách sản phẩm up tay (`supplier_id = 0` / Local Stock)
- **SP 40:** `TikTok Random Live` (format: `username|password|cookie...` -> lấy `UID` = username).
- **SP 57:** `Instagram · 2FA On` (format: `username|password|2fa...` -> lấy `UID` = username).
- **SP 38, 39, 60, 61:** Tạm hết hàng (`stock = 0`, ẩn tự động do `product_hide_outstock=1`).

## 2. Đặc điểm các trang check live bên ngoài
- **`khommo247.com/cong-cu/check-tiktok`:**
  - Input: danh sách username (không gửi password).
  - Bảo vệ: Cloudflare Managed Challenge / WAF -> cURL / server request thuần bị HTTP 403 / HTML challenge. Cần Headless Browser (Playwright) nếu muốn cào tự động.
- **`clonefbig.com/checklive` (IG / FB):**
  - Input: danh sách username (không gửi password).
  - Cơ chế: WebSocket `wss://clonefbig.com/ws/checklive`.
  - Bảo vệ: Bắt buộc kèm `cf_token` từ Cloudflare Turnstile CAPTCHA (single-use, expire sau vài phút). Không có token -> WebSocket bị đóng với mã `1008 policy violation`.
  - API backend: clonefbig không mở public API cho check live (`/api/checklive*.php` đều 404).
  - Tự động hóa thành công: Dùng Playwright Chromium (`--disable-blink-features=AutomationControlled`), Cloudflare Turnstile tự động cấp `cf-turnstile-response` vào input ẩn -> nạp username vào `#inputArea` -> gọi `startCheck()` -> đọc `#liveOutput` / `#dieOutput`.

## 3. Quy trình Cron Daily chuẩn hoá (Đã deploy qua Hermes Cronjob)
- **Cronjob:** `daily-manual-stock-checklive` (`0 3 * * *`, daily 03:00).
- **Script launcher:** `~/AppData/Local/hermes/scripts/daily_manual_stock_checklive.py`.
- **Luồng xử lý:**
  1. Đọc danh sách acc từ `product_stock` theo `product_code` qua SSH MySQL VPS.
  2. Tách chuỗi `account` chỉ lấy `UID` / `username`, bỏ password / 2FA.
  3. Check status:
     - **TikTok (SP 40):** Dùng GitHub Actions Workflow nội bộ (`thanhdatbui/tiktok_check_live`) trigger qua `workflow_dispatch` + download artifact `checklive-result.json`. Vượt 100% WAF/anti-bot.
     - **Instagram (SP 57):** Dùng Playwright tự động hóa qua `clonefbig.com/checklive` (Turnstile auto-token bypass).
  4. Xử lý kết quả DB VPS:
     - **LIVE:** Bỏ qua hoặc cập nhật timestamp.
     - **DIE:** `INSERT INTO product_die` (`type='die_checklive'`) và `DELETE FROM product_stock` trong transaction SQL atomic.
     - Báo cáo kết quả chi tiết về Telegram.
