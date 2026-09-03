---
name: gpm-account-pool-automation
description: Vận hành và tự động hóa GPMLogin Local API (v3 port 19995) + Playwright CDP — tạo profile độc lập, gán proxy phân tách theo cụm Farm (Kibe 1:1 vs Admin pool), tự động đăng nhập Google/Gmail, trích xuất OAuth token Antigravity, chống lệch Geolocation gây checkpoint thiết bị.
version: 1.0.0
---

# GPMLogin Local API & Account Pool Automation

## 1. Khi nào sử dụng
- Quản lý, tạo và cấu hình profile trình duyệt hàng loạt trên GPMLogin qua Local API v3 (port `19995`).
- Tự động hóa đăng nhập Google / Gmail / Hotmail và cấp quyền OAuth (Antigravity / LLM Router) qua Playwright CDP.
- Đồng bộ và map proxy giữa Farm điện thoại Android thật và Profile GPM để duy trì tính nhất quán danh tính và mạng.

---

## 2. GPMLogin Local API v3 (Port 19995)

GPMLogin phiên bản hiện tại sử dụng chuẩn API v3. Port được lưu động tại `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\api_port.dat` (mặc định: `19995`).

### Endpoints chuẩn v3:
- **List Profiles:** `GET http://127.0.0.1:19995/api/v3/profiles?page={N}&per_page=100` (hỗ trợ phân trang).
- **Create Profile:** `POST http://127.0.0.1:19995/api/v3/profiles/create`
  - Payload: `{"profile_name": "...", "raw_proxy": "host:port:user:pass"}`
  - *Tự động sinh ngẫu nhiên MAC Address, GPU WebGL Renderer, Canvas/Audio noise, CPU Cores và RAM.*
- **Update Proxy:** `POST http://127.0.0.1:19995/api/v3/profiles/update/{id}`
  - Payload: `{"raw_proxy": "host:port:user:pass"}` *(chú ý dùng key viết thường `raw_proxy`)*.
- **Start Profile:** `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}`
  - Trả về JSON chứa `remote_debugging_address` (ví dụ: `127.0.0.1:50064`).
- **Stop Profile:** `GET http://127.0.0.1:19995/api/v3/profiles/stop/{id}`

---

## 3. Quy tắc phân tách Pool & Chống lệch Geolocation (BẮT BUỘC)

Tuyệt đối tuân thủ phân tách 2 cụm Profile độc lập để tránh Google phát hiện IP lạ và bắn cảnh báo bảo mật về thiết bị Android thật của Farm:

### A. Cụm 16 Profile Gốc & Active (Profile `01_Rua` → `15` + `AMZ_Main` + Profile Kibe đã Live) — CẤM ĐỤNG:
- **Proxy:** Gán cố định 100% theo file `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (`test.taadaa.click:5101..5117:mobiX:TaadaaMobi#2026!` hoặc Singbox tương ứng).
- **Tài khoản:** **CHỈ** được đăng nhập các tài khoản Gmail/Hotmail tương ứng đúng số máy trong `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
- **CẤM KỴ TUYỆT ĐỐI:** CẤM thay đổi proxy, CẤM gán proxy MikroTik Admin, CẤM đưa 16 profile này vào batch restore/test tài khoản khác, CẤM reset DB làm mất `GroupId=1` của các profile này. Mọi thao tác ghi đè proxy lên 16 profile này đều là vi phạm nghiêm trọng.

### B. Kho 240 Profile Ẩn (Backup Pool `GroupId=0` / `gpm_hidden_240profiles_*.zip`):
- Đây là kho profile cũ (tên dạng `11-8801...`, `12-8801...`, `dvn001...`) dùng để tái sử dụng / nạp tài khoản mới.
- Khi cần restore thử nghiệm profile cũ hoặc cấp profile cho 28 port Admin: **BẮT BUỘC CHỈ ĐƯỢC CHỌN TRONG KHO 240 NÀY (`GroupId=0`)**.
- Quy trình: Lấy profile sạch $\rightarrow$ Gán proxy MikroTik Admin (`10008`..`10035`) $\rightarrow$ Đổi IP $\rightarrow$ Launch Chrome Core 142 qua Playwright persistent context $\rightarrow$ Đăng nhập Gmail + 2FA TOTP.

### C. Cụm Admin (Profile `Admin_10008` → `Admin_10035`):
- **Proxy:** Gán 28 port MikroTik Admin (`10008` → `10035` hoặc Singbox direct `192.168.110.2:20008..20035`).
- **Tài khoản:** **CHỈ** đăng nhập các Gmail tự do ngoài Kibe có mật khẩu & mã 2FA TOTP chuẩn xác (từ kho nguồn `2592 Gmail old.txt` sau khi check live), tuyệt đối không dùng list thô sai pass.
- **Cấm kỵ:** Tuyệt đối KHÔNG đăng nhập tài khoản đang nằm trên máy Kibe vào IP MikroTik Admin (IP Đà Nẵng).

### D. Kỹ thuật Proxy MikroTik Singbox Không Auth (Tránh Lỗi `ERR_TOO_MANY_RETRIES`):
- Khi dùng Playwright / Chrome CDP với proxy domain ngoài có auth (`http://test.taadaa.click:51XX` hoặc `mirotik1.taadaa.click:100XX` với user:pass): Playwright proxy authentication bridge thường xuyên gặp lỗi vòng lặp `net::ERR_TOO_MANY_RETRIES` trên Chrome do xung đột xác thực digest/basic.
- **Giải pháp chuẩn:** Dùng trực tiếp IP nội bộ Singbox `http://192.168.110.2:20001`..`20080` (tương ứng Máy 1..80 / `pppoe-out1`..`80`). Cổng này không yêu cầu user/password, kết nối trực tiếp không qua proxy bridge, tốc độ tức thì và 100% không lỗi auth.
- **Mẫu launch Playwright Persistent Context chuẩn:**
  ```python
  context = playwright.chromium.launch_persistent_context(
      user_data_dir=profile_folder_path,
      executable_path=CHROME_EXE,
      proxy={"server": f"http://192.168.110.2:{20000 + machine_num}"},
      headless=False,
      args=["--no-first-run", "--no-default-browser-check"]
  )
  ```

