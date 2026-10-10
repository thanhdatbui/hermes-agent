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
- **BẪY CHẨN ĐOÁN LẦM LẪN (FALSE SENTINEL/TURNSTILE ERROR):**
  * Trong `chatgpt-web.ts`, OmniRoute bắt mọi lỗi `HTTP 401` hoặc `403` trên `/backend-api/sentinel/chat-requirements/prepare` rồi tự động ném ra chuỗi: `ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
  * **Bản chất thực tế:** Hầu hết các lỗi `HTTP 401` này KHÔNG PHẢI do Cloudflare Turnstile, mà do OpenAI trả về `{"error": {"code": "token_revoked", "message": "Encountered invalidated oauth token for user"}}` vì tài khoản đã bị OpenAI khóa/vô hiệu hóa vĩnh viễn (`account_deactivated`).
  * **Cách chẩn đoán chính xác:** Giải mã cookie từ SQLite (`api_key` với secret `STORAGE_ENCRYPTION_KEY`), gọi `/api/auth/session` lấy `accessToken`, rồi gọi trực tiếp `POST /backend-api/sentinel/chat-requirements/prepare` với `{"p": ""}`:
    - Nếu `HTTP 200`: Tài khoản **LIVE 100%**.
    - Nếu `token_revoked`: Tài khoản đã **BỊ BAN / VÔ HIỆU HÓA**. Áp dụng ngay luật **"ban xóa DB giữ GPM"**: Xóa bản ghi trong `provider_connections` và xóa khỏi `models` của combo (`gpt-web-sol`, `chatgpt-web-pool`, `gpt-web-luna`). Giữ nguyên profile GPM.
    - Nếu `token_expired` hoặc hết hạn session: Tài khoản còn sống, chỉ cần re-login.

- **BẪY CẦU DAO TREO CẢ HỆ THỐNG (30-MIN CIRCUIT BREAKER TRAP):**
  * Nếu để các tài khoản bị ban/revoked trong combo Round-Robin, hệ thống sẽ gọi trúng 5 tài khoản lỗi liên tiếp và kích hoạt cầu dao tự ngắt: `Circuit breaker tripped for chatgpt-web: 5 consecutive failures. Blocked for 30min.`
  * Cầu dao này nằm trong RAM của OmniRoute (`_circuitBreaker["chatgpt-web"]`), sẽ phong tỏa toàn bộ 100% tài khoản (kể cả các tài khoản LIVE), khiến mọi lệnh gọi Advisor (`consult_advisor.py`) bị timeout >45s.
  * **Quy trình phục hồi khẩn cấp:**
    1. Lọc và lấy danh sách các connection ID thực sự LIVE (HTTP 200 trên `/prepare`).
    2. Cập nhật SQLite: Chỉ đặt `is_active = 1` cho các ID live; xóa bỏ các ID bị ban; cập nhật lại JSON `models` của các combo `gpt-web-sol`, `chatgpt-web-pool`, `gpt-web-luna` chỉ chứa các ID live.
    3. Buộc restart tiến trình OmniRoute (qua `Stop-Process` PowerShell, watchdog `omniroute_watchdog.ps1` sẽ tự khởi động lại sau ~20s) để xóa sạch biến circuit breaker trong RAM.
    4. Kiểm chứng lại bằng: `python D:/Taadaa/tools/consult_advisor.py "test ping"`.

- **CANARY & GATE 6 KHI RE-LOGIN QUA GPM:**
  * Luôn chạy Canary trên 1 tài khoản trước khi chạy hàng loạt.
  * CHECKPOINT 1 (Pre-submit): Điền email xong, chụp ảnh kiểm tra bằng WinRT OCR/vision.
  * CHECKPOINT 2 (Post-submit): Submit xong chụp ảnh ngay. Nếu gặp thông báo *"Chúng tôi đã gặp sự cố khi đăng nhập cho bạn, vui lòng tạm dừng một lát và thử lại sau"* (OpenAI rate-limit IP proxy), DỪNG NGAY LẬP TỨC. Tuyệt đối không cố chạy vòng lặp mù làm cháy proxy/tài khoản.

- **KỶ LUẬT CÁCH LY PROXY FARM & ĐỒNG BỘ DUAL-FARM (KIBE + ADMIN):**
  * Dải IP Mikrotik PPPoE (`10001-10040`) là IP nội bộ của dàn farm thiết bị, dùng cố định cho các tài khoản TikTok/Hotmail của dàn máy đó, tuyệt đối không được tùy tiện dùng ké để đăng nhập lan man.
  * Mọi quy trình vòng đời GPM/Hotmail (`batch_gpm_5profiles_supervisor.py`) BẮT BUỘC hỗ trợ cả 2 Farm: Kibe (`D:\OneDrive\TaadaaData\kibe`) và Admin (`D:\OneDrive\TaadaaData\admin`).
  * Master Excel Kibe có 12 cột (`PASS CHATGPT`), còn Admin chỉ có 10-11 cột; code đọc Excel bắt buộc dùng boundary check safe `idx < len(row)` tránh `IndexError`.
  * Lập lịch cron supervisor cho 2 cluster lệch phút (Kibe `0,5,10...`, Admin `2,7,12...`) để tránh nghẽn GPM concurrency. Báo cáo 6h phải gộp số liệu cả 2 Farm.

### Bước 5: Đóng Profile sau khi hoàn tất
Gọi API dừng profile để tránh rò rỉ tiến trình Chromium:
`GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`
