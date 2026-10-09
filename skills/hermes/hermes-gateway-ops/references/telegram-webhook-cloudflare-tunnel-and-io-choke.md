# Telegram Webhook qua Cloudflare Tunnel & Triệt tiêu Silent Drop / Quét đĩa

## 1. Vấn đề gốc rễ (Root Cause)

1. **Long-Polling kẹt Silent TCP Stall (Treo 5-10 phút):**
   - Mạng ISP (FPT, Viettel) bóp hoặc âm thầm ngắt (silent drop) kết nối TCP long-poll `getUpdates` đến Telegram mà không gửi cờ `TCP RST`.
   - Client rơi vào trạng thái Half-open socket, ngâm 300s-600s mới reconnect.
2. **WARP SOCKS5 bóp gói UDP:**
   - Dùng Cloudflare WARP SOCKS5 proxy (`127.0.0.1:40000`) qua giao thức MASQUE (HTTP/3 UDP) dễ bị nghẽn gói media nặng -> lỗi `NetworkError` khi tải/gửi ảnh.
3. **Giải pháp chuẩn: Telegram Webhook qua Cloudflare Tunnel (`cloudflared`):**
   - Đảo ngược chiều kết nối: Telegram server Singapore push HTTP POST về Cloudflare Edge, Cloudflare Tunnel chuyển tiếp về local `127.0.0.1:8443`.
   - Nhận tin tức thì (<0.1s), không ngâm socket -> triệt tiêu hoàn toàn silent drop.
   - Luồng gửi/tải ảnh đi thẳng Direct FPT siêu tốc (0.7s), không nghẽn proxy.

---

## 2. Cấu hình Webhook & Cloudflare Tunnel trên Windows

### A. Cloudflare Tunnel Setup (`cloudflared.exe`)
1. Lấy chứng chỉ uỷ quyền:
   ```cmd
   "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel login
   ```
   (Mở browser chọn domain, tải cert về `~/.cloudflared/cert.pem`).
2. Tạo Tunnel & Route DNS:
   ```cmd
   "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel create hermes-bot
   "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel route dns hermes-bot bot.taadaa.click
   ```
3. File config `C:\Users\Kibe\.cloudflared\config.yml`:
   ```yaml
   tunnel: <TUNNEL_UUID>
   credentials-file: C:\Users\Kibe\.cloudflared\<TUNNEL_UUID>.json

   ingress:
     - hostname: bot.taadaa.click
       service: http://127.0.0.1:8443
     - service: http_status:404
   ```
4. Auto-start cùng Windows:
   Đặt script VBS trong `shell:startup` gọi runner PowerShell chạy `cloudflared tunnel --config config.yml run <name>`.

### B. Cấu hình Hermes Gateway (`.env`)
```bash
TELEGRAM_WEBHOOK_URL=https://bot.taadaa.click/telegram
TELEGRAM_WEBHOOK_SECRET=<hex_32_bytes_random>
TELEGRAM_WEBHOOK_PORT=8443
# Tắt bỏ hoàn toàn proxy polling cũ:
# TELEGRAM_PROXY=socks5://127.0.0.1:40000
```

---

## 3. Pitfalls khi Hermes có vẻ "treo 6-7 phút" dù Webhook đã hoạt động

Khi user phàn nàn "bot vẫn treo 6-7 phút không thấy tin nhắn / OmniRoute trống trơn 0 request":
1. **Kiểm tra `getWebhookInfo` trước tiên:**
   - Nếu `last_error_message` là `"Read timeout expired"`, nghĩa là Gateway nhận POST nhưng không kịp trả lời HTTP 200 trong 5s.
2. **Nguyên nhân 1 - Quét đĩa diện rộng (Disk I/O Choke):**
   - Subagent hoặc script chạy `os.walk('D:/Taadaa')` hoặc `grep.exe -rn ...` vào node_modules/repo lớn.
   - Khiến `state.db` (SQLite) và filesystem bị lock contention, Event Loop của Gateway bị nghẽn (freeze).
   - Hook `guard_broad_grep.py` bắt buộc phải chặn cả `grep.exe`, `-rn`, và `os.walk` có nháy đơn/ngoặc.
3. **Nguyên nhân 2 - Hàng đợi Admission OmniRoute quá tải:**
   - Nhiều session (15-30 session) chạy ngầm cùng nã context nặng (100k-250k tokens).
   - OmniRoute kẹt `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT` (cần nâng từ 9 lên 24+).
   - Coordinator chạy chuỗi 10-15 tool calls: mỗi call chờ model 20s -> tích lũy 5 phút "im lặng", user tưởng bot treo.
   - **Kỷ luật:** Coordinator ở session chat chính KHÔNG chạy chuỗi tool dài ngầm, phải update trạng thái hoặc dispatch worker.