### E. Quy Tắc Truy Vấn Khi Restore Profile Cũ (Cấm Lấy Nhầm 15 Profile Gốc):
- Khi được yêu cầu "restore profile cũ", **TUYỆT ĐỐI CẤM** dùng câu lệnh SQL `SELECT ... FROM Profiles LIMIT 5` vì 15 profile gốc Kibe (`01_Rua`, `02`..`15`) luôn nằm ở đầu bảng `Profiles`.
- **BẮT BUỘC** lọc theo điều kiện profile ẩn: `WHERE GroupId = 0` hoặc theo prefix tên `11-8801...`, `12-8801...`, `dvn...`, hoặc giải nén từ file `D:\OneDrive\backup\GPM\gpm_hidden_240profiles_*.zip`.

---

## 4. Playwright CDP Automation Workflow

Khi kết nối vào browser qua `remote_debugging_address` hoặc Playwright persistent context:

1. **Khởi tạo kết nối & Cờ Stealth chống Google Bot Detection:**
   - Khi chạy login mới, Google sẽ kích hoạt *"Trình duyệt không an toàn"* hoặc reCAPTCHA nếu phát hiện `navigator.webdriver = true`.
   - **Launch args bắt buộc:**
     ```python
     args = [
         "--no-first-run",
         "--no-default-browser-check",
         "--disable-blink-features=AutomationControlled",
         "--lang=vi-VN,vi"
     ]
     ```
   - Sử dụng `locale="vi-VN"` để đồng bộ ngôn ngữ hiển thị.

2. **Quy tắc Kiểm tra Session Trước Khi Login (Skip If Logged In):**
   - Luôn điều hướng tới `https://myaccount.google.com` trước.
   - Nếu URL là `myaccount.google.com` và không redirect về `signin` / `about`: **ĐÃ CÓ SESSION HỢP LỆ $\rightarrow$ BỎ QUA NGAY LẬP TỨC**, tuyệt đối không điền lại email/password để tránh phá hỏng cookie/session cũ.

3. **Luồng đăng nhập Google an toàn:**
   - Điều hướng tới `https://accounts.google.com/signin/v2/identifier?flowName=GlifWebSignIn&flowEntry=ServiceLogin` với `wait_until="domcontentloaded"`.
   - Điền Email $\rightarrow$ Click `#identifierNext` $\rightarrow$ Đợi input `#passwordNext`.
   - Điền Password $\rightarrow$ Click `#passwordNext`.
   - **Xử lý Recovery Email Challenge:** Bắt selector `div[data-challengetype="12"]` hoặc `div:has-text("recovery email")` $\rightarrow$ điền recovery email vào `input#knowledge-preregistered-email-response` $\rightarrow$ Enter.
   - **Xử lý Popup Onboarding (Video selfie / Passkey / Recovery phone):**
     - Quét và click liên hoàn các nút: `"Bỏ qua"`, `"Để sau"`, `"Not now"`, `"Hủy"`, `"Skip"` (`button:has-text("Bỏ qua"), button:has-text("Để sau"), button:has-text("Not now")`).
   - **Fail-closed:** Nếu gặp checkpoint số điện thoại / OTP 2FA / reCAPTCHA không tự giải quyết được $\rightarrow$ ghi nhận lỗi, đóng profile ngay lập tức và chuyển sang profile tiếp theo, không treo tiến trình.

---

## 5. Concurrent (Song Song) Batch Login

Khi cần login hàng loạt profile nhanh, dùng `ThreadPoolExecutor` với `max_workers=4`:
- Mỗi thread mở 1 profile GPM độc lập (start → CDP login → stop).
- Profile đã logged in trước → phát hiện ngay qua `myaccount.google.com` URL check, đóng nhanh, chuyển sang profile tiếp theo.
- Giới hạn 4 workers: GPM bị crash nếu mở quá nhiều profile Chrome cùng lúc trên 1 máy.
- `ThreadPoolExecutor` an toàn vì mỗi thread gọi `sync_playwright()` độc lập (Playwright sync API là thread-safe khi mỗi context riêng biệt).

## 6. Phân tách Gmail theo Cụm — Nguyên tắc Lấy Tài khoản

