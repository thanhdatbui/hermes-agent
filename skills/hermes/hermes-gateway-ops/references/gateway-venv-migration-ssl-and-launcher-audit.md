# Gateway Venv Migration SSL & Stale Launcher Pitfall (2026-11-03)

## Bối cảnh & Hiện tượng
Khi di dời hoặc chuẩn hóa codebase Hermes sang venv mới (ví dụ từ `%LOCALAPPDATA%\hermes\hermes-agent\venv` sang `D:\Taadaa\Hermes\.venv`):
- `Hermes_Gateway.vbs` trong service đã được sửa sang venv mới, nhưng process cũ vẫn chạy giữ biến môi trường `SSL_CERT_FILE` trỏ vào venv cũ.
- Khi venv cũ bị đổi tên hoặc xóa (ví dụ `hermes-agent.retired_backup`), `cacert.pem` biến mất.
- `ssl_guard.py` lập tức kích hoạt lỗi:
  `SSL_CERT_FILE points to a missing CA bundle: ...\hermes-agent\venv\Lib\site-packages\certifi\cacert.pem`
- Toàn bộ các session Telegram bị phản hồi "Sorry, I encountered an unexpected error" do không thể khởi tạo OpenAI client.

## Quy trình Kiểm tra & Đối soát Toàn diện
1. **Kiểm tra process Gateway đang chạy và biến môi trường:**
   - Dùng script inspect qua `psutil` để đọc `environ` của PID gateway (`pythonw.exe` / `python.exe`).
   - Kiểm tra `SSL_CERT_FILE`, `VIRTUAL_ENV`, và `PYTHONPATH`.
2. **Kiểm tra file chứng chỉ CA thực tế:**
   - Kiểm tra `os.path.exists(SSL_CERT_FILE)` và kích thước file.
3. **Quét sạch các shortcut / launcher phụ trợ còn lưu đường dẫn venv cũ:**
   - `C:\Users\<User>\Desktop\BAT_Hermes_Gateway.vbs`
   - `C:\Users\<User>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\*.vbs`
   - Bắt buộc cập nhật đồng bộ sang launcher chuẩn hoặc gọi `Hermes_Gateway.vbs` của service để tránh việc click thủ công làm sống lại runtime lỗi cũ.
