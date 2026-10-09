# Telegram Gateway Media Download & Proxy Failover Quirks

## Hiện tượng (Symptom)
- Khi user gửi file đính kèm hoặc ảnh qua Telegram, bot liên tục trả về:
  `⚠️ Couldn't download your attachment (<filename>) (NetworkError). Please try sending it again.`
  hoặc
  `⚠️ Couldn't download your photo (NetworkError). Please try sending it again.`
- Trong log hoặc stdio xuất hiện:
  `httpcore.ProxyError: Proxy Server could not connect: Host unreachable.`

## Nguyên nhân gốc rễ (Root Cause)
1. Trong file `.env`, `TELEGRAM_PROXY` được cấu hình trỏ tới SOCKS5 local (ví dụ `socks5://127.0.0.1:40000`).
2. Nếu cổng proxy đó là HTTP CONNECT proxy (như Cloudflare WARP proxy mode) hoặc proxy local bị crash/chập chờn, httpx không thể thiết lập kết nối SOCKS5 tới Telegram CDN để tải bytes media (`download_as_bytearray()`).
3. Mặc dù tin nhắn text vẫn đi qua cơ chế failover (Multi-ISP fallback) của Hermes, luồng tải binary file/ảnh bị bắt lỗi và kích hoạt `_surface_media_cache_failure()`.

## Cách khắc phục chuẩn
1. Kiểm tra kết nối Telegram trực tiếp từ máy host:
   `curl -I -s --max-time 5 https://api.telegram.org`
2. Nếu mạng bình thường (không bị chặn ở ISP hiện tại):
   - Comment out `TELEGRAM_PROXY` trong `.env` (`# TELEGRAM_PROXY=...`).
3. Khởi động lại Gateway từ bên trong session Hermes:
   - CẤM chạy trực tiếp `hermes gateway restart` trong terminal của session (sẽ bị block vì SIGTERM giết luôn lệnh).
   - Kích hoạt qua kịch bản Detached Delayed Restart:
     `powershell -WindowStyle Hidden -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Kibe\AppData\Local\hermes\scripts\delayed-restart.ps1\"' -WindowStyle Hidden"`