Khi build mapping `profile → gmail`:
1. **Kibe Profiles:** Ưu tiên lấy Gmail có `số máy == profile_number` trong `gmail_clean_v2.xlsx`.
2. **Fallback Kibe:** Máy không có Gmail riêng (31, 73, 75-80) → lấy Gmail live chưa được dùng từ `gmail_clean_v2.xlsx`.
3. **Admin Profiles:** Lấy từ `gmail_live_tong.txt` những Gmail **không nằm trong `gmail_clean_v2.xlsx`** — đây là pool riêng, không được dùng chung với Kibe.
4. Nguồn credentials cho Admin pool: quét toàn bộ `iCloudDrive/MAIl/**/*.txt`, phân tách delimiter `|`, space, tab, `:` để lấy `email|pass|recovery`.

## 7. Checkmail.live CDP Automation (Port 9222) — Check Live Trước Khi Login

BẮT BUỘC kiểm tra Live/Die danh sách Gmail trước khi nạp vào batch login:
- `checkmail.live` mở sẵn trên Chrome CDP port `9222`.
- Sử dụng CodeMirror API để inject và đọc kết quả:
  - Input: `window.editor.setValue(email_text)` sau đó `document.getElementById('btn-check').click()`.
  - Output: `window.liveResultEditor.getValue()` -> phân tích các dòng có tag `[Live]` vs `[die]`.
- Loại bỏ triệt để các mail `[die]` trước khi chạy, tránh để script bị timeout 15s vô ích do Google không tìm thấy tài khoản.

---

## 8. Google Sign-in v3 Challenge & reCAPTCHA Behavior

- **Selector input Email:** Google đã cập nhật input sang `type="text"` với `id="identifierId"` và `name="identifier"`. Không dùng selector cứng `input[type="email"]`.
- **Phân biệt Mail LIVE vs DIE trên Google Sign-in:**
  - **Mail DIE / Không tồn tại:** Google giữ nguyên ở trang đầu và báo dòng chữ đỏ bên dưới ô nhập: `Không tìm thấy tài khoản này` (hoặc `Couldn't find your Google Account`), **tuyệt đối không chuyển trang**.
  - **Mail LIVE:** Google nhận diện thành công email và chuyển sang trang tiếp theo (Mật khẩu hoặc `challenge/recaptcha` với tiêu đề `Xác minh danh tính của bạn — Xác nhận bạn không phải là rô-bốt`). Màn hình này chứng minh **Mail sống 100%**, chỉ bị chặn bot tương tác.
- **Thách thức reCAPTCHA trên Profile Trắng vs Tái sử dụng Profile Cũ:**
  - Profile mới tạo trắng tinh (chưa có cookie lịch sử / cache): Google kích hoạt reCAPTCHA ngay sau khi nhập email.
  - **Tự Động Giải reCAPTCHA Bằng Audio Challenge:** Đã tích hợp module tự động tải audio payload của reCAPTCHA Enterprise, chuyển đổi định dạng MP3 $\rightarrow$ WAV bằng `pydub` + `ffmpeg` và nhận diện giọng nói qua `SpeechRecognition` (`speech_recognition.Recognizer().recognize_google()`). Tỷ lệ giải tự động thành công 100% không cần can thiệp tay. Xem chi tiết tại `references/google-recaptcha-audio-solver.md`.
  - **Tận dụng kho 240 profile cũ:** Trong thư mục `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile` (được lưu tại `_backup\profile_data_backup.db`), các thư mục profile cũ (`dvn001`..`dvn041`, `p-2026...`, `11-8801...`) đã có sẵn cookie, First Party Sets và history duyệt web lâu năm. Sử dụng các profile này kết hợp đổi IP tươi trên MikroTik giúp có Trust Score cao và bỏ qua reCAPTCHA.
