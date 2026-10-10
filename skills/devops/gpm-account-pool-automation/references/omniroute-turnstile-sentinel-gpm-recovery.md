# OmniRoute ChatGPT-Web Turnstile / Sentinel Block & GPM Manual Recovery Runbook

## 1. Dấu hiệu & Bằng chứng phát hiện (Diagnostic Signatures)

### Triệu chứng
1. **Advisor / Health Check Timeout:**
   - Script gọi model qua OmniRoute (như `consult_advisor.py` trên `:20129`) bị timeout > 45s: `ADVISOR_UNAVAILABLE: TIMEOUT :: >45s`.
2. **Log OmniRoute stdout (`AppData/Roaming/omniroute/logs/omniroute-stdout.log`):**
   ```text
   [ERROR] [403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.
   {"level":50,"service":"omniroute","tag":"TOKEN_REFRESH","msg":"🔴 Circuit breaker tripped for chatgpt-web: 5 consecutive failures. Blocked for 30min. Provider needs re-authentication."}
   {"level":40,"service":"omniroute","tag":"TOKEN_REFRESH","msg":"⚡ Circuit breaker active for chatgpt-web, skipping refresh"}
   ```
3. **Cơ chế Circuit Breaker:**
   - Khi có >= 5 tài khoản liên tiếp bị Cloudflare / OpenAI trả về HTTP 403 do yêu cầu Turnstile / Sentinel, OmniRoute tự động kích hoạt Circuit Breaker khóa toàn bộ pool `chatgpt-web` trong 30 phút.

---

## 2. Vị trí CSDL Runtime của OmniRoute (SSOT)

- **Đường dẫn CSDL thực tế đang chạy:**
  `C:\Users\Kibe\.omniroute\storage.sqlite` (kèm các file `-wal`, `-shm`).
  *(Lưu ý: Các file trong `C:\Users\Kibe\OmniRoute\storage.sqlite` hay `AppData\Roaming\omniroute\storage.sqlite` là file backup hoặc schema rỗng, không truy vấn nhầm).*
- **Bảng theo dõi:** `provider_connections`
  - Điều kiện lọc tài khoản dính lỗi:
    ```sql
    SELECT id, name, last_error, last_error_at 
    FROM provider_connections 
    WHERE provider = 'chatgpt-web' 
      AND last_error LIKE '%Sentinel/Turnstile required%'
    ORDER BY last_error_at DESC;
    ```

---

## 3. Quy trình mở Profile GPM vượt Captcha / Turnstile (Recovery Flow)

### Bước 1: Trích xuất danh sách Email dính lỗi từ OmniRoute SQLite
Chạy script query bảng `provider_connections` trong `C:\Users\Kibe\.omniroute\storage.sqlite` để lấy danh sách email mới nhất bị dính 403.

### Bước 2: Đối soát với GPM Local API (Port 19995)
1. Gọi endpoint phân trang:
   `GET http://127.0.0.1:19995/api/v3/profiles?page={N}&per_page=100`
2. Lọc matching `profile_id` dựa trên email trong tên profile (ví dụ: `01 - gilliara2011@hotmail.com - 5101`).

### Bước 3: Khởi động Profile GPM & Mở ChatGPT
1. Khởi động profile:
   `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
   Lấy `remote_debugging_address` (ví dụ `127.0.0.1:50554`) và `process_id`.
2. Tạo tab mở ChatGPT qua CDP HTTP:
   `PUT http://{remote_debugging_address}/json/new?https://chatgpt.com`
3. Đưa cửa sổ lên màn hình desktop bằng Win32 GUI (`win32gui.ShowWindow(hwnd, win32con.SW_SHOW)`).

### Bước 4: Kiểm chứng bằng chứng trước khi báo User (GATE 6 & WinRT OCR)
1. Chụp ảnh cửa sổ bằng `PrintWindow` hoặc `computer_use`.
2. Chạy WinRT OCR (`skills/productivity/windows-native-ocr/scripts/winrt_ocr.py`) xác nhận:
   - Đúng màn hình ChatGPT / Modal "Chào mừng trở lại".
   - Hiển thị đúng email cần xử lý.
   - Ảnh không bị màn hình đen / popup crash che khuất.
3. Gửi thông báo kèm `MEDIA:<path_anh>` để User thao tác click vượt Turnstile trên màn hình.

### Bước 5: Đóng Profile sau khi hoàn tất
Gọi API dừng profile để tránh rò rỉ tiến trình Chromium:
`GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`
