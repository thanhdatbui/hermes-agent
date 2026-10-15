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
   - **BẪY CHỌN NÚT "TIẾP TỤC" (TRÁNH BẤM NHẦM OAUTH GOOGLE):**
     * Trên `chatgpt.com/auth/login`, các nút mạng xã hội gồm: *"Tiếp tục với Google"*, *"Tiếp tục với Apple"*, *"Tiếp tục với số điện thoại"*, và nút submit email chính là *"Tiếp tục"*.
     * **CẤM DÙNG:** `b.innerText.includes('Tiếp tục')` vì nó sẽ match ngay nút đầu tiên là *"Tiếp tục với Google"*, đẩy trình duyệt sang Google Sign-in và nhập nhầm OTP vào ô email Google!
     * **BẮT BUỘC DÙNG EXACT MATCH:**
       ```javascript
       const buttons = Array.from(document.querySelectorAll('button'));
       const contBtn = buttons.find(b => {
           const t = (b.innerText || '').trim();
           return (t === 'Tiếp tục' || t === 'Continue' || b.type === 'submit') &&
                  !t.includes('Google') && !t.includes('Apple') && !t.includes('thoại') && !t.includes('phone');
       });
       if (contBtn) contBtn.click();
       ```
   - **KỶ LUẬT ĐỐI SOÁT ẢNH THẬT BẰNG OCR / VISION TRƯỚC KHI BÁO CÁO (CHỐNG GỬI ẢNH MÙ):**
     * Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào, BẮT BUỘC gọi `browser_vision` hoặc WinRT OCR mở ảnh ra soi mắt kiểm tra từng dòng chữ.
     * TUYỆT ĐỐI CẤM tự suy diễn nội dung từ turn trước để khẳng định đã thấy trang lỗi `account_deactivated` khi ảnh thực tế vẫn đang kẹt ở màn hình Google Sign-in hoặc OTP chưa submit.
   - **DỌN SẠCH CẢ OMNIROUTE (:20129) VÀ 9ROUTER (:20128):**
     * Khi tài khoản dính lỗi `account_deactivated` / xóa vĩnh viễn, BẮT BUỘC phải dọn sạch ở cả hai proxy:
       - OmniRoute (:20129): Gọi `DELETE /api/providers/{id}`, xóa trong bảng `provider_connections` và mảng `models` của các combos trong `~/.omniroute/storage.sqlite`, gọi `PUT /api/combos/{id}` sync in-memory.
       - 9Router (:20128): Gọi `DELETE /api/providers/{id}` trên `:20128/api/providers` nếu connection tồn tại.
   - Gọi `computer_use(action='click', element=<index_card_tai_khoan>, delivery_mode='background', capture_after=true)`.
   - Chờ 3-5 giây và capture lại fresh state để phân loại phản hồi tiếp theo:
     * **Tình huống 1 - Yêu cầu mã OTP qua Email (`auth.openai.com/email-verification`):** 
       - OpenAI hết hạn phiên và gửi mã 6 số về hòm thư.
       - **TỰ ĐỘNG BÓC OTP (CẤM ĐẨY VIỆC CHO USER):**
         + Với Hotmail: Tìm dòng tài khoản trong `D:/Taadaa/Hotmail/` (e.g. `latest_bought_70.txt`, `hotmail_all_60_bought.txt`), lấy `refresh_token` và `client_id`. Gọi Microsoft Graph API (`https://login.microsoftonline.com/common/oauth2/v2.0/token` scope `https://graph.microsoft.com/Mail.Read offline_access` -> `https://graph.microsoft.com/v1.0/me/messages`), bóc mã OTP 6 số mới nhất từ thư "Mã đăng nhập ChatGPT tạm thời của bạn".
         + Điền OTP tự động vào ô "Mã" bằng `computer_use(action='type', text=otp, delivery_mode='foreground')` rồi click nút "Tiếp tục" (`computer_use(action='click', element=..., delivery_mode='foreground')`).
         + **KẾT QUẢ XÁC MINH DIE THẬT (INVARIANT: BANNED LÀ BAN THẬT):**
           - **Dấu hiệu 1 (Forced Logout / Cookie Wipe khi mở GPM):** Mở `https://chatgpt.com`, URL tự động bị đẩy về `https://chatgpt.com/auth/logout`, `https://chatgpt.com/unauth-mweb/conversation?lightweight_authenticated=1` (modal "Đăng nhập hoặc đăng ký"), hoặc landing page khách vãng lai ("Log in" / "Sign up for free"). Toàn bộ session cookie cũ đã bị vô hiệu hóa từ server OpenAI.
           - **Dấu hiệu 2 (Lỗi account_deactivated sau khi nhập OTP):** Nếu sau khi nhập OTP, OpenAI ném trang `Lỗi xác thực - OpenAI` với thông báo: *"Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"* kèm `error_code: account_deactivated` (đồng thời kiểm tra hòm thư có mail từ `trustandsafety@tm.openai.com` báo *"Truy cập bị vô hiệu hóa"*): Đây là **DIE THẬT Ở PHÍA SERVER OPENAI**. Banned không phải do OmniRoute dán nhãn bậy. CẤM cố gắng đăng nhập lại; áp dụng ngay quy tắc xóa connection khỏi DB proxy, xóa khỏi combo và bảo toàn GPM profile gốc.
           - **Kỹ thuật chụp ảnh đối soát nhanh qua CDP (không phụ thuộc pywin32):** Khi cần chụp ảnh GPM gửi User qua `MEDIA:`, tạo tab qua `PUT http://{remote_debugging_address}/json/new?https://chatgpt.com`, kết nối WebSocket tới `webSocketDebuggerUrl`, gửi lệnh CDP `Page.captureScreenshot` lưu ảnh vào `D:/Taadaa/runtime/artifacts/`, rồi dùng `browser_vision` soi mắt trước khi gửi thẻ `MEDIA:`.
       - Chỉ hỏi User khi tài khoản không có refresh token / không bóc được OTP qua API.
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