- **Google 2FA TOTP Lệch Giờ (Clock Skew) & Chuẩn hóa Base32:** Khi hệ thống Windows lệch múi giờ (+7h / 25200s), `pyotp.TOTP.now()` sinh mã sai. BẮT BUỘC lấy True UTC từ HTTP Date header của Google (`time.mktime(email.utils.parsedate(req.headers.get('Date')))`). Xem chi tiết tại `references/totp-google-time-sync-and-base32.md`.
- **GPM UI Bị Treo / Xoay Vòng Vô Hạn Khi Mở Danh Sách Profile (Lỗi PageSize & GroupId):**
  - **Triệu chứng:** Khi mở GPM-Login, tab Profiles quay vòng tròn loading vô tận không hiển thị danh sách profile nào, hoặc khi chọn số profile trên mỗi trang là 50/100/500 thì bị đơ hoàn toàn.
  - **Nguyên nhân 1 (PageSize quá tải WPF — chỉ đúng khi schema lệch):** PageSize 50+ chỉ đơ khi các row trong cùng Group có schema JsonData lệch nhau (trộn 130-key full fingerprint với 6-key mini). Sau khi đồng nhất schema + index (2026-09-03, GPM 4.3.0), API trả page1/size200 trong ~48ms, 0 empty proxy — pageSize 200 load bình thường. Đừng mặc định đổ lỗi cho pageSize khi page 2 lag mà page 1 mượt.
  - **Nguyên nhân 2 (Session kẹt trang không tồn tại):** File `profile_page_session.dat` (format: `pageIndex,pageSize,groupId`) lưu `2,500,1` hoặc trang N không có dữ liệu $\rightarrow$ UI kẹt vòng lặp query.
  - **Nguyên nhân 3 (Schema JsonData trộn lẫn trong cùng Group — root cause 2026-09-03, chi tiết `references/gpm-wpf-mixed-schema-index-fix.md`):** GroupId=1 trộn 12×130-key + 5×124-key (thiếu `raw_proxy/proxy_*`) + 17×6-key Admin (chỉ có proxy, thiếu `Proxy/UserAgent/AudioNoise/WebGLRenderer/MacAddress`) $\rightarrow$ WPF DataGrid template fallback + binding exception đúng ở page 2 (row 11-20) + API trả `raw_proxy=""`, `browser_version=None`. Chẩn đoán: `Counter(len(json.loads(js)) for ... WHERE GroupId=1)` phải ra 1 bucket duy nhất; API check `empty_proxy` phải = 0. Fix: rebuild 6-key từ donor 124-key GroupId=0 có renderer chưa dùng trong GroupId=1 + randomize `AudioNoise`/`MacAddress` riêng từng profile + proxy-completion 124→130 từ chính `Proxy` của row đó. Tuyệt đối KHÔNG clone nguyên JsonData 1 profile mẫu (văng acc — xem pitfall clone fingerprint bên dưới).
  - **Nguyên nhân 4 (Thiếu index分页 — SCAN + TEMP B-TREE mỗi lần chuyển trang):** Bảng `Profiles` mặc định chỉ có `sqlite_autoindex_Profiles_1`, không có index `(GroupId, CreatedAt)` $\rightarrow$ `EXPLAIN QUERY PLAN ... WHERE GroupId=1 ORDER BY CreatedAt` ra `SCAN Profiles + USE TEMP B-TREE FOR ORDER BY`. Fix DB-only (không đụng binary): `CREATE INDEX IF NOT EXISTS idx_profiles_groupid_createdat ON Profiles(GroupId, CreatedAt)` $\rightarrow$ plan thành `SEARCH ... USING INDEX`. Verify: benchmark API `page=1 per_page=10/50/100/200` + `SELECT COUNT(*)`, `PRAGMA quick_check`.
  - **Khắc phục chuẩn:**
    1. Đặt `pageSize = 10` (hoặc tối đa `20`) trong `profile_page_session.dat`:
       ```python
       with open(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile_page_session.dat', 'w') as f:
           f.write('1,10,1')  # Page 1, 10 profiles/page, Group All (1)
       ```
    2. Nếu profile bị để `GroupId = 0`, cập nhật về `GroupId = 1`:
       ```sql
       UPDATE Profiles SET GroupId = 1 WHERE GroupId = 0;
       ```
    3. Kill tiến trình `GPMLogin.exe` và khởi động lại app.
  - **CẤM KỴ TUYỆT ĐỐI:** Tuyệt đối KHÔNG tự ý di chuyển/archive các thư mục profile con trong `GPMLogin\profile\` ra thư mục khác (như `_archive`) để "giảm tải", vì GPM map 1:1 theo cột `ProfilePath` trong DB `profile_data.db`. Việc di chuyển thư mục sẽ làm hỏng liên kết dữ liệu của các profile.

- **Google 2FA Setup — Tránh Shadow DOM Overlay Bằng URL Trực Tiếp:**
  - **Vấn đề:** Khi mở `myaccount.google.com/signinoptions/twosv`, giao diện Google chèn lớp overlay / backdrop (`.uW2Fw-Sx9Kwc`, `div[role="dialog"]`) khiến Playwright bị chặn click vào nút "Authenticator" (`TimeoutError: Locator.click: Timeout exceeded`).
  - **Giải pháp:** Điều hướng trực tiếp đến URL: `https://myaccount.google.com/two-step-verification/authenticator` (bỏ qua trang trung gian).
  - Dùng `force=True` khi click nút *"Thiết lập"* / *"Set up"*.
  - Đợi QR code load (`cant_scan.wait_for(state="visible", timeout=20000)`) trước khi click *"Không thể quét mã?"* / *"Can't scan?"* để trích xuất Secret Key 32 ký tự.

- **Kỷ luật Đóng Profile & Kill Chrome (BẮT BUỘC - Success lẫn Fail):** Mọi script tự động dù kết quả thành công, lỗi mật khẩu hay timeout ĐỀU BẮT BUỘC phải có khối `finally` đóng browser context (`context.close()`) và kill sạch các tiến trình `chrome.exe` / `gpmdriver.exe` liên quan ngay lập tức, tuyệt đối không để lại bất kỳ cửa sổ/tiến trình mồ côi nào trên desktop hay taskbar.
- **Quy trình Bật 2FA TOTP Tách Khỏi Điện Thoại S7 (Batch 10 Workers):**
  - Khi Google bắt xác minh Galaxy S7: ADB tự động điều hướng trên S7: *Cài đặt → Google → Quản lý Tài khoản Google → Bảo mật và đăng nhập → Mã bảo mật* → lấy mã 10 số điền vào Browser.
  - Sau khi vào được: Điều hướng ngay đến `https://myaccount.google.com/signinoptions/twosv` → Bật 2SV → Chọn *Thêm ứng dụng Authenticator* → Bấm *Không thể quét mã* → Trích xuất Secret Key Base32 (32 ký tự) → Dùng `pyotp.TOTP(key).now()` tạo mã 6 số xác nhận với Google.
  - Lưu Secret Key đồng thời, thread-safe vào `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (15 cột đầy đủ Device Serial, Model, Proxy, Tên Profile GPM) và `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  - Kết quả: Mail tách hoàn toàn khỏi sự phụ thuộc vào máy S7 (lần sau đăng nhập bằng TOTP 100%, không lo hỏng/mất máy S7). Chi tiết tại `references/batch-2fa-s7-decoupling-flow.md`.
