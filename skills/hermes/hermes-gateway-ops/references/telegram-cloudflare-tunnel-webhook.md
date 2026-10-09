# Telegram Webhook qua Cloudflare Tunnel (Chống ISP Bóp Socket & Lỗi Media)

## Bối cảnh & Nguyên nhân sự cố (2026-09-24 Incident)

1. **Sự cố 1: ISP (FPT/VNPT) ngắt ngầm TCP socket (Silent Drop)**
   - Cơ chế Long-polling (`getUpdates`): Bot duy trì 1 socket HTTP kéo dài 30-60s chờ tin từ Telegram.
   - Nhà mạng âm thầm ngắt kết nối TCP nhàn rỗi mà không gửi cờ `TCP RST`.
   - Kết quả: Socket rơi vào trạng thái Half-open, Gateway tưởng kết nối còn sống nên đứng chờ timeout 5–10 phút mới reconnect -> Bot bị treo cứng 6-10 phút.

2. **Sự cố 2: Lỗi gửi/nhận ảnh khi dùng WARP Proxy (NetworkError / Host unreachable)**
   - Khi cấu hình `TELEGRAM_PROXY=socks5://127.0.0.1:40000` (Cloudflare WARP MASQUE HTTP/3 UDP):
   - Mạng ISP bóp băng thông/gói tin UDP quốc tế, làm rớt gói khi tải/gửi media dung lượng lớn -> Gây timeout và lỗi mạng.

3. **Sự cố 3: Telegram phạt Exponential Backoff (5-6 phút) do Sync Disk I/O**
   - Trong `telegram/adapter.py`, các hàm cache media (`cache_image_from_bytes()`) chạy đồng bộ (sync) thẳng trên Main Event Loop.
   - Khi ổ đĩa bận, event loop bị block 5-15s -> Webhook không trả kịp `HTTP 200` cho Telegram -> Telegram ghi nhận `Read timeout expired` và tự động phạt backoff: `1s -> 2s -> 5s -> 10s -> 30s -> 60s -> 300s (5 phút)`. Telegram giam toàn bộ tin nhắn tại server, không bắn về máy.

---

## Kiến trúc giải pháp triệt để: Telegram Webhook + Cloudflare Tunnel

Thay đổi mô hình từ **Pull** (ngâm socket chờ tin) sang **Push** (Telegram Server bắn HTTP POST thẳng về Cloudflare Edge Singapore trong <5ms, truyền qua 4 đường hầm multiplexed về local).

### 1. Chuẩn bị Cloudflare Tunnel
- Cài đặt `cloudflared` (Windows: `C:\Program Files (x86)\cloudflared\cloudflared.exe`).
- Đăng nhập và ủy quyền domain:
  ```bash
  cloudflared.exe tunnel login
  ```
- Tạo tunnel và định tuyến DNS cho subdomain:
  ```bash
  cloudflared.exe tunnel create hermes-bot
  cloudflared.exe tunnel route dns hermes-bot bot.taadaa.click
  ```
- File cấu hình `C:\Users\<User>\.cloudflared\config.yml`:
  ```yaml
  tunnel: <TUNNEL_UUID>
  credentials-file: C:\Users\<User>\.cloudflared\<TUNNEL_UUID>.json

  ingress:
    - hostname: bot.taadaa.click
      service: http://127.0.0.1:8443
    - service: http_status:404
  ```

### 2. Thiết lập khởi động cùng Windows (Startup Script)
Tạo file VBS chạy ngầm tại `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\cloudflared_tunnel.vbs`:
```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell -WindowStyle Hidden -File ""C:\Users\Kibe\.cloudflared\run_tunnel.ps1""", 0, False
```
Script `run_tunnel.ps1`:
```powershell
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --config "C:\Users\Kibe\.cloudflared\config.yml" run
```

### 3. Cấu hình biến môi trường Hermes Gateway (`~/.hermes/.env` hoặc `%LOCALAPPDATA%\hermes\.env`)
```bash
# TẮT HOÀN TOÀN TELEGRAM_PROXY để ảnh đi thẳng mạng Direct FPT siêu tốc (0.7s)
# TELEGRAM_PROXY=

# BẬT WEBHOOK QUA CLOUDFLARE TUNNEL
TELEGRAM_WEBHOOK=https://bot.taadaa.click/telegram
TELEGRAM_WEBHOOK_PORT=8443
TELEGRAM_WEBHOOK_SECRET=<random_secret_token_64_chars>
```

### 4. Khởi động lại Hermes Gateway và Kiểm tra
- Khởi động lại Gateway (chạy ngoài tiến trình Gateway):
  ```bash
  hermes gateway restart
  ```
- Kiểm tra trạng thái Webhook trực tiếp từ máy chủ Telegram:
  ```python
  import urllib.request, json
  token = "<TELEGRAM_BOT_TOKEN>"
  url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
  with urllib.request.urlopen(url) as r:
      print(json.dumps(json.loads(r.read().decode()), indent=2))
  ```
  Kỳ vọng:
  ```json
  {
    "ok": true,
    "result": {
      "url": "https://bot.taadaa.click/telegram",
      "has_custom_certificate": false,
      "pending_update_count": 0,
      "max_connections": 40
    }
  }
  ```

---

## Các cạm bẫy cần lưu ý (Pitfalls)
1. **Tuyệt đối không chạy Sync Disk I/O trong Webhook Handler**: Mọi thao tác ghi file/cache ảnh trong handler bắt buộc phải wrap `await loop.run_in_executor(None, fn, *args)` để không block event loop.
2. **Không để ổ đĩa đầy (Disk Full)**: Nếu ổ C cạn kiệt, mọi lệnh commit SQLite của webhook handler sẽ bị đóng băng ở mức OS Kernel.
3. **Bỏ qua port mapping**: Cloudflare Tunnel trỏ về `http://127.0.0.1:8443`, port này phải khớp chính xác với `TELEGRAM_WEBHOOK_PORT` trong `.env`.
