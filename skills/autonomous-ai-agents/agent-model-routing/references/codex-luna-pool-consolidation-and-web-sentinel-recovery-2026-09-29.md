# Codex Luna Pool Consolidation, Timeout Invariant & ChatGPT Web Sentinel Recovery (2026-09-29)

## 1. Bối cảnh & Khắc phục Sự Cố Vận Hành

Trong phiên làm việc ngày 29/09/2026, ba sự cố kiến trúc ngầm trên hệ thống OmniRoute (:20129) và Hermes Delegation đã được phát hiện và xử lý dứt điểm:
1. **Lệch Model Thực Thi (Luna Medium vs Luna High):** Hermes cấu hình yêu cầu `cx/gpt-5.6-luna-high`, nhưng request thực tế trong OmniRoute bị hạ xuống `gpt-5.6-luna-medium` do cấu hình cũ trong pool.
2. **Bẫy 2 Pool & Timeout 45s (Lỗi HTTP 499):** Tồn tại song song 2 pool (`codex-luna-pool` và `codex-luna`). Combo cha `omni-worker` trỏ vào `codex-luna-pool` bị kẹp cứng ở `targetTimeoutMs: 45000` (45s), làm văng hàng loạt lỗi 499 khi Luna High suy luận sâu.
3. **Hiểu Nhầm "Ban Nick" ChatGPT Web vs Codex OAuth:** Tài khoản `chuloan02122003@gmail.com` bị OmniRoute đánh dấu `banned` trên Web do lỗi HTTP 403, nhưng thực chất vẫn sống 100% trên Codex. Đã thực nghiệm quy trình giải cứu tự động qua GPM CDP khôi phục trạng thái 200 OK cho Web.

---

## 2. Chuẩn Hóa Phân Vai: Worker Bắt Buộc là Luna High

- **Quyết định đã chốt từ Tournament 15 trận:** Worker chính thức của hệ thống là **`codex/gpt-5.6-luna-high`** (Vô địch với 462.0đ; Luna Medium bị loại ở bán kết với 448.0đ).
- **Phân biệt Model vs Reasoning Effort:**
  * Cấu hình `delegation.reasoning_effort: medium` trong Hermes chỉ là mức suy luận (để khống chế thời gian thi công gọn trong 60–90s, tránh overthinking).
  * **Bản thân model thực thi bắt buộc phải là con não to `gpt-5.6-luna-high`**, tuyệt đối không được hạ xuống `gpt-5.6-luna-medium`.
- **Đã cập nhật:** Toàn bộ 25 tài khoản trong pool Codex đã được chuyển sang `codex/gpt-5.6-luna-high`.

---

## 3. Quy Tắc Gộp Pool & Timeout Invariant ("Để 1 pool thôi")

### A. Quy tắc Gộp Duy Nhất (Single Canonical Pool)
- **Người dùng chốt:** *"Để 1 pool thôi"*.
- CẤM duy trì các pool alias thừa thãi hoặc các biến thể cũ gây phân mảnh cấu hình:
  * Xóa bỏ `codex-luna-pool` (cũ), giữ duy nhất **`codex-luna`**.
  * Xóa bỏ `codex-terra-pool` (cũ), giữ duy nhất **`codex-terra`**.
  * Combo cha `omni-worker` (Tier 3) cập nhật trỏ trực tiếp vào `codex-luna`.
  * Gom toàn bộ các tài khoản sống khỏe (từ 18 lên 25 tài khoản LIVE) vào chung 1 pool duy nhất, loại bỏ các session expired/inactive.

### B. Timeout Invariant Cho Model Thinking (`targetTimeoutMs >= 90000`)
- Model suy luận (`luna-high`, `luna-max`, `terra-high`) có quá trình sinh token suy nghĩ ngầm (1.000–3.000 tokens) trước khi trả về content.
- Nếu `targetTimeoutMs` đặt ở mức 45s (mặc định cũ): OmniRoute sẽ đơn phương ngắt kết nối (HTTP 499 Client Closed Request) đúng ở giây 45–47.
- **Invariant:** Mọi combo/pool chứa model Codex Thinking bắt buộc phải cấu hình:
  ```json
  "config": {
    "targetTimeoutMs": 90000,
    "maxRetries": 1,
    "strategy": "cache-optimized"
  }
  ```

---