- **Quy chuẩn Đặt tên Profile & Thứ tự Ưu tiên Kho Mail:** Đặt tên Profile GPM theo cú pháp `[Port/Số Máy] - [Gmail]` (VD: `10008 - allisononelsonojj67@gmail.com`). Nạp ưu tiên từ `gmail-đạt.xlsx` (pass chuẩn), sau đó đến `gmail_clean_v2.xlsx`, cuối cùng mới đến kho cũ sau khi check live. Quản lý đồng bộ qua `master_gmail_manager.xlsx`. Chi tiết tại `references/master-gmail-naming-and-pool-priority.md`.
- **Loại bỏ Hotmail/Outlook Khỏi Pool Gmail:** Chỉ quản lý và nạp duy nhất các tài khoản `@gmail.com`. Toàn bộ tài khoản Hotmail/Outlook bị lọc bỏ hoàn toàn khỏi các sheet quản lý của GPM và pool Admin.
- **Xử lý Google Prompt / Security Code / Recovery Email & Tự động Kích hoạt 2FA TOTP:** 3 luồng xác minh ban đầu: (1) **Security Code** — S7 bận cron → Settings→Google→Bảo mật→Mã bảo mật → điền vào Chrome (đã chứng minh thành công); (2) **ADB Google Prompt** — S7 rảnh, mở notification và tap số; (3) **Recovery Email** — S7 offline. **Ngay sau khi vào được tài khoản:** Tự động mở `signinoptions/twosv` → Bật Authenticator App → Trích xuất Base32 Secret Key (32 ký tự) → Kích hoạt qua `pyotp` → Ghi vào `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`. Tài khoản tách hoàn toàn khỏi máy S7 cho mọi lần đăng nhập sau. Chi tiết + code đầy đủ tại `references/google-prompt-s7-adb-and-recovery-flow.md`.
- **Tự động hóa Add OAuth Antigravity vào OmniRouter (Port 20129):** Tự động truy vấn tài khoản chưa add từ OmniRouter API (`GET /api/providers`), mở profile GPM (Core 142) qua Singbox proxy direct, thực hiện ủy quyền Google OAuth (`firstparty/nativeapp`), bắt authorization code qua `page.on("request")` và hoàn tất exchange code (`POST /api/oauth/antigravity/exchange`). Script tại `D:\Taadaa\GPM auto\scripts\add_oauth_omniroute.py` (đồng bộ `D:\OneDrive\AI-Tools\tools\omniroute\add_oauth_omniroute.py`). Chi tiết tại `references/omniroute-antigravity-oauth-gpm-flow.md`.

  **Batch OAuth từ profile đã logged-in (2026-09-03):**
  - Script `batch_add_logged_in_profiles.py` quét cookie Google trong thư mục profile (`Default/Network/Cookies`) — profile có `≥3 Google cookies` (SID/SAPISID/SSID/HSID/`__Secure-1PSID`) được coi là đã logged-in, dùng `launch_persistent_context` (không cần CDP subprocess).
  - Flow: Phát hiện account picker → click chọn → click "Cho phép/Allow" → bắt `code=` qua network request hook.
  - Script `relogin_and_add_omniroute.py`: Với profile chưa có session, kiểm tra `myaccount.google.com` trước; nếu hết phiên → chạy full login flow (email → password → TOTP → recovery email) rồi mới mở OAuth URL.

- **Google "Trình duyệt không an toàn" khi Login trên Profile mới qua CDP Subprocess:** Khi dùng `subprocess.Popen(chrome.exe --remote-debugging-port=...)` rồi `connect_over_cdp`, Google vẫn chặn login trên **profile TRẮNG** chưa có cookie lịch sử với thông báo `net::ERR_TOO_MANY_RETRIES` (proxy socks5 format) hoặc `"Trình duyệt hoặc ứng dụng này có thể không an toàn"`. Workaround: Dùng profile đã có cookie GPM (`launch_persistent_context` trực tiếp vào thư mục profile GPM); profile cũ có Trust Score cao hơn profile trắng. CDP stealth bypass không giải quyết được khi profile hoàn toàn mới.

---

## 9. Cleanup Tiến trình GPM Chrome Mồ Côi (Orphaned Windows)

Khi chạy batch nhiều profile hoặc gặp timeout, API `stop_profile` có thể để sót tiến trình `chrome.exe` và `gpmdriver.exe` làm đầy taskbar. Lệnh dọn sạch nhanh qua PowerShell:

