# Telegram Webhook qua Cloudflare Tunnel & Khắc phục Treo Socket ISP

Tài liệu kỹ thuật tổng hợp giải pháp chuyển đổi từ Telegram Long-Polling sang Webhook qua Cloudflare Tunnel và các bẫy chẩn đoán độ trễ / nghẽn Event Loop.

---

## 1. So sánh 3 cơ chế kết nối Telegram Bot

| Cơ chế | Ưu điểm | Nhược điểm & Rủi ro | Phù hợp |
|---|---|---|---|
| **Direct ISP (FPT/Viettel) + Long-polling** | Đơn giản, không cần cấu hình thêm | **Silent TCP Stall:** ISP âm thầm drop kết nối TCP `getUpdates` kéo dài mà không gửi `TCP RST`. Socket rơi vào trạng thái half-open, bot đứng chờ chạm trần timeout (5–10 phút) mới reconnect. | Môi trường VPS quốc tế, không bị ISP can thiệp |
| **Cloudflare WARP (SOCKS5 :40000) + Polling** | Bypass được DPI/bóp gói của ISP trên luồng text | **Lỗi gửi nhận Media:** WARP chạy MASQUE (HTTP/3 UDP), khi truyền file ảnh/voice nặng dễ bị rớt gói/bóp UDP, timeout SOCKS5 văng `NetworkError` / `Host unreachable`. | Chữa cháy tạm thời cho text |
| **Cloudflare Tunnel (cloudflared) + Webhook** | **Push thay vì Poll:** Telegram bắn thẳng HTTP POST về máy qua Cloudflare Edge (< 0.1s). Chấm dứt 100% treo socket ngầm. Media gửi nhận thẳng Direct FPT siêu tốc. | Cần có domain trỏ qua Cloudflare và chạy tiến trình `cloudflared`. | **Khuyến nghị chuẩn 24/7** |

---

## 2. Quy trình thiết lập Cloudflare Tunnel cho Telegram Webhook (Windows)

### Bước 1: Ủy quyền Cert và Tạo Tunnel
```bash
# 1. Ủy quyền zone domain (yêu cầu trình duyệt mở URL để approve domain taadaa.click)
cloudflared.exe tunnel login
# File cert được lưu tại: %USERPROFILE%\.cloudflared\cert.pem

# 2. Tạo tunnel cố định
cloudflared.exe tunnel create hermes-bot
# Trả về UUID, credentials lưu tại: %USERPROFILE%\.cloudflared\<UUID>.json

# 3. Trỏ DNS subdomain về tunnel
cloudflared.exe tunnel route dns hermes-bot bot.taadaa.click
```

### Bước 2: Cấu hình Ingress `~/.cloudflared/config.yml`
```yaml
tunnel: <UUID>
credentials-file: C:\Users\<USER>\.cloudflared\<UUID>.json

ingress:
  - hostname: bot.taadaa.click
    service: http://127.0.0.1:8443
  - service: http_status:404
```

### Bước 3: Khởi động tự động cùng Windows (Startup Script)
Tạo file `cloudflared_tunnel.vbs` trong `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`:
```vbscript
Option Explicit
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\Users\<USER>\.cloudflared\run_tunnel.ps1""", 0, False
Set WshShell = Nothing
```
File `run_tunnel.ps1`:
```powershell
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$config = "C:\Users\<USER>\.cloudflared\config.yml"
while ($true) {
    try {
        & $cloudflared tunnel --config $config run hermes-bot
    } catch {}
    Start-Sleep -Seconds 5
}
```

### Bước 4: Cập nhật biến môi trường `.env` của Hermes
```bash
# Tắt proxy nếu có
# TELEGRAM_PROXY=socks5://127.0.0.1:40000

# Bật Webhook mode
TELEGRAM_WEBHOOK_URL=https://bot.taadaa.click/telegram
TELEGRAM_WEBHOOK_PORT=8443
TELEGRAM_WEBHOOK_SECRET=<random_hex_32_bytes>
```
*Lưu ý: BẮT BUỘC có `TELEGRAM_WEBHOOK_SECRET`. Nếu thiếu, Hermes Gateway sẽ từ chối khởi động vì lý do bảo mật (chống update giả mạo).*

---

## 3. Các cạm bẫy & Chẩn đoán khi "tưởng bot bị treo"

