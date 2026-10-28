# ChatGPT-Web Pool Cooldown and Self-Healing Protocol (OmniRoute gpt-web-sol)

## 1. Bản Chất 2 Dạng "Acc Lỗi / Acc Chết" Trên ChatGPT-Web

Trong hạ tầng OmniRoute nối với Web reverse proxy của OpenAI (`chatgpt-web`), tài khoản không bị xóa/die vĩnh viễn mà rơi vào 2 trạng thái kỹ thuật:

1. **Lỗi 401 Auth Failed (Hết hạn phiên cookie)**:
   - Log: `[401]: ChatGPT auth failed — re-paste your __Secure-next-auth.session-token cookie from chatgpt.com.`
   - Cơ chế: Cookie phiên hết hạn. Connection này hoàn toàn mất quyền gọi API chatgpt.com cho đến khi đăng nhập lại trên trình duyệt để lấy cookie mới.
   - Trạng thái DB: `apiKeyHealth.primary.status = 'invalid'` hoặc `last_error` chứa `401`.

2. **Lỗi Sentinel / Turnstile Block (Cloudflare Challenge ngầm)**:
   - Log: `ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
   - Cơ chế: Cloudflare / OpenAI Sentinel phát hiện traffic bất thường qua proxy IP, dựng rào cản Turnstile (bắt tick Captcha). Backend headless không thể tick nên request bị từ chối tức thì.
   - Trạng thái DB: `last_error` chứa `Sentinel/Turnstile`.

---

## 2. Vì Sao Pool Có Hàng Trăm Acc Sống Mà Vẫn Sập HTTP 503?

- Trong combo `gpt-web-sol`, danh sách models chứa toàn bộ connections (ví dụ 157 accounts).
- Cấu hình mặc định:
  - `strategy: round-robin`
  - `maxGlobalAttempts: 8`
- **Bẫy Round-Robin dính cụm acc liệt**: Khi con trỏ round-robin xoay tới một dải gồm 8 tài khoản liên tiếp bị 401 hoặc Sentinel block, OmniRoute thử tuần tự 8 lần rồi chạm trần `maxGlobalAttempts = 8`.
- Kết quả: OmniRoute bỏ cuộc và ném thẳng lỗi `HTTP 503: Service Unavailable` ra ngoài, mặc dù trong pool còn hơn 110 accounts hoàn toàn khỏe mạnh.

---

## 3. Quy Trình Cô Lập & Tự Hồi Phục (Self-Healing Playbook)

Script canonical chuẩn: `D:/Taadaa/tools/cooldown_broken_chatgpt.py`

### Bước 1: Nguyên Tắc Bất Di Bất Dịch: Cooldown Tạm Thời, CẤM Tắt Vĩnh Viễn / CẤM Xóa Khỏi Pool
- **CẤM TUYỆT ĐỐI**: Đặt `is_active = 0` hoặc xóa connectionId ra khỏi combo `gpt-web-sol`. Tắt vĩnh viễn hoặc xóa khỏi combo là phá hủy tài sản pool, khiến các acc bị loại bỏ hoàn toàn và cron cứu hộ không thể tự động tái kích hoạt.
- **CƠ CHẾ COOLDOWN CHUẨN OMNIROUTE (`rate_limited_until`)**:
  OmniRoute có cơ chế `isAccountUnavailable` / `cooldownUntilMs` đọc trường `rate_limited_until` trong `provider_connections`:
  ```sql
  UPDATE provider_connections
  SET rate_limited_until = datetime('now', '+30 minutes') -- hoặc ISO format 'YYYY-MM-DDTHH:MM:SS.sssZ'
  WHERE provider = 'chatgpt-web' AND is_active = 1
    AND (last_error LIKE '%401%' OR last_error LIKE '%Sentinel%' OR json_extract(provider_specific_data, '$.apiKeyHealth.primary.status') = 'invalid');
  ```
  * **Lưu ý định dạng**: `cooldownUntilMs()` trong OmniRoute coi chuỗi số nguyên là epoch mili-giây, KHÔNG dùng epoch giây (ví dụ `time.time() + 1800` dạng int sẽ bị parse thành năm 1970 và hết hạn ngay lập tức). Luôn dùng chuỗi ISO 8601 UTC.
  * Khi có `rate_limited_until` trong tương lai, router tự động bỏ qua (skip) connection đó trong vòng 30 phút mà KHÔNG cần xóa khỏi combo hay đổi `is_active=0`. Hết 30 phút, router tự động thử lại mà không cần can thiệp thủ công.

### Bước 2: Cron Cứu Hộ Tự Động Định Kỳ
- Pool luôn có Cronjob tự động kiểm tra sức khỏe và hồi sinh tài khoản: `chatgpt-web-pool-healer-watchdog` (Job ID: `fff7f688990d`, script `cron_chatgpt_web_pool_watchdog.py`).
- Cronjob này quét định kỳ qua `GET /api/providers`, gửi request test liveness và tự động giải phóng cooldown hoặc làm mới cookie phiên.

### Bước 3: Nâng Cấp Cấu Hình Định Tuyến Kháng Lỗi Trong Combo
Giữ nguyên toàn bộ 157 models trong combo (để cron và router tự quản lý), chỉ tối ưu tham số định tuyến trong bảng `combos`:
- `strategy`: Chuyển từ `round-robin` sang `cache-optimized` (ưu tiên kết nối đã warm cache và bỏ qua connection đang cooldown).
- `config.maxGlobalAttempts`: Tăng từ `8` lên `25`.
- `config.disableSessionStickiness`: Đặt `True` để không bị kẹt dính vào connection vừa phát sinh lỗi.

---

## 4. Tự Động / Thủ Công Dỡ Bỏ Cooldown Khi Đã Quá Thời Gian Phạt

Khi thời gian `rate_limited_until` đã hết hạn (quá 30 phút), hoặc khi proxy egress đã ổn định trở lại:
1. **Kiểm tra số lượng acc đã hết hạn cooldown**:
   ```sql
   SELECT count(*) FROM provider_connections
   WHERE provider = 'chatgpt-web' AND rate_limited_until IS NOT NULL AND rate_limited_until < datetime('now');
   ```
2. **Dỡ bỏ cooldown và reset backoff**:
   Chạy script canonical `D:/Taadaa/tools/unfreeze_expired_cooldown.py`:
   ```sql
   UPDATE provider_connections
   SET rate_limited_until = NULL, backoff_level = 0, last_error = NULL, updated_at = CURRENT_TIMESTAMP
   WHERE provider = 'chatgpt-web' AND (rate_limited_until < datetime('now') OR rate_limited_until IS NOT NULL);
   ```
3. **Ping Endpoint Làm Mới In-Memory Cache**:
   Gửi request `GET http://127.0.0.1:20129/api/providers` (HTTP 200) để router đồng bộ lại trạng thái từ SQLite vào bộ nhớ RAM của tiến trình OmniRoute. Toàn bộ 100% pool accounts sẽ lập tức sẵn sàng nhận request mới.