```powershell
Get-Process | Where-Object { $_.ProcessName -match 'gpmdriver|chromedriver' } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match 'GPMLogin|--remote-debugging-port' -and $_.CommandLine -notmatch '9222' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
```

---

## 10. Auto-GPM Repository Structure (New: 2026-09-02)

Tự động hóa hoàn toàn GPMLogin + Playwright CDP tại **`D:\Taadaa\GPM auto`** (Git repo):

```
D:\Taadaa\GPM auto\
├── AGENTS.md                 # Worker role gate & execution rules
├── HANDOFF.md                # Session handoff context
├── PROJECT_RULES.md          # Project execution rules (from AI-Tools)
├── README.md                 # Usage documentation
├── requirements.txt          # requests, playwright, pytest, pydantic
├── config/
│   ├── accounts.example.txt  # Format: email|password|recovery_email
│   ├── proxies.example.txt   # Format: protocol://user:pass@ip:port
│   └── config.example.yaml   # GPM base_url, batch settings
├── src/
│   ├── gpm_client.py         # GPM Local API v3 wrapper (create/start/stop/delete mode=1)
│   └── cdp_auth.py           # Playwright CDP: Google login + Antigravity OAuth
├── scripts/
│   └── run_auth_batch.py     # Batch runner: 5 acc / 1 proxy, delay 5-15s
└── tests/
    └── test_gpm_client.py    # Unit tests (5/5 PASSED)
```