- **BẪY RE-LOGIN TRÊN GPM & CDP AUTOMATION (THỰC NGHIỆM CHI TIẾT):**
  * **Landing Modal Trap vs Auth Login:** Khi mở `https://chatgpt.com/`, modal "Đăng nhập hoặc đăng ký" chỉ là guest onboarding vãng lai (`unauth-mweb`). Nút "Tiếp tục" trong modal này không gửi form xác thực OpenAI. Để đăng nhập thật vào OpenAI, BẮT BUỘC điều hướng thẳng đến `https://chatgpt.com/auth/login` để vào cổng xác thực chính thức `auth.openai.com`.
  * **React DOM Input Value Trap:** Giao diện Next.js/React của ChatGPT bỏ qua thao tác gán `input.value = ...` thông thường. Muốn điền email/mật khẩu qua JS BẮT BUỘC dùng prototype setter:
    `Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(input, val)` kèm `input.dispatchEvent(new Event('input', { bubbles: true }))` và `change`, HOẶC dùng CDP `Input.dispatchKeyEvent` gõ từng ký tự.
  * **CDP WebSocket Origin 403 Trap:** Thư viện WebSocket chuẩn (như Python `websocket-client`) tự gửi header `Origin: http://127.0.0.1:<port>` sẽ bị Chromium CDP chặn `403 Forbidden (Rejected incoming WebSocket connection)`. Phải dùng raw socket kết nối trực tiếp không gửi header `Origin`.
  * **Forced Email OTP & Xác nhận Account Deactivated:**
    - OpenAI thường bỏ qua mật khẩu và ép xác minh OTP qua email (`auth.openai.com/email-verification`). Bóc OTP qua Graph API nếu là Hotmail có token.
    - Sau khi nhập OTP, nếu màn hình hiện `error_code: account_deactivated` ("Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"), tài khoản đã bị OpenAI trảm thẳng server-side, không thể khôi phục.
  * **Kỷ luật Visual Evidence:** Tuyệt đối không báo trạng thái tài khoản qua text suông. Bắt buộc chụp ảnh màn hình tại từng checkpoint, soi mắt qua vision/OCR xác nhận rõ màn hình trước khi báo cáo.

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
  * **PHÂN BIỆT RÕ CHECKPOINT FORM OTP vs ẢNH LỖI CUỐI CÙNG ("ẢNH LỖI ĐÂU?"):**
    - Màn hình dừng ở ô nhập OTP (`auth.openai.com/email-verification`) CHƯA PHẢI là ảnh lỗi. Đó chỉ là checkpoint chờ mã xác thực.
    - User đòi "Ảnh lỗi đâu?" là đòi bằng chứng xác thực việc tài khoản bị OpenAI từ chối/vô hiệu hóa.
    - BẮT BUỘC phải hoàn tất bước nhập OTP (bóc qua Graph API/Outlook) rồi submit để ghi nhận màn hình thông báo lỗi chính thức: `Lỗi xác thực - OpenAI` (`error_code: account_deactivated`, *"Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"*).
    - Chỉ gửi thẻ `MEDIA:` của màn hình báo lỗi này làm bằng chứng xác thực tài khoản bị xóa vĩnh viễn; cấm gửi ảnh form OTP rồi kết luận tài khoản die.
  * **SCOPE CHUẨN MICROSOFT GRAPH API KHI BÓC OTP HOTMAIL:**
    - Khi đổi `refresh_token` lấy `access_token` tại `https://login.microsoftonline.com/common/oauth2/v2.0/token`:
    - BẮT BUỘC dùng: `scope = "https://graph.microsoft.com/Mail.Read offline_access"` kèm header `Content-Type: application/x-www-form-urlencoded`.
    - TUYỆT ĐỐI CẤM dùng `scope = "https://graph.microsoft.com/.default offline_access"` vì Microsoft OAuth2 endpoint sẽ trả về `HTTP Error 400: Bad Request` đối với refresh token tài khoản cá nhân.
  * **ĐIỀU HƯỚNG AUTH TRỰC TIẾP & BẪY REACT INPUT VALUE:**
    - Tránh nhập email trên popup modal của `https://chatgpt.com/` (guest conversation onboarding). BẮT BUỘC navigate thẳng đến URL: `https://chatgpt.com/auth/login`.
    - Form React của ChatGPT bỏ qua việc gán `input.value = ...` trực tiếp. Phải dùng:
      `Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(input, email_val)`
      kèm dispatch event `input` và `change` (`{ bubbles: true }`), hoặc dùng CDP `Input.dispatchKeyEvent` gõ từng ký tự.
  * CHECKPOINT 1 (Pre-submit): Điền email xong, chụp ảnh kiểm tra bằng WinRT OCR/vision.
  * CHECKPOINT 2 (Post-submit): Submit xong chụp ảnh ngay. Nếu gặp thông báo *"Chúng tôi đã gặp sự cố khi đăng nhập cho bạn, vui lòng tạm dừng một lát và thử lại sau"* (OpenAI rate-limit IP proxy), DỪNG NGAY LẬP TỨC. Tuyệt đối không cố chạy vòng lặp mù làm cháy proxy/tài khoản.

