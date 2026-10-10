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

### Bước 4: Chủ động thao tác Click qua Background Computer Use (Chống đẩy việc cho User)
1. Chụp ảnh cửa sổ và quét SOM tree bằng `computer_use(action='capture', mode='som', pid=..., window_id=...)`.
2. Chạy WinRT OCR (`skills/productivity/windows-native-ocr/scripts/winrt_ocr.py`) xác nhận đúng email và modal "Chào mừng trở lại".
3. **KỶ LUẬT CHỦ ĐỘNG (PROACTIVE ASSISTANCE):** Tuyệt đối KHÔNG dừng lại chỉ để bảo User tự bấm khi các button hoàn toàn click được qua automation.
   - Gọi `computer_use(action='click', element=<index_card_tai_khoan>, delivery_mode='background', capture_after=true)`.
   - Chờ 3-5 giây và capture lại fresh state để phân loại phản hồi tiếp theo:
     * **Tình huống 1 - Yêu cầu mã OTP qua Email (`auth.openai.com/email-verification`):** 
       - OpenAI hết hạn phiên và gửi mã 6 số về hòm thư.
       - **TỰ ĐỘNG BÓC OTP (CẤM ĐẨY VIỆC CHO USER):**
         + Với Hotmail: Tìm dòng tài khoản trong `D:/Taadaa/Hotmail/` (e.g. `hotmail_all_60_bought.txt`), lấy `refresh_token` và `client_id`. Gọi Microsoft Graph API (`https://login.microsoftonline.com/common/oauth2/v2.0/token` scope `https://graph.microsoft.com/Mail.Read offline_access` -> `https://graph.microsoft.com/v1.0/me/messages`), bóc mã OTP 6 số mới nhất từ thư "Mã đăng nhập ChatGPT tạm thời của bạn".
         + Điền OTP tự động vào ô "Mã" bằng `computer_use(action='type', text=otp)` rồi click nút "Tiếp tục" (`computer_use(action='click', element=...)`).
         + Chỉ hỏi User khi tài khoản không có refresh token / không bóc được OTP qua API.
     * **Tình huống 2 - Cloudflare Turnstile Checkbox:** Thử click vào checkbox Turnstile. Nếu bị kẹt hoặc dính puzzle hình ảnh thì mới bàn giao màn hình cho User kèm ảnh chụp thực tế.
     * **Tình huống 3 - Đăng nhập thành công:** Đóng profile an toàn và chuyển tiếp tài khoản tiếp theo.

### Lưu ý quan trọng khi chọn tài khoản:
- Phải kiểm tra trạng thái `is_active = 0` và `last_error` trong `C:\Users\Kibe\.omniroute\storage.sqlite` để chọn đúng profile đang thực sự cần gỡ cờ.
- Kiểm tra hòm thư loại trừ các tài khoản đã nhận mail "OpenAI - Truy cập bị vô hiệu hóa" (tài khoản đã bị OpenAI khóa vĩnh viễn, không cố login lại).

### Bước 5: Đóng Profile sau khi hoàn tất
Gọi API dừng profile để tránh rò rỉ tiến trình Chromium:
`GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`