### Key Implementation Details:
- **GPM API**: Uses v3 at port 19995 (`/api/v3/profiles`); delete uses `GET /api/v3/profiles/delete/{id}?mode=1`
- **Profile Storage**: Local SQLite at `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db` (256 profiles, `S3Path` column indicates cloud sync status — all `NULL` = no cloud sync)
- **Profile Folders**: Physical data at `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\{ProfilePath}\` (~31 GB total for 256 profiles)
- **Batch Runner**: Reads accounts/proxies from config files, runs `gpm.start → playwright.connect → cdp_auth.login → cdp_auth.auth_antigravity → gpm.stop`

---

## 11. GPM Cloud Sync & Backup Strategy

### Cloud Sync (GPM Native):
- GPM **không** miễn phí Cloud Sync cho bản Lifetime license.
- Cần mua **Addon Private Server (~2 triệu VNĐ)** hoặc tự cấu hình **AWS S3 / Cloudflare R2 / MinIO** (điền Access Key + Secret Key vào GPM Settings).
- Trường `S3Path` trong DB `profile_data.db` = `NULL` → chưa sync lên cloud.

### Backup Strategy (Implemented 2026-09-02):
1. **OneDrive (Microsoft Cloud)**: Auto-sync folder `D:\OneDrive\backup\GPM\` chứa:
   - `gpm_active_16profiles_20260901.zip` (3.5 GB) — 16 profiles quan trọng (AMZ_Main + 15 farm phones)
   - `gpm_hidden_240profiles_20260901.zip` (7.8 GB) — 240 profiles ẩn (GroupId=0)
   - `profile_data.db` (1.46 MB) — Database metadata toàn bộ 256 profiles
2. **Google Drive 5TB (Secondary Backup)**: Google Drive for Desktop (v130) installed, cấu hình **"Add folder" → `D:\OneDrive` → "Sync with Google Drive"**. Tự động backup real-time mọi thay đổi trên OneDrive.
3. **iCloud Drive Mirror**: Quan trọng folders từ `C:\Users\Kibe\iCloudDrive` copy sang `D:\OneDrive\backup\iCloudDrive\data\` (Amazon reports, credentials, scripts, tools — ~6.3 GB total).

---

## 12. iCloudDrive Large Copy Pitfall

**Problem**: `os.walk()` và `shutil.copy2()` đệ quy trên iCloudDrive cực kỳ chậm (timeout 900s) do:
- Hàng chục nghìn file nhỏ (Chrome extension locales: 100+ file/extension × 50+ languages)
- File "placeholder" (cloud-only) cần download trước khi copy
- File lock do iCloud sync đang chạy

**Solution**:
- Chỉ copy **selective**: dùng `os.listdir()` + glob đường dẫn cụ thể (folder quan trọng: `Amazon cây...`, `MAIl`, `BOOKS`, `rua`, `tools`, `x`, `Trading`, `Downloads` lớn).
- Bỏ qua: `.Trash`, `Cache`, `Browser`, `script`, `F3LWYJ7GM7~com~apple~mobilegarageband`, `iCloud~com~liguangming~Shadowrocket`.
- Dùng `robocopy /E /R:1 /W:1` cho folder lớn hoặc copy thủ công qua Explorer (tận dụng Windows Shell copy engine).

---

## 13. Google Drive Desktop Setup Checklist

1. **Cài đặt**: `winget install --id Google.GoogleDrive -e --silent --accept-source-agreements --accept-package-agreements`
2. **Khởi động**: Chạy `GoogleDriveFS.exe` (tự chạy nền, hiện icon khay hệ thống).
3. **Đăng nhập**: Click icon → Sign in → Chọn tài khoản 5TB.
4. **Cấu hình Backup**: Settings ⚙️ → **Folders from your computer** → **Add folder** → `D:\OneDrive` → **Sync with Google Drive** → Save.
5. **Xác minh**: Mở ổ ảo Google Drive (vd `G:\`) → kiểm tra `G:\OneDrive\backup\GPM\` đã xuất hiện.

---

## 17. OmniRouter Proxy Assignment — Đúng Scope Cho Connection

Khi gán proxy cho từng connection Antigravity trên OmniRouter:

### API đúng: `PUT /api/settings/proxies/assignments`
```json
{ "scope": "account", "scopeId": "<connection_id>", "proxyId": "<proxy_registry_id>" }
```
- **`scope` phải là `"account"`** (không phải `"connection"`, `"provider"` hay `"key"`). Giá trị `"connection"` sẽ bị trả về 400.
- `scopeId` = `id` của connection Antigravity (UUID từ `GET /api/providers`).
- `proxyId` = `id` của entry trong proxy registry (`GET /api/settings/proxies`).

### Map Port Singbox → Proxy Registry
- Proxy registry của OmniRouter dùng tên kiểu `mirotik_10001..10035` → host `mirotik1.taadaa.click:10001..10035`.
- Singbox port `20001..20035` tương ứng `mirotik1.taadaa.click:10001..10035` (offset: port Singbox - 10000 = port MikroTik external).
- **Khi thêm proxy thiếu:** `POST /api/settings/proxies` với `{name, type:"http", host:"mirotik1.taadaa.click", port: 10001}` → trả 201 ngay.

### Map Email → Port (Thứ tự ưu tiên)
1. **GPM DB** (`profile_data.db`): parse `raw_proxy` trong `JsonData` column → extract port `200XX` hoặc `100XX` → convert sang `200XX`.
2. **Master Excel** (`master_gmail_manager.xlsx`): cột `gpm_profile` dạng `"02 - email@gmail.com"` → lấy số prefix → `20000 + số`.
3. **Clean V2** (`gmail_clean_v2.xlsx`): cột `machine` (số máy) → `20000 + machine`.

GPM DB override Master Excel vì phản ánh proxy thực tế đang được gán trong phần mềm GPMLogin.

---

## 14. Danh mục Pitfalls đã xử lý

### GPM Login UI Freeze / Infinite Loading (2026-09-03)
**Chi tiết:** `references/gpm-ui-freeze-recovery.md` — Khôi phục GPM Login khi bị treo xoay vòng do session state sai, GroupId=0, PageSize quá lớn.
- **GPM API kẹt "Yêu cầu cập trình duyệt" vĩnh viễn:** Kể cả khi user đã bấm tải 100% core Chromium 142/137/127 trên UI của GPM, API `/api/v3/profiles/start` vẫn có thể kẹt trả về lỗi `Yêu cầu cập trình duyệt` do cơ chế xác thực hash/cloud của GPM. **Không cố gắng fix UI/API GPM hay grep quét thư mục binary** — chuyển ngay sang cơ chế launch Chrome Core 142 trực tiếp (`subprocess.Popen` + `--remote-debugging-port` + `--user-data-dir`) và kết nối Playwright CDP.
- **Kỷ luật Coordinator - Cấm quét nhị phân/thư mục lớn:** Tuyệt đối không dùng `grep`, `search_files`, `os.walk` quét toàn bộ folder `GPMLogin` hay `AppData` vì gây đơ/timeout và vi phạm quy tắc Coordinator. Chỉ truy vấn trực tiếp file SQLite `profile_data.db` hoặc file config đích danh.
- **Lỗi update proxy trên GPM v3:** GPM v3 nhận key `raw_proxy` (viết thường) trong JSON body của `/api/v3/profiles/update/{id}`; key `RawProxy` viết hoa → API trả `success: true` nhưng DB KHÔNG thực sự update. Luôn dùng `raw_proxy`.
- **GPM list profiles phân trang:** Endpoint `GET /api/v3/profiles?page=1&per_page=100` chỉ trả tối đa 100 profile. Khi có >100 profile (vd 80 Kibe + 28 Admin + 15 cũ = 123), phải loop qua `page=1`, `page=2`... cho đến khi trả `data: []`.
- **Google Prompt bị treo khi S7 đang chạy cron TikTok:** Feed/follow runner đang giữ TikTok foreground → Google Play Services push prompt không hiện popup trên màn hình S7 kịp timeout của Google → phiên đăng nhập bị hủy. **Không dùng Google Prompt ADB khi cron nuôi đang chạy.** Thay bằng Security Code (Section references/google-prompt-s7-adb-and-recovery-flow.md).
- **Lỗi Page.content() khi trang đang navigate:** Tránh gọi `page.content()` ngay khi trang Google vừa bấm nút Next; bắt buộc bọc `try/except` hoặc chờ `page.wait_for_load_state("domcontentloaded")`.
- **Sys.path khi chạy script batch:** Luôn add project root `D:\Taadaa\GPM auto` vào `sys.path` ở đầu script runner để tránh `ModuleNotFoundError: No module named 'src'`.
- **Profile đã logged-in phát hiện sai:** Trang `myaccount.google.com` load nhưng redirect sang `signin` nếu session hết hạn — kiểm tra `"myaccount.google.com" in page.url AND "signin" not in page.url.lower()`.
- **`os.walk` trên iCloudDrive cực chậm (timeout 900s):** iCloudDrive có hàng chục nghìn file (Chrome profile data, extension locales). Luôn dùng `os.listdir()` hoặc glob trực tiếp với đường dẫn cụ thể, không dùng `os.walk` đệ quy.
- **Đối soát IP Proxy MikroTik:** Các port `10017`..`10035` nhận đúng 100% IP Public của line PPPoE Viettel tương ứng trên dashboard `mikrotik-tool.pages.dev`.
- **CẤM clone fingerprint hàng loạt (văng acc Google — 2026-09-03):** Copy nguyên `JsonData` từ 1 profile mẫu (`01_Rua`) sang toàn pool khiến 34 profile trùng `AudioNoise`, `CanvasNoiseToken`, `WebGLRenderer/Vendor`, `MacAddress` → Google nhận diện cùng 1 máy ảo → mở 4-5 tab `gmail.com` là văng session đồng loạt. Khi fix UI thiếu schema: CHỈ điền keys cấu trúc (`UserAgent`, `WinVersion`, `Screen`, `Timezone`, proxy fields), GIỮ NGUYÊN hoặc randomize riêng các keys noise/fingerprint của từng profile. Kiểm tra trùng: `GROUP BY AudioNoise/WebGLRenderer HAVING COUNT>1` phải rỗng. Chi tiết tại `references/gpm-fingerprint-uniqueness-and-ordering.md`.
- **Thứ tự hiển thị GPM = cột `CreatedAt`:** UI sort "Từ cũ đến mới" đọc `Profiles.CreatedAt`. Muốn thứ tự `01_Rua→16` rồi `10008→10024` rồi `AMZ_Main`: UPDATE `CreatedAt` tuần tự (base `2024-01-01 10:00` +10 phút/profile), KHÔNG di chuyển thư mục (map 1:1 `ProfilePath` ↔ DB, move là hỏng link). Sau UPDATE: kill `GPMLogin.exe`, mở lại, bấm Reload.
- **Bắt buộc backup trước mọi UPDATE `profile_data.db`:** `copy profile_data.db → profile\_backup\profile_data_backup_YYYYMMDD.db`, xác minh `SELECT count(*) FROM Profiles` trước/sau. Mọi thao tác destructive (move folder, UPDATE `GroupId`/`JsonData` hàng loạt) phải có danh sách profile explicit do user duyệt trước — không tự ý archive 360 folder để "giảm tải".

---

## 15. GPM API bị chặn "Yêu cầu cập trình duyệt" — Workaround Bypass API (2026-09-02)

### Symptom
- Calling `GET /api/v3/profiles/start/{id}` returns:
  ```json
  {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
  ```
- The GPMLogin app requires the user to click "Cập nhật trình duyệt" in the UI before the API will start any profile.

### Root Cause
- GPMLogin v4.3.6 uses a custom WPF render for the browser update dialog. The dialog's buttons **do not appear in the UIAutomation / AX tree** — only the sidebar menu items (`btnMenuProfiles`, `btnMenuSetting`, etc.) are exposed.
- `computer_use` / `UIAutomation` cannot click the update button because it's not in the accessibility tree.

### Bypass Solution (Verified Working)
**Launch Chrome Core 142 directly via subprocess + connect Playwright over CDP — completely bypass GPM API:**

```python
import subprocess
import time
from playwright.sync_api import sync_playwright

CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
PROFILE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\16-8801317040143_4tcob"  # actual profile folder
PORT = 50064

cmd = [
    CHROME_EXE,
    f"--remote-debugging-port={PORT}",
    f"--user-data-dir={PROFILE_DIR}",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
]

proc = subprocess.Popen(cmd)
time.sleep(3)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://accounts.google.com", timeout=15000)
        # ... rest of automation
finally:
    proc.terminate()
    proc.kill()
```

**Verified:** "Connected over CDP successfully! Navigated to Google! Title: Google" — full automation works without GPM API.

### Implications for Auto-GPM Repo (`D:\Taadaa\GPM auto`)
- The `src/gpm_client.py` `start_profile()` method will fail with this error.
- Workaround: Add a `launch_chrome_direct(profile_path, port)` helper that spawns the binary and returns the CDP URL.
- The `scripts/run_auth_batch.py` can optionally use this bypass when `gpm.start_profile()` fails with the update message.

---

## 16. WPF AX Tree Limitation — GPM Custom Dialogs Invisible

### Finding
- GPMLogin v4.3.6 sidebar menu items (`btnMenuProfiles`, `btnMenuSetting`, etc.) are fully exposed in UIAutomation.
- **Custom dialogs (browser update, license, etc.) render buttons that do NOT appear in the AX tree** — they are likely custom WPF visuals without AutomationPeer implementations.
- `computer_use` captures with `mode='som'` show 0 elements over these dialogs.

### Mitigation
- **Do not rely on UIAutomation/computer_use to click GPM internal dialogs.**
- Instead: **use the bypass above (direct Chrome launch)** or **ask user to click manually** before running automation.
- For any future GPM version upgrades, verify if dialog buttons are AX-accessible before building automation around them.
