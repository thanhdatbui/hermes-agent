# Telegram Webhook Mode qua Cloudflare Named Tunnel (bot.taadaa.click)

## 1. Bối cảnh & So sánh 3 giải pháp kết nối Telegram

Khi vận hành Telegram Bot trên hệ thống Phone Farm tại Việt Nam (đặc biệt là mạng FPT/Viettel kết nối tới Telegram DC5 Singapore):

| Giải pháp | Cơ chế | Ưu điểm | Nhược điểm / Rủi ro |
|---|---|---|---|
| **1. Direct Long-polling** | Giữ kết nối TCP HTTP long-poll liên tục (`getUpdates`) | Không cần cấu hình thêm domain hay proxy | **Bị drop socket ngầm (Silent TCP Stall):** ISP DPI âm thầm ngắt TCP không gửi RST/FIN. Thư viện đợi đủ 300s (5 phút) timeout mới reconnect $\rightarrow$ Bot bị nín/treo 5–8 phút rồi mới xả dồn tin nhắn. |
| **2. Cloudflare WARP SOCKS5 (`127.0.0.1:40000`)** | Đóng gói traffic Telegram qua WireGuard/MASQUE | Che giấu SNI và IP Telegram khỏi DPI của ISP VN, giảm 90% lỗi Timeout | **Vẫn bị drop socket:** WARP daemon đôi khi bị mất kết nối ngắn với Cloudflare edge hoặc kẹt daemon $\rightarrow$ ném lỗi `httpx.ProxyError: Proxy Server could not connect: Host unreachable` khiến bot ngắt polling 5–8 phút. |
| **3. Cloudflare Tunnel Webhook Mode (KHUYÊN DÙNG - TRIỆT TIỂU 100% LỖI)** | Telegram chủ động gửi **HTTP POST (Push)** về domain riêng (`https://bot.taadaa.click/telegram`) | **Miễn nhiễm hoàn toàn với Silent TCP Stall:** Không giữ socket ngâm. Tin nhắn đẩy tức thì (<200ms). Hoàn toàn độc lập với DPI của ISP VN. | Cần 1 domain trỏ qua Cloudflare DNS và chạy daemon `cloudflared`. |

---

## 2. Kiến trúc luồng Webhook (Push Architecture)

```
[User Telegram Client]
          │
          ▼
[Telegram Datacenter 5 (Singapore)]
          │  (HTTP POST Push tới https://bot.taadaa.click/telegram)
          ▼
[Cloudflare Edge Anycast CDN (Bảo vệ DDoS, SSL/TLS tự động)]
          │  (Đường hầm bảo mật QUIC / WireGuard)
          ▼
[cloudflared.exe (Chạy nền trên Windows Host)]
          │  (HTTP Forwarding nội bộ localhost)
          ▼
[Hermes Gateway Webhook Server (0.0.0.0:8443)]
          │
          ▼
[Hermes Agent Dispatch & Reply]
```

---

## 3. Quy trình triển khai chuẩn (End-to-End Setup)

### Bước 1: Cài đặt Cloudflared
```bash
winget install --id Cloudflare.cloudflared --silent --accept-package-agreements --accept-source-agreements
# Binary nằm tại: C:\Program Files (x86)\cloudflared\cloudflared.exe
```

### Bước 2: Ủy quyền và tạo chứng chỉ Cloudflare
- Chạy lệnh ủy quyền:
  `"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel login`
- Mở link hiện ra trên trình duyệt (hoặc dùng Chrome CDP nếu đã đăng nhập Cloudflare Dashboard).
- Chọn zone domain của mình (ví dụ `taadaa.click`) và bấm **Authorize**.
- Cloudflare sẽ tự động ghi chứng chỉ vào: `C:\Users\<user>\.cloudflared\cert.pem`.

### Bước 3: Tạo Named Tunnel & Gán Route DNS
```powershell
$cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

# 1. Tạo Tunnel mới (vd: hermes-bot)
& $cf tunnel create hermes-bot
# Kết quả sinh ra file credentials JSON: ~/.cloudflared/<tunnel-id>.json

# 2. Định tuyến subdomain DNS sang Tunnel vừa tạo
& $cf tunnel route dns hermes-bot bot.taadaa.click
# Cloudflare tự động thêm bản ghi CNAME bot.taadaa.click trỏ về <tunnel-id>.cfargotunnel.com
```

