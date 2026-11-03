# OmniRoute ChatGPT-Web Turnstile 403 Burst RCA, Subnet Taint vs 4G/R3G & 3-Way Proxy Sync (2026-11-03)

## 1. Hiện Tượng: Vệt "TI: 0 | TO: 0" & Bão Turnstile Trên Dashboard OmniRoute (:20129)
- **Triệu chứng:** Trên OmniRoute Dashboard xuất hiện liên tiếp 5–8 request có `TI: 0 | TO: 0` với TPS `-`, kéo dài trong 30–60 giây, sau đó session bị ngâm đơ hoặc văng lỗi.
- **Nguyên nhân cốt lõi (Bóc tách cơ chế Cloudflare Sentinel):**
  1. **Khác biệt giữa API Test và Real Chat Request:**
     - Endpoint kiểm tra sức khỏe `/api/providers/{cid}/test` chỉ gọi `GET /api/auth/session` để đối soát session token. Endpoint này **KHÔNG kích hoạt kiểm tra Sentinel**, nên luôn trả về `valid: true`.
     - Tuy nhiên, khi vào lượt chat thực tế, OmniRoute bắn request vào `POST /backend-api/sentinel/chat-requirements/prepare`. Tại đây Cloudflare kiểm tra danh tiếng IP (Threat Score / ASN). Nếu IP bị đưa vào diện rủi ro, Cloudflare chặn đứng với **HTTP 403 (Sentinel/Turnstile required)**.
     - Hệ quả: Watchdog/cron kiểm tra thấy `valid: true` nên chỉ bật lại `is_active=1` mà không mở GPM giải captcha, nhưng ngay lượt chat kế tiếp tài khoản lại bị ném 403 và chuyển về `testStatus: banned`.
  2. **Bẫy Dồn Dập Fallback (Cascade Burst):**
     - Cấu hình cũ: `retryDelayMs: 500` và `maxGlobalAttempts: 8` (thậm chí 25 trên `gpt-web-sol`).
     - Khi acc đầu dính 403, OmniRoute nhảy acc tiếp theo chỉ sau 0.5s. Việc bắn dồn dập 8 request/phút từ cùng dải IP khiến Cloudflare định danh hành vi spam bot và quét ban dây chuyền cả cụm.

---

## 2. Phân Tích Thực Tế Tỷ Lệ Lỗi Theo Dải Mạng Proxy (Subnet Taint)
Đối soát trực tiếp bảng `proxy_logs` trong CSDL `.omniroute/storage.sqlite`:
- **Cụm Cáp Quang Cố Định MikroTik Đà Nẵng (`mirotik1.taadaa.click:100xx`):**
  * 230 lỗi / 274 thành công (**Tỷ lệ xịt ~46%**, trong đó 196 lỗi là `[403]: Sentinel/Turnstile required`).
  * Dải IP PPPoE của Viettel Đà Nẵng bị Cloudflare theo dõi sát và liên tục bắt giải Turnstile.
- **Cụm MobiProxy 4G Thái Bình (`test.taadaa.click:51xx`):**
  * 2.339 thành công / 170 lỗi (**Tỷ lệ sống ~93%**). Dải IP 4G xoay vòng ít bị Cloudflare gắn cờ bot.
- **Cụm Xiaomi R3G Thái Bình (`tb.taadaa.click:5141–5158`):**
  * 16 cổng Tinyproxy Direct WAN, đo kiểm thực tế phản hồi 100% IP Public Viettel sạch, không bị dính Turnstile.

---

## 3. Bộ Thông Số Chuẩn Hóa Cho Combo ChatGPT-Web Trên OmniRoute
Cập nhật trong bảng `combos` (trường `data.config`):
```json
{
  "strategy": "round-robin",
  "stickyRoundRobinLimit": 0,
  "disableSessionStickiness": true,
  "retryDelayMs": 1500,
  "maxGlobalAttempts": 4,
  "failoverBeforeRetry": true,
  "disablePromptCacheAffinity": true
}
```
- **`retryDelayMs = 1500` (1.5s):** Giãn nhịp thở tối thiểu 1.5s giữa các lần failover, triệt tiêu tín hiệu burst request trong mắt Cloudflare.
- **`maxGlobalAttempts = 4`:** Ngắt sớm (fail-fast) sau tối đa 4 lần thử thất bại để combo nhảy sang nhánh model dự phòng (như Antigravity/Gemini-Web), tránh ngâm session chat quá 30 giây.

---

## 4. Quy Trình Đồng Bộ Trọn Vẹn 3 Mắt Xích (3-Way Proxy Synchronization)
Khi chuyển các máy farm sang cụm proxy mới (ví dụ 32 máy S7 M203..M272 sang R3G 16 port):

### Bước 1: Nạp Proxy Vào OmniRoute Registry (`proxy_registry`)
- Thêm 16 port R3G (`tb.taadaa.click:5141–5158`) với `type: 'http'`, user/pass rỗng (do đã có scan guard whitelist).

### Bước 2: Ánh Xạ Tài Khoản OmniRoute (`proxy_assignments`)
- Dựa trên bảng quy hoạch:
  * `5141`: M203, M204 | `5142`: M208, M211 | `5143`: M213, M217 | `5144`: M220, M223
  * `5145`: M227, M230 | `5146`: M233, M235 | `5147`: M238, M241 | `5148`: M243, M246
  * `5151`: M251, M253 | `5152`: M255, M260 | `5153`: M262, M264 | `5154`: M268, M270
  * `5155`: M261, M263 | `5156`: M265, M266 | `5157`: M267, M269 | `5158`: M271, M272
- Cập nhật `proxy_assignments.proxy_id` của từng tài khoản tương ứng sang `proxy_id` của R3G, đồng thời reset `test_status = 'active'`, `error_code = NULL`.

### Bước 3: Đồng Bộ Profile GPMLogin Qua Local API (Port 19995)
- Duyệt các profile GPM có tên định dạng `M<mid> - <email> - <port>`.
- Gửi `POST http://127.0.0.1:19995/api/v3/profiles/update/{pid}` với payload:
  `{"raw_proxy": "tb.taadaa.click:<target_port>"}`.
- Đảm bảo cả 3 mắt xích: **Phone S7 Sing-box (`20000 + M`) $\leftrightarrow$ GPM Profile (`tb.taadaa.click:<port>`) $\leftrightarrow$ OmniRoute Connection (`tb.taadaa.click:<port>`)** đi chung 1 cổng upstream.

---

## 5. Quy Trình Reset PPPoE MikroTik & Cập Nhật Tức Thời Whitelist
1. **Reset PPPoE qua RouterOS REST API (`192.168.110.2:9090`):**
   ```python
   # Lấy target .id của pppoe-out1
   # PATCH /interface/pppoe-client/{id} với {"disabled": "true"}
   # sleep 2s
   # PATCH /interface/pppoe-client/{id} với {"disabled": "false"}
   # Poll kiểm tra IP mới tại /ip/address
   ```
2. **Kích hoạt tức thời cập nhật Whitelist:**
   - Ngay sau khi đổi IP, BẮT BUỘC gọi ngay cronjob `mobiproxy-scan-guard-auto-ip` (`update_mikrotik_scan_guard.py`) để nạp IP WAN mới vào tường lửa MobiProxy và R3G Tinyproxy, tránh nguy cơ sập toàn cụm do IP cũ bị loại khỏi whitelist.