- **KỶ LUẬT CÁCH LY PROXY FARM & ĐỒNG BỘ DUAL-FARM (KIBE + ADMIN):**
  * Dải IP Mikrotik PPPoE (`10001-10040`) là IP nội bộ của dàn farm thiết bị, dùng cố định cho các tài khoản TikTok/Hotmail của dàn máy đó, tuyệt đối không được tùy tiện dùng ké để đăng nhập lan man.
  * Mọi quy trình vòng đời GPM/Hotmail (`batch_gpm_5profiles_supervisor.py`) BẮT BUỘC hỗ trợ cả 2 Farm: Kibe (`D:\OneDrive\TaadaaData\kibe`) và Admin (`D:\OneDrive\TaadaaData\admin`).
  * Master Excel Kibe có 12 cột (`PASS CHATGPT`), còn Admin chỉ có 10-11 cột; code đọc Excel bắt buộc dùng boundary check safe `idx < len(row)` tránh `IndexError`.
  * Lập lịch cron supervisor cho 2 cluster lệch phút (Kibe `0,5,10...`, Admin `2,7,12...`) để tránh nghẽn GPM concurrency. Báo cáo 6h phải gộp số liệu cả 2 Farm.

### Bước 5: Đóng Profile & Dọn Dẹp Tiến Trình Mồ Côi (Chống Khóa File Cookies & Tràn RAM)
1. Gọi API dừng profile:
   `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`
