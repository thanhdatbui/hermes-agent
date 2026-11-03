# ChatGPT-Web Cloudflare Turnstile 403: IP/ASN Reputation vs. Token Validity & In-Flight Triage RCA (2026-11-03)

## 1. Hiện Tượng & Nhầm Lẫn Chẩn Đoán Thường Gặp
- **Triệu chứng trên Dashboard (:20129):** Xuất hiện chuỗi 5–8 request liên tiếp mang `TI: 0 | TO: 0`, TPS `-`.
- **Sai lầm phổ biến của Agent:**
  1. *Đoán mò cấu hình dồn tải:* Cho rằng combo bị cấu hình sai dồn vào 1–2 acc, trong khi thực tế combo đã bật `round-robin`, `disableSessionStickiness: true`, `maxGlobalAttempts: 8`.
  2. *Bảo User bấm `/new`:* Khi User đang làm dở task mà bị treo turn, bảo bấm `/new` là **tối kỵ** vì xóa sạch context lịch sử phiên. Phải dùng `/stop` để ngắt turn ngâm và giữ nguyên context, hoặc đổi sang model pool sạch (`/model ag-gemini-pool-3`).
  3. *Đổ lỗi token chết / thắc mắc tại sao cron không cứu được:* Cron watchdog kiểm tra qua `POST /api/providers/{cid}/test` chỉ gọi `GET /api/auth/session` (vẫn trả về `valid: true`). Nhưng khi chat thật chạm vào `/backend-api/sentinel/chat-requirements/prepare`, Cloudflare ném ngay `403 Sentinel/Turnstile required`.

## 2. Bản Chất Kỹ Thuật (Ground Truth từ `.omniroute/storage.sqlite`)

### A. Kiểm tra Proxy Phân Tán vs. Dải IP / ASN Bị Flagged
- Trong bảng `proxy_assignments`, các tài khoản được gán proxy riêng từng port. Tuy nhiên:
  - Nếu nhiều port cùng trỏ về một cụm router (ví dụ `mirotik1.taadaa.click:10001 - 10035` thuộc cùng 1 dải IP WAN PPPoE): Cloudflare đánh giá mức độ rủi ro (Threat Score) theo **dải IP / subnet / ASN**, không theo port cục bộ.
  - Khi dải IP đó bị đưa vào diện nghi vấn, toàn bộ request đi qua các port của cụm đó đều bị Cloudflare yêu cầu giải Turnstile Captcha.
  - Đối soát thực tế: Cụm MikroTik Đà Nẵng dính 196 lỗi 403 Sentinel (tỷ lệ lỗi ~46%), trong khi cụm MobiProxy 4G (`test.taadaa.click`) đạt tỷ lệ sống 93% (2.339 success / 170 error).

### B. Cơ Chế Bão Fallback (Cascade Burst)
- Khi `maxGlobalAttempts: 8` và `retryDelayMs: 500`, 1 request thất bại sẽ kích hoạt 8 lần thử liên tiếp trong vài giây.
- Nếu đa số tài khoản trong pool được gán vào cụm proxy đang bị gắn cờ, 8 lần thử đều đi qua cùng dải IP WAN $\rightarrow$ Cloudflare càng siết chặt và trả 403 đồng loạt $\rightarrow$ sinh ra vệt `TI: 0 | TO: 0`.

### C. Lỗ Hổng Kiểm Tra Của Cron Healer Watchdog
- `cron_chatgpt_web_pool_watchdog.py` kiểm tra `api/providers/{cid}/test` $\rightarrow$ Endpoint này chỉ xác thực session cookie với `api/auth/session` (không qua Sentinel) $\rightarrow$ luôn trả về `valid: true`.
- Script ngỡ tài khoản còn sống nên chỉ set `is_active = 1` mà không mở GPM để giải Captcha.
- Khi có chat thật phát sinh, Cloudflare ném 403 trở lại, đưa acc về `test_status: banned`.

## 3. Quy Trình Khắc Phục & Kỷ Luật Điều Phối
1. **Tuyệt đối không xui User `/new` khi task đang dở:**
   - Dùng `/stop` để hủy turn đang kẹt socket.
   - Chuyển tức thời sang pool sạch bằng `/model ag-gemini-pool-3` hoặc `/model gemini-web` (Argon pool) để tiếp tục task ngay lập tức.
2. **Khắc phục tầng mạng:**
   - Reconnect / renew IP WAN PPPoE trên router đang dính đòn (MikroTik Đà Nẵng).
   - Di dời các tài khoản `chatgpt-web` từ cụm cáp quang cố định sang cụm MobiProxy 4G (`test.taadaa.click`).
3. **Nâng cấp Watchdog Probe:**
   - Probe kiểm tra sức khỏe của `chatgpt-web` bắt buộc phải bắn thử vào endpoint sentinel (`chat-requirements/prepare`), không chỉ kiểm tra thụ động `api/auth/session`.
