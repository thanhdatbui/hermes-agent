# Gateway Migration to D:\Taadaa\Hermes & Desktop/Startup Launcher Standardization (2026-11-03)

## Bối cảnh & Nguyên nhân sự cố
Khi toàn bộ codebase và môi trường venv của Hermes được chuyển dịch về `D:\Taadaa\Hermes\.venv`, thư mục `%LOCALAPPDATA%\hermes\hermes-agent` cũ bị retire/xóa. Sự cố phát sinh theo 2 nhịp:
1. **SSL CA Bundle Trap (`SSL_CERT_FILE` & `ssl_guard.py`):**
   Process Gateway cũ (khởi động trước lúc đổi script) vẫn giữ biến môi trường `SSL_CERT_FILE` trỏ tới `.../hermes-agent/venv/.../cacert.pem`. Khi thư mục cũ biến mất, `ssl_guard.py` chặn đứng toàn bộ việc khởi tạo client OpenAI/httpx, văng lỗi `SSLConfigurationError` và gây rớt mọi tin nhắn phản hồi Telegram.
2. **Hardcoded Launcher Skew trên Desktop & Startup:**
   Mặc dù service Gateway chính (`gateway-service\Hermes_Gateway.vbs`) đã được cập nhật trỏ sang `D:\Taadaa\Hermes\.venv`, các file shortcut, fallback watchdog và startup scripts khác vẫn âm thầm giữ đường dẫn cũ:
   - `C:\Users\Kibe\Desktop\BAT_Hermes_Gateway.vbs`
   - `C:\Users\Kibe\Desktop\Bat Gan Proxy Watcher.cmd`
   - `Startup\start_tiktok_dashboard.vbs`
   - `D:\Taadaa\tools\start_tiktok_dashboard_hidden.vbs`
   Nếu người dùng hoặc automation chạy lại các file này, hệ thống sẽ rơi vào tình trạng chết process hoặc cố nạp venv không còn tồn tại.

## Checklist Chuẩn hoá khi Di chuyển Gateway sang Venv Mới
Khi thực hiện migrate Hermes Gateway sang venv mới (đặc biệt là đổi ổ C: sang D:):
1. **Kiểm tra và dọn dẹp các Shortcut & Startup Script:**
   - Quét Desktop (`C:\Users\<user>\Desktop\*.vbs`, `*.cmd`, `*.bat`).
   - Quét Startup (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.vbs`).
   - Quét các công cụ khởi động ẩn tại `D:\Taadaa\tools\`.
   - Đảm bảo `BAT_Hermes_Gateway.vbs` gọi qua service chuẩn `%LOCALAPPDATA%\hermes\gateway-service\Hermes_Gateway.vbs` hoặc trỏ trực tiếp vào `D:\Taadaa\Hermes\.venv\Scripts\pythonw.exe`.
2. **Kiểm tra môi trường Process sống của Gateway:**
   - Sau khi restart Gateway, kiểm tra process sống bằng psutil: xác nhận `VIRTUAL_ENV` và `SSL_CERT_FILE` trỏ đúng vào file `cacert.pem` thực tế đang tồn tại ở venv mới (`D:\Taadaa\Hermes\.venv\Lib\site-packages\certifi\cacert.pem`).
3. **Audit Scheduler / Cron Jobs:**
   - Đọc `jobs.json` và kiểm tra toàn bộ 100% active cron jobs không còn tham chiếu tới binary python của venv cũ.