### Bước 4: Tạo file cấu hình Tunnel (`~/.cloudflared/config.yml`)
Ghi nội dung sau vào `C:\Users\Kibe\.cloudflared\config.yml`:
```yaml
tunnel: ee4f1e6f-56e9-4f77-889c-7af16e176569
credentials-file: C:\Users\Kibe\.cloudflared\ee4f1e6f-56e9-4f77-889c-7af16e176569.json

ingress:
  - hostname: bot.taadaa.click
    service: http://127.0.0.1:8443
  - service: http_status:404
```

### Bước 5: Cấu hình Daemon chạy ngầm 24/7 (Zero-Flicker)
1. **Script quản trị vòng lặp auto-restart (`C:\Users\Kibe\.cloudflared\run_tunnel.ps1`):**
   ```powershell
   $cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
   $config = "C:\Users\Kibe\.cloudflared\config.yml"

   while ($true) {
       try {
           & $cloudflared tunnel --config $config run hermes-bot
       } catch {}
       Start-Sleep -Seconds 5
   }
   ```
2. **Khởi động cùng Windows qua Startup VBS (`C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\cloudflared_tunnel.vbs`):**
   ```vbscript
   Option Explicit
   Dim WshShell
   Set WshShell = CreateObject("WScript.Shell")
   WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\Users\Kibe\.cloudflared\run_tunnel.ps1""", 0, False
   Set WshShell = Nothing
   ```

### Bước 6: Cấu hình Hermes Gateway (`.env`)
Thêm các biến cấu hình Webhook vào `$HERMES_HOME\.env`:
```bash
# Bật Webhook Mode thay cho Polling:
TELEGRAM_WEBHOOK_URL=https://bot.taadaa.click/telegram
TELEGRAM_WEBHOOK_PORT=8443

# BẮT BUỘC: Secret token chống giả mạo update (GHSA-3vpc-7q5r-276h)
# Sinh ngẫu nhiên bằng Python: secrets.token_hex(32)
TELEGRAM_WEBHOOK_SECRET=eb658efc123aaf58839b5fe68a67624975efc386a37d34fa3448fc1298e5ad2d

# Tắt Proxy SOCKS5 (để request outbound gửi direct hoặc qua DNS sạch, không phụ thuộc WARP daemon)
# TELEGRAM_PROXY=socks5://127.0.0.1:40000
```

### Bước 7: Khởi động lại Gateway
Chạy kịch bản `delayed-restart.ps1` để nạp cấu hình mới mà không làm gián đoạn bot.

---

## 4. Checklist Thẩm Định Nghiệm Thu (O(1) Verification)

1. **Kiểm tra tiến trình Tunnel sống:**
   `Get-Process cloudflared | Select-Object Id, ProcessName, Responding` $\rightarrow$ `Responding: True`.
2. **Kiểm tra cổng Webhook cục bộ của Hermes:**
   `Get-NetTCPConnection -LocalPort 8443` $\rightarrow$ Phải có 1 socket ở trạng thái `Listen` (do Hermes mở) và các socket `Established` từ cloudflared.
3. **Kiểm tra thông qua Telegram API `getWebhookInfo`:**
   ```bash
   curl -s https://api.telegram.org/bot<TOKEN>/getWebhookInfo
   ```
   **Dấu hiệu chuẩn 100%:**
   - `"url": "https://bot.taadaa.click/telegram"`
   - `"pending_update_count": 0`
   - `"has_custom_certificate": false`
4. **Kiểm tra phản hồi Public Endpoint:**
   `curl -s -I https://bot.taadaa.click/telegram` $\rightarrow$ Trả về `HTTP/1.1 405 Method Not Allowed` từ máy chủ Hermes (do PTB Webhook chỉ chấp nhận HTTP POST, chứng minh traffic từ internet đã đi xuyên qua Cloudflare Tunnel vào tận code Python của Hermes).