## 4. Kiến Trúc Codex OAuth vs ChatGPT Web & Cơ Chế Giải Cứu Sentinel

### A. Bản chất Khác Biệt Giữa 2 Cánh Cửa
| Tiêu chí | Cổng Codex CLI (`codex`) | Cổng ChatGPT Web (`chatgpt-web`) |
|---|---|---|
| **Giao thức** | OAuth 2.0 PKCE Developer (`/v1/responses`) | Reverse-engineered Web Session (`chatgpt.com`) |
| **Bảo vệ Bot** | **KHÔNG CÓ** Cloudflare Sentinel / Turnstile | Được Cloudflare Sentinel & Turnstile bảo vệ gắt gao |
| **Chi phí Quota** | Có hạn ngạch chu kỳ (Codex Scope Allowance) | **0đ chi phí Quota** (Rất lý tưởng cho Sol High review code) |
| **Độ ổn định** | 100% tự động refresh qua `refresh_token` | Cần làm mới cookie định kỳ khi dính cờ Sentinel |

### B. Bản chất Lỗi "Banned" Trên OmniRoute
- Khi OmniRoute gửi request HTTP giả lập trình duyệt, Cloudflare phát hiện không có hành vi rê chuột/màn hình người thật $\rightarrow$ Trả về **HTTP 403 (Sentinel/Turnstile required)**.
- Mã nguồn OmniRoute gán nhãn `test_status = 'banned'`. Đây là **misnomer** (nhầm lẫn thuật ngữ): Tài khoản **KHÔNG BỊ BAN NICK**, mà chỉ đang bị Cloudflare thử thách (`CHALLENGED`).
- Nick chỉ thực sự DIE khi OpenAI trả về *"Your account has been deactivated"* (lúc đó cả Web lẫn Codex đều chết).

### C. Quy trình Tự Động Hóa Giải Cứu (Automated Sentinel Recovery Procedure)
Đã thực nghiệm thành công 100% trên `chuloan02122003@gmail.com`:
1. **Khởi động GPM Profile:** Mở profile Chromium tương ứng qua cổng Proxy Mobi 4G 1:1 (`http://127.0.0.1:19995/api/v3/profiles/start/{pid}`).
2. **Vượt Tường Lửa Tự Nhiên:** Trình duyệt Chromium thật kết hợp IP 4G sạch sẽ tự động vượt qua Cloudflare Sentinel mà không bị chặn.
3. **Xử lý Chuyển Hướng & Form Kẹt:**
   - Nếu gặp màn hình *"Phiên của bạn đã kết thúc"* $\rightarrow$ Click `[Đăng nhập]`.
   - Nếu ở trang Google Consent (`/oauth/id`) $\rightarrow$ Click `[Tiếp tục]`.
   - Nếu OpenAI mở trang `about-you` bắt điền tuổi $\rightarrow$ Điền `age: 23` và submit.
4. **Trích Xuất Session Token:**
   - Lọc cookies lấy `__Secure-next-auth.session-token`.
   - Ghép đầy đủ các chunk `.0`, `.1` nếu token bị chia cắt (độ dài ~4.600 ký tự `eyJhbG...`).
5. **Cập Nhật OmniRoute SQLite:**
   ```sql
   UPDATE provider_connections 
   SET api_key = ?, is_active = 1, test_status = 'active', last_error = NULL, updated_at = CURRENT_TIMESTAMP
   WHERE id = ?;
   ```
6. **Teardown & Verification:** Đóng profile GPM trong khối `finally`, bắn 1 request test inference `chatgpt-web/gpt-5.6-sol-high` xác nhận 200 OK.

---

## 5. Tích Hợp Vào Cron Healer Watchdog (`cron_chatgpt_web_pool_watchdog.py`)

Cơ chế này được chuẩn hóa để tích hợp vào cronjob `0 5 * * *` (05:00 AM hàng ngày):
- **Concurrency = 1 (Tuần tự tuyệt đối):** Mỗi thời điểm chỉ mở đúng 1 profile GPM để tránh quá tải RAM và nghẽn port proxy.
- **Fail-Fast Circuit Breaker:** Bỏ qua ngay các nick bị Google SMS Checkpoint hoặc OpenAI Deactivated, không retry mù quáng.
- **Inference Verification Gate:** Bắt buộc test phản hồi model Sol High thành công trước khi kết luận hồi sinh.