Khi người dùng phản ánh: *"Vừa fix xong sao vẫn thấy bot im 5–6 phút?"*, cần phân biệt ngay 3 nguyên nhân khác nhau:

### Bẫy 1: Nghẽn hàng đợi LLM tại OmniRoute (Admission Queue Congestion)
- **Triệu chứng:** Webhook đã đẩy tin về máy ngay trong 0.01s, nhưng bot không trả lời. Trên Dashboard OmniRoute thấy request xử lý rất lâu hoặc hàng đợi đầy.
- **Nguyên nhân:** Nhiều topic/session khác (farm watchdog, code review, batch agent) đang chạy đồng thời với context lớn (50k–250k tokens).
- **Cách kiểm tra:**
  ```python
  import urllib.request, json
  # Kiểm tra activeConnections và health
  # Nếu > 100 active connections, mỗi request có thể mất 20-30s hàng đợi
  ```
- **Xử lý:** Tăng `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT` (ví dụ từ 9 lên 24) hoặc phân luồng model ưu tiên cho session tương tác chính.

### Bẫy 2: Telegram Webhook "Read timeout expired" do Event Loop bị nghẽn
- **Triệu chứng:** Kiểm tra `getWebhookInfo` thấy `last_error_message: "Read timeout expired"` tại timestamp vừa xảy ra.
- **Nguyên nhân:** Telegram yêu cầu server webhook phải phản hồi `HTTP 200` trong vòng ~5 giây. Nếu tiến trình Gateway đang bị nghẽn CPU/Event loop bởi các tác vụ synchronous (ví dụ lệnh subagent quét `os.walk` ổ đĩa hoặc truy vấn SQLite lock contention trên `state.db`), Tornado server của webhook không kịp trả 200 $\rightarrow$ Telegram đánh dấu fail và chuyển sang retry sau vài phút.
- **Xử lý:**
  - Không chạy các lệnh blocking synchronous trên main thread của Gateway.
  - Nghiêm cấm các script quét đĩa diện rộng (`grep -rn`, `os.walk` trên các cây thư mục lớn như `node_modules`, `runtime`).

### Bẫy 3: Multi-tool loop tích lũy độ trễ (Perceived Freeze)
- **Triệu chứng:** OmniRoute không có request suốt 5 phút, nhưng máy đang cặm cụi chạy tool.
- **Nguyên nhân:** Bot thực thi một chuỗi 10–15 tool calls liên tiếp. Nếu mỗi lượt gọi LLM mất ~20s do tải nặng, tổng thời gian: $15 \times 20s = 300s$ (5 phút). Do Telegram không streaming từng turn trung gian, user thấy bot hoàn toàn im lặng.
- **Kỷ luật điều phối:** Coordinator phải phản hồi tiến độ sớm, tránh tự chạy chuỗi tool quá dài mà không có checkpoint cập nhật cho user.

### Bẫy 4: Cloudflare WAF chặn Webhook bằng Error Code 1010
- **Triệu chứng:** Telegram webhook gọi sang URL `https://<subdomain>.<domain>/telegram` nhận HTTP 403 Forbidden, response body trả về `error code: 1010`.
- **Nguyên nhân:** Cloudflare bật tính năng bảo mật mặc định "Browser Integrity Check" hoặc WAF Managed Rules. Khi Telegram Bot API đẩy request webhook sang, User-Agent header là `TelegramBot (like TwitterBot)` hoặc thiếu standard browser headers, dẫn tới Cloudflare Edge gán cờ bot và chặn cứng với mã lỗi 1010 trước khi request chạm vào Cloudflare Tunnel.
- **Cách chẩn đoán:** Dùng curl/Python gửi POST request với header `User-Agent: Mozilla/5.0...` thì trả 200, nhưng không có UA hoặc UA TelegramBot thì bị 403 `error code: 1010`.
- **Khắc phục:**
  - Trong Cloudflare Dashboard của domain (`dash.cloudflare.com` -> Domain -> Security -> WAF -> Custom Rules):
  - Tạo Custom Rule: nếu `(http.host eq "bot.taadaa.click" and http.request.uri.path eq "/telegram")` -> Action: `Skip` (Skip all remaining WAF / Browser Integrity Check / Rate Limiting).
  - Hoặc tắt "Browser Integrity Check" trong Security -> Settings cho zone domain.