2. **BẪY RÒ RỈ TIẾN TRÌNH CON GPM CHROMIUM:**
   - GPM Stop API thường xuyên để sót tiến trình `gpm_browser_chromium_core.exe` chạy ngầm. Các tiến trình này tiếp tục giữ file lock trên `Cookies` (gây lỗi `sqlite3.OperationalError: unable to open database file` cho các tiến trình kiểm tra sau) và ngốn cạn RAM hệ thống.
   - **Bắt buộc dọn dẹp bằng psutil sau mỗi profile:**
     ```python
     import psutil
     for p in psutil.process_iter(['name', 'exe']):
         name = (p.info.get('name') or '').lower()
         exe = (p.info.get('exe') or '').lower()
         if 'gpm_browser' in name or 'gpmlogin\\gpm_browser' in exe:
             try: p.kill()
             except Exception: pass
     ```
     *(Lưu ý: Chỉ kill `gpm_browser_chromium_core.exe` trong thư mục GPMLogin, tuyệt đối không chạm vào `chrome.exe` thông thường của User).*

---

## 4. Các Bẫy Kiến Trúc & Quy Tắc Nạp Pool OmniRoute Cần Nhớ

### Bẫy 1: Lưu Bare Session-Token Gây 403 Sentinel/Turnstile Block
- Khi nạp cookie vào `provider_connections.api_key` của OmniRoute, nếu **chỉ lưu duy nhất giá trị token `__Secure-next-auth.session-token`** (`eyJhbG...`), Cloudflare Sentinel sẽ phát hiện thiếu fingerprint trình duyệt và chặn lại bằng mã lỗi:
  `[403]: ChatGPT blocked the request (Sentinel/Turnstile required)`.
- **Giải pháp:** Hàm `extract_cookies` qua CDP Playwright bắt buộc phải lấy toàn bộ cookies từ `https://chatgpt.com` và `https://auth.openai.com` (đặc biệt là `cf_clearance`, `oai-did`, `oai-sc`, `__cf_bm`) và nối thành chuỗi:
  `"; ".join(f"{c['name']}={c['value']}" for c in cookies)`
  Hàm `buildSessionCookieHeader` của OmniRoute sẽ giữ nguyên chuỗi đầy đủ này khi gửi tới `backend-api/f/conversation`, giúp vượt qua kiểm tra Sentinel.

### Bẫy 2: Kỷ Luật Thực Thi Chống Nói Suông & Chuyển Giao Worker Khi Quota Chạm Ngưỡng
- **Chống nói suông:** Khi nhận nhiệm vụ rà soát hoặc nạp pool, CẤM emit câu chat text "em đang cho rà soát..." rồi dừng lại khiến task bị treo chết suốt hàng chục phút qua cữ reboot máy. Tác vụ dài BẮT BUỘC phải dispatch ngay qua `terminal(background=True, notify_on_complete=True)` hoặc subagent.
- **Kỷ luật bảo vệ Claude Quota:** Khi Claude CLI chạm ngưỡng an toàn 85% quota 5h (`CLAUDE_QUOTA_GUARD_BLOCKED`), hệ thống phải lập tức chuyển giao quyền can thiệp sang worker dự phòng **Antigravity CLI** (`python D:/Taadaa/tools/ag_cli.py fix ...` qua profile `acc_01..acc_07`, model `gemini-3.8-flash-high`), không được dừng im hay xin phép lòng vòng.

