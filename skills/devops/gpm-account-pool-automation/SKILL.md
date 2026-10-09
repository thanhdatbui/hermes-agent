---
name: gpm-account-pool-automation
description: "GPMLogin v3 + Playwright/CDP account-pool operations: proxy-safe Gmail lifecycle, nurture, OAuth, and ChatGPT direct registration."
version: 1.2.0
---

# GPMLogin Local API & Account Pool Automation

## 1. Khi nào sử dụng

Use for GPM v3 (19995), Gmail/Hotmail lifecycle, proxy-safe account selection, CRX/CDP, cache/core issues, OAuth, ChatGPT/Codex pool operations, watchdogs, pagination, and geo-safety. Existing topic detail remains in `references/`; cron summary handling is in `references/cron-watchdog-report-triage.md`.
- No-Agent Cron Silent Watchdog: `references/no-agent-cron-silent-watchdog-and-telegram-chunking.md`.
- Preflight Liveness & Auto-Launch: `references/gpm-local-api-liveness-and-autolaunch-pattern.md`.
- Hook ChatGPT Web/Codex: `references/codex-oauth-phone-verification-5sim-and-sumistore.md`.
- Bounded Codex OAuth: `references/codex-oauth-bounded-live-run-evidence.md`.
- Map proxy Farm S7 ↔ Profile GPM (Kibe 1:1 vs Admin pool).
- Profile ẩn & Google OTP: `references/profile_db_and_verification_quirks.md`.
- ChatGPT candidate selection: `references/chatgpt-direct-reg-verification-and-candidate-selection.md`.
- Google Prompt & mã bảo mật S7: `references/s7_device_lock_google_prompt_and_oauth.md`.
- Dọn cache có chọn lọc: `references/selective_site_cleanup_cdp_verification.md`.

---

## 2. GPMLogin Local API v3 (Port 19995)

GPMLogin phiên bản hiện tại sử dụng chuẩn API v3. Port được lưu động tại `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\api_port.dat` (mặc định: `19995`).
- **Preflight & Auto-Launch**: Khi app bị đóng hoặc port 19995 không phản hồi, cron script bắt buộc dùng preflight check để auto-launch `GPMLogin.exe` hoặc thoát silent exit 0 (xem `references/gpm-local-api-liveness-and-autolaunch-pattern.md`), cấm `sys.exit(1)` làm nổ alert cron rác.

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

### A. Quy Tắc Bắt Buộc Gán Proxy TRƯỚC Khi Khởi Chạy Browser & Login (2026-09-04):
- **Gán Proxy Ngay Khi Tạo Profile:** Khi gọi API tạo profile (`POST /api/v3/profiles/create`), payload BẮT BUỘC phải truyền trường `raw_proxy: "test.taadaa.click:<PORT>:<USER>:<PASS>"` ngay từ mili-giây đầu tiên.
- **CẤM TUYỆT ĐỐI:** CẤM bật browser bằng IP mạng nhà rồi mới vào đổi proxy hay login (Google sẽ bắt checkpoint thiết bị lạ ngay lập tức).
- **Kỷ Luật Đóng Profile Tức Thì (Success Lẫn Fail):** Sau khi login xong từng profile (kể cả thành công, lỗi mật khẩu hay dính checkpoint), BẮT BUỘC khối `finally` phải gọi `GET /api/v3/profiles/stop/{id}` để đóng sạch browser và giải phóng DeviceLock/RAM, tuyệt đối KHÔNG ngâm nhiều browser mở đồng thời gây tràn tài nguyên.

### B. Cụm Profile Kibe Farm S7 (80 Máy = Đúng 40 Proxy x 2 Máy):
- **Cơ cấu 40 Proxy vật lý bất biến của Kibe:**
  - 32 cổng Mobi 4G: `test.taadaa.click:5101..5108`, `5111..5118`, `5121..5128`, `5131..5138` (auth: `mobi1`..`mobi38`).
  - 7 cổng MikroTik: `mirotik1.taadaa.click:10001..10007` (auth: `admin@1:admin@1`).
  - 1 cổng Khoalee: `khoalee.duckdns.org:16002` (auth: `5ns08q:AmLmaMJ0`).
  - Mỗi proxy map cố định đúng 2 máy S7 (Tầng 1 Máy 1..32, Tầng 2 Máy 39..70, MikroTik Máy 33..37 & 71..80).
- **Quy trình đối soát Proxy chưa đăng nhập trong ngày (Daily Untouched Proxy Audit):** Xem chi tiết Section 6 tại `references/proxy-pairing-and-batch-circuit-breaker.md` (truy vấn nhanh O(1) từ `profile_data.db` `GroupId=1` lọc theo `CreatedAt`/`UpdatedAt` so với 40 port trong `PROXYgandienthoai.xlsx`, lọc bỏ 100% khoaleemagic và máy chỉ có Hotmail).
- **Quy tắc gán proxy 1:1:** BẮT BUỘC gán cố định 100% theo file `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`. Tuyệt đối ép tài khoản nào phải login đúng proxy của máy đó. CẤM login dồn dập nhiều tài khoản trên cùng 1 proxy trong cùng 1 batch (tránh Google kích hoạt Phone SMS Checkpoint).
- **Cụm 16 Profile Gốc & Active (Profile `01_Rua` → `15` + `AMZ_Main` + Profile Kibe đã Live) — CẤM ĐỤNG:**
  - **CẤM KỴ TUYỆT ĐỐI:** CẤM thay đổi proxy, CẤM gán proxy MikroTik Admin, CẤM đưa 16 profile này vào batch restore/test tài khoản khác, CẤM reset DB làm mất `GroupId=1` của các profile này. Mọi thao tác ghi đè proxy lên 16 profile này đều là vi phạm nghiêm trọng.

### B. Kho 240 Profile Ẩn (Backup Pool `GroupId=0` / `gpm_hidden_240profiles_*.zip`):
- Đây là kho profile cũ (tên dạng `11-8801...`, `12-8801...`, `dvn001...`) dùng để tái sử dụng / nạp tài khoản mới.
- Khi cần restore thử nghiệm profile cũ hoặc cấp profile cho 28 port Admin: **BẮT BUỘC CHỈ ĐƯỢC CHỌN TRONG KHO 240 NÀY (`GroupId=0`)**.
- Quy trình: Lấy profile sạch $\rightarrow$ Gán proxy MikroTik Admin (`10008`..`10035`) $\rightarrow$ Đổi IP $\rightarrow$ Launch Chrome Core 142 qua Playwright persistent context $\rightarrow$ Đăng nhập Gmail + 2FA TOTP.

### C. Cụm Admin (Profile `Admin_10008` → `Admin_10035`):
- **Proxy:** Gán 28 port MikroTik Admin (`10008` → `10035` hoặc Singbox direct `192.168.110.2:20008..20035`).
- **Tài khoản:** **CHỈ** đăng nhập các Gmail tự do ngoài Kibe có mật khẩu & mã 2FA TOTP chuẩn xác (từ kho nguồn `2592 Gmail old.txt` sau khi check live), tuyệt đối không dùng list thô sai pass.
- **Cấm kỵ:** Tuyệt đối KHÔNG đăng nhập tài khoản đang nằm trên máy Kibe vào IP MikroTik Admin (IP Đà Nẵng).

### D. Kỹ thuật Proxy MikroTik Singbox Không Auth (Tránh Lỗi `ERR_TOO_MANY_RETRIES` & Hairpin NAT):
- Khi dùng Playwright / Chrome CDP với proxy domain ngoài có auth (`http://test.taadaa.click:51XX` hoặc `mirotik1.taadaa.click:100XX` với user:pass): Playwright proxy authentication bridge thường xuyên gặp lỗi vòng lặp `net::ERR_TOO_MANY_RETRIES` trên Chrome do xung đột xác thực digest/basic.
- **Lỗi Hairpin NAT khi GPM Start Profile trên Host Local:** Khi PC chạy trong mạng nội bộ (`192.168.110.123`), gọi API `/api/v3/profiles/start/{id}` với `raw_proxy` là domain ngoài (`mirotik1.taadaa.click:100xx`) sẽ bị GPM pre-flight test fail (`"Không thể kết nối tới proxy"`) do router không hỗ trợ Hairpin loopback.
  - **Khắc phục khi test/launch trên máy host:** Tạm thời đổi `raw_proxy` sang LAN IP gateway (`192.168.110.2:100xx:admin@1:admin@1`) hoặc Singbox direct port (`192.168.110.2:200xx`), start profile, và restore lại cấu hình gốc khi stop. Xem template script `scripts/verify_restored_profiles_cdp.py`.
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
     - Quét và click liên hoàn các nút: `"Bỏ qua"`, `"Để sau"`, `"Not now"`, `"Hủy"`, `"Skip"`. **Lưu ý quan trọng:** Nút *"Để sau"* trên màn hình video selfie (`gds.google.com`) render dưới dạng thẻ `<a>` chứa thẻ con `<span>`, KHÔNG PHẢI thẻ `<button>`. Bắt buộc dùng selector quét cả `a`, `button` và `span`: `a:has-text("Để sau"), button:has-text("Để sau"), span:has-text("Để sau"), a:has-text("Bỏ qua"), button:has-text("Bỏ qua")`.
   - **Fail-closed:** Nếu gặp checkpoint số điện thoại / OTP 2FA / reCAPTCHA không tự giải quyết được $\rightarrow$ ghi nhận lỗi, đóng profile ngay lập tức và chuyển sang profile tiếp theo, không treo tiến trình.

---

## 5. Concurrent (Song Song) Batch Login & 2FA Setup

Khi cần login hoặc bật 2FA hàng loạt profile nhanh, dùng `ThreadPoolExecutor` hoặc Subagents với **`max_workers=3..4`**:
- **Preflight Check Excel Trước Khi Bật 2FA (Tiết kiệm 60-70% thời gian):** Trước khi nạp danh sách, BẮT BUỘC đối soát cột `2fa` / `Secret Key` trong `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`. Tài khoản đã có Secret Key thì BỎ QUA 100%, chỉ gom các tài khoản thực sự chưa bật 2FA.
- **Kỷ Luật Viết Script Python Thực Thi Độc Lập (CẤM Lái Browser Từng Turn Bằng LLM):** Subagent bắt buộc viết một script Python hoàn chỉnh (`scripts/run_2fa_*.py`) và chạy qua terminal thay vì gọi LLM lái browser từng click (tránh ballooning token, kéo dài 1-2 tiếng và crash khi LLM gateway timeout `APIConnectionError`).
- **Kỷ Luật Điều Phối Batch Runner Cho Subagent (Chống Trùng Lặp Tiền Kiểm Tra — 2026-09-05):** Khi Coordinator đã xác nhận môi trường (ADB S7 online, GPM Local API port 19995 sẵn sàng, IMAP kết nối tốt, Excel đã đối soát), prompt dispatch BẮT BUỘC chỉ thị worker thực thi ngay chu trình 3 bước: `1. Tạo script patcher -> 2. py_compile -> 3. Chạy lệnh batch script -> 4. Báo cáo kết quả`. CẤM TUYỆT ĐỐI worker tiêu tốn 20–30 turns đọc lại hàng loạt file tham chiếu hay test lại hạ tầng gây cạn kiệt ngân sách `max_iterations = 35` trước khi thực sự chạy batch.
- **Cấm Trộn Lẫn MikroTik Admin (`10008..10035`) Vào Group 1 Farm S7:** Group 1 là kho chuẩn 1:1 của Farm S7 gồm 32 cổng Mobi 4G (`test.taadaa.click:5101..5138`), 7 cổng MikroTik Farm (`mirotik1.taadaa.click:10001..10007` cho Máy 33..37 & 71..80) và 1 cổng Khoalee (`khoalee.duckdns.org:16002` cho Máy 38). **CHỈ CẤM** tạo hay nạp profile MikroTik Admin (`10008..10035`) vào Group 1, CẤM để xảy ra duplicate profiles cùng email giữa Farm và Admin.
- **Kỷ Luật Ngân Sách Lượt Gọi Cho Mọi Batch Runner GPM / Login / 2FA (Budget <= 15 Calls Discipline — 2026-09-05):** Khi nhận yêu cầu chạy batch login / bật 2FA / OAuth cho danh sách máy xác định kèm script mẫu (như `run_batch_12_untouched_proxies.py`):
  - BẮT BUỘC: Tạo script thực thi trực tiếp bằng `write_file` trong 2–3 turn đầu tiên (sao chép logic từ script tham khảo và nạp targets), gọi `python -m py_compile`, chạy script qua `terminal(background=True)` hoặc `terminal()`, rồi đọc log/kết quả.
  - CẤM TUYỆT ĐỐI: Tiêu tốn 10–30 turns đọc dàn trải từng đoạn file mẫu, test curl từng proxy riêng lẻ, kiểm tra ADB từng máy, hay query thủ công DB/Excel nhiều lần gây cạn kiệt ngân sách lượt gọi (`max_iterations = 15` hoặc `35`) trước khi script thực thi được chạy. Mọi logic kiểm tra proxy, ADB device lock, IMAP OTP, fallback password và đồng bộ Excel đã được đóng gói hoàn chỉnh bên trong script runner.
- **Cú Pháp Proxy Chứa Ký Tự `@` (MikroTik `admin@1:admin@1`):**
  - Trong curl hoặc URL chuẩn: Ký tự `@` trong username/password bắt buộc phải URL-encode thành `%40` (ví dụ `http://admin%401:admin%401@mirotik1.taadaa.click:10003`). Nếu để nguyên `admin@1`, curl sẽ parse sai authority và báo lỗi `Unsupported proxy syntax: Port number was not a decimal number`.
  - Trong GPMLogin API `raw_proxy`: Định dạng phân tách bằng dấu hai chấm `host:port:user:pass` (ví dụ `mirotik1.taadaa.click:10003:admin@1:admin@1`), TUYỆT ĐỐI KHÔNG url-encode ký tự `@` trong payload gửi tới GPM Local API.
- **Cấm bung 10-25 workers cùng lúc:** GPM Local API (19995) sẽ bị nghẽn port (`connect ECONNREFUSED`), crash Chrome và đóng context hàng loạt.
- **Stagger Startup (Bắt buộc):** Trì hoãn 10-15s giữa các lần start profile của từng worker để tránh đột biến RAM và CPU.
- **Thời gian chờ Chrome bind port:** Sau khi gọi `start/{id}`, chờ 5-10s trước khi gọi `connect_over_cdp` (kèm retry 5 lần, mỗi lần 2-3s).
- **Kỷ luật đóng profile tức thì:** Mỗi worker xử lý xong từng profile (thành công hay thất bại) BẮT BUỘC gọi `GET /api/v3/profiles/stop/{id}` và dọn tiến trình con ngay lập tức, không ngâm trình duyệt.
- Chi tiết kỹ thuật tại `references/google-2fa-totp-localization-and-concurrency.md`.
- **Script mẫu sản xuất:** `scripts/run_2fa_pipeline_canonical.py` (bao gồm xử lý redirect challenge password, bóc secret Base32, tính TOTP, đồng bộ Excel 2 chiều, và kill Chrome theo port tránh đóng nhầm browser cá nhân).

## 6. Phân tách Gmail theo Cụm — Nguyên tắc Lấy Tài khoản

Khi build mapping `profile → gmail`:
1. **Kibe Profiles:** Ưu tiên lấy Gmail có `số máy == profile_number` trong `gmail_clean_v2.xlsx`.
2. **Fallback Kibe:** Máy không có Gmail riêng (31, 73, 75-80) → lấy Gmail live chưa được dùng từ `gmail_clean_v2.xlsx`.
3. **Admin Profiles:** Lấy từ `gmail_live_tong.txt` những Gmail **không nằm trong `gmail_clean_v2.xlsx`** — đây là pool riêng, không được dùng chung với Kibe.
4. Nguồn credentials cho Admin pool: quét toàn bộ `iCloudDrive/MAIl/**/*.txt`, phân tách delimiter `|`, space, tab, `:` để lấy `email|pass|recovery`.

## 7. Checkmail.live Automation (Playwright & Mobile Proxy Cloudflare Bypass) — Check Live Trước Khi Login

BẮT BUỘC kiểm tra Live/Die danh sách Gmail trước khi nạp vào batch login:
- `checkmail.live` yêu cầu session đăng nhập có credit / API Key (`document.getElementById('api-key')`).
- Nếu chưa login hoặc IP bị ban ("Multiple accounts detected"): Bắt buộc dùng Playwright persistent context kết nối qua **Mobile Proxy Farm** (`http://test.taadaa.click:5101`, auth `mobi1:TaadaaMobi#2026!`) kèm `--disable-blink-features=AutomationControlled` để Cloudflare Turnstile tự động giải trong 1-3s.
- Form đăng ký: Username bắt buộc chỉ chứa chữ và số `[a-zA-Z0-9]+` (5-12 ký tự, không dùng dấu `_`). Click `.switch-btn` trên `login.php` để kích hoạt render Turnstile trên form đăng ký.
- Sử dụng CodeMirror API để inject danh sách Gmail (bare emails only, cấm nạp pass/secret):
  - Input: `window.editor.setValue(payload)` sau đó `document.getElementById('btn-check').click()`.
  - Output: `window.liveResultEditor.getValue()` -> phân loại regex `[Live]`, `[die]`, `[Disabled]`, `[Verify]`, `[Unregistered]`. Tốc độ ~75 mails / 1.5s.
- **Quy tắc Phân định Proxy Farm vs Admin Pool (BẮT BUỘC):**
  - Gmail Kibe Farm S7 (Máy 1..80) bắt buộc map cố định vào proxy Farm `test.taadaa.click` (ports `5101..5138` / Singbox `20001..20074`).
  - Tuyệt đối KHÔNG gán hoặc sửa proxy MikroTik admin pool (`10001..10007` hoặc `10008..10035`) cho các tài khoản farm.
  - Ưu tiên hàng đầu của tự động hóa GPM: Login, bảo toàn và nuôi dàn Gmail Kibe Farm S7 trước, không được ưu tiên hay nhầm lẫn với dàn Admin pool phụ.
- **Quy tắc Bảo mật Tuyệt đối khi Check Live:**
  - BẮT BUỘC chỉ trích xuất và gửi duy nhất chuỗi email thuần (`xxx@gmail.com`) lên trang check live bên ngoài (`checkmail.live`).
  - CẤM TUYỆT ĐỐI bóc tách hay gửi kèm mật khẩu, Recovery Email, mã OTP hay 2FA Secret lên bất kỳ tool/website check live nào.
- Runner sản xuất: `D:\Taadaa\GPM auto\scripts\run_checkmail_kibe_farm.py` (lưu kết quả JSON/TXT tại `checkmail_results/kibe_farm_gmail_live_results.json` và cập nhật `master_gmail_manager.xlsx`).

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
- **Google 2FA TOTP Lệch Giờ (Clock Skew) & Chuẩn hóa Base32 — BUG CRITICAL (2026-09-04):** Trên Windows UTC+7, `time.mktime(email.utils.parsedate(req.headers.get('Date')))` trừ thêm 25200s (7h) vì `time.mktime` interpret struct_time là local time rồi convert sang epoch. Kết quả: TOTP code lệch ~7 vòng → Google báo "Sai mã 2FA". **Fix bắt buộc: dùng `calendar.timegm(email.utils.parsedate(response.headers['Date']))` thay thế** — `calendar.timegm` treat struct_time là UTC trực tiếp, cho True UTC epoch. Sau fix tỷ lệ TOTP success 100%. Xem chi tiết tại `references/totp-google-time-sync-and-base32.md`.
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
  - **Dialog Button Multi-Set Pitfall (2026-09-05):** Trong dialog thiết lập Authenticator của Google, DOM render 2 bộ nút song song (bộ đầu ẩn `visible=False`, bộ sau hiện `visible=True`). Khi bấm *Tiếp theo* / *Next* hoặc *Xác minh* / *Verify*, BẮT BUỘC duyệt qua `dialog.locator('button').all()` và chỉ click nút thỏa mãn `b.is_visible()`. Ô nhập mã TOTP sau khi bấm Next là `input[type="text"]` (không dùng selector cứng `input[type="tel"]`).
  - **Màn Hình Trung Gian Trước reCAPTCHA Khi Vào 2SV (2026-09-05):** Khi điều hướng trực tiếp vào URL Authenticator, Google có thể hiện màn hình trung gian *"Xác minh danh tính của bạn"* có nút *"Tiếp theo"* trước khi iframe reCAPTCHA được mount vào DOM. Script cần click *"Tiếp theo"* này trước, sau đó mới quét và giải reCAPTCHA qua Audio Challenge. Nếu Google disable nút audio (`rc-button-disabled`), ưu tiên preflight check Excel để bỏ qua nếu tài khoản đã có Secret Key từ trước. Chi tiết kỹ thuật tại `references/google-authenticator-2fa-activation-discipline.md`.

- **Kỷ luật Đóng Profile & Kill Chrome (BẮT BUỘC - Success lẫn Fail):** Mọi script tự động dù kết quả thành công, lỗi mật khẩu hay timeout ĐỀU BẮT BUỘC phải có khối `finally` đóng browser context (`context.close()`) và kill sạch các tiến trình `chrome.exe` / `gpmdriver.exe` liên quan ngay lập tức, tuyệt đối không để lại bất kỳ cửa sổ/tiến trình mồ côi nào trên desktop hay taskbar.
- **Quy trình Bật 2FA TOTP Tách Khỏi Điện Thoại S7 (Batch 10 Workers):**
  - Khi Google bắt xác minh Galaxy S7: ADB tự động điều hướng trên S7: *Cài đặt → Google → Quản lý Tài khoản Google → Bảo mật và đăng nhập → Mã bảo mật* → lấy mã 10 số điền vào Browser.
  - Sau khi vào được: Điều hướng ngay đến `https://myaccount.google.com/signinoptions/twosv` → Bật 2SV → Chọn *Thêm ứng dụng Authenticator* → Bấm *Không thể quét mã* → Trích xuất Secret Key Base32 (32 ký tự) → Dùng `pyotp.TOTP(key).now()` tạo mã 6 số xác nhận với Google.
  - **GIỮ NGUYÊN KẾT NỐI S7 — CẤM TUYỆT ĐỐI ĐĂNG XUẤT S7 KHỎI `device-activity` (User Invariant):** Kệ nguyên thiết bị Samsung S7 kết nối trong mục Lời nhắc của Google! TUYỆT ĐỐI CẤM vào `device-activity` bấm "Đăng xuất" S7 vì sẽ làm văng tài khoản trên điện thoại Farm (lỗi "Yêu cầu xử lý tài khoản", tê liệt cron nuôi acc). Sau khi bật 2FA Authenticator TOTP xong, chỉ cần lưu Secret Key vào Excel. Khi đăng nhập GPM, nếu gặp màn hình nhắc S7 thì tự động bấm **"Thử cách khác" (Try another way)** $\rightarrow$ chọn **"Ứng dụng Authenticator"** $\rightarrow$ điền mã TOTP 6 số từ Excel. Chi tiết tại `references/google-prompt-s7-never-signout-discipline.md`.
  - Lưu Secret Key đồng thời, thread-safe vào `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (15 cột đầy đủ Device Serial, Model, Proxy, Tên Profile GPM) và `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  - Kết quả: Mail tách hoàn toàn khỏi sự phụ thuộc vào máy S7 (lần sau đăng nhập bằng TOTP 100%, không lo hỏng/mất máy S7). Chi tiết tại `references/batch-2fa-s7-decoupling-flow.md` và `references/google-prompt-s7-never-signout-discipline.md`.
- **Quy chuẩn Đặt tên Profile & Thứ tự Ưu tiên Kho Mail:** Đặt tên Profile GPM theo cú pháp `[Số Máy] - [Gmail] - [Port]` (VD: `01 - duongkien12022001@gmail.com - 5101`). Nạp ưu tiên từ `gmail-đạt.xlsx` (pass chuẩn), sau đó đến `gmail_clean_v2.xlsx`, cuối cùng mới đến kho cũ sau khi check live. Quản lý đồng bộ qua `master_gmail_manager.xlsx`. Chi tiết tại `references/master-gmail-naming-and-pool-priority.md`, `references/gmail-pool-hierarchy-and-checklive-discipline.md` và `references/gpm-profile-standardization-and-verification-gates.md`.
- **Quy tắc Verification-First Naming & Gán Proxy S7 Bất Biến (2026-09-04):** Khi import/restore profile cũ, BẮT BUỘC mở profile lên kiểm tra DOM `myaccount.google.com` xác thực tài khoản Gmail thực tế đang live bên trong; CHỈ ĐỔI TÊN thành `<Số_Máy> - <Gmail> - <Port>` khi đã verify live; profile hết hạn/dính checkpoint giữ nguyên tên. Gán proxy chuẩn xác theo số máy S7 trong `PROXYgandienthoai.xlsx` (CẤM gán lung tung, Máy 9 dùng port 5111, Máy 41/42/60 map đúng port mobi tương ứng). Chi tiết tại `references/gpm-profile-standardization-and-verification-gates.md`.
- **Bản Chất Các Kho Mail & Kỷ Luật Không Chệch Trọng Tâm (2026-09-04):**
  - **Kho Kibe Farm S7 (`clean_v2`):** Tài sản vận hành số 1 (80 máy S7), bắt buộc map proxy Farm `test.taadaa.click:5101..5138` (Singbox `20001..20074`), luôn ưu tiên số 1 trong mọi thao tác GPM.
  - **Kho Đạt (`Gmail_Dat`):** Là **Gmail CỔ (Aged/Ancient Accounts)** có Trust Score cao (90% Live), KHÔNG PHẢI mail mới reg.
  - **Admin Pool (`10008..10035`):** Là pool phụ gán proxy MikroTik cho OmniRoute, tuyệt đối không được ưu tiên trước dàn S7.
  - Chi tiết tại `references/gmail-pool-hierarchy-and-checklive-discipline.md`.
- **Loại bỏ Hotmail/Outlook Khỏi Pool Gmail:** Chỉ quản lý và nạp duy nhất các tài khoản `@gmail.com`. Toàn bộ tài khoản Hotmail/Outlook bị lọc bỏ hoàn toàn khỏi các sheet quản lý của GPM và pool Admin.
- **Xử lý Google Prompt / Security Code / Recovery Email & Tự động Kích hoạt 2FA TOTP:** 3 luồng xác minh ban đầu: (1) **Security Code** — S7 bận cron → Khởi động intent trực tiếp `com.google.android.gms/.app.settings.GoogleSettingsLink` → Banner tài khoản → "Tài khoản Google" → "Mã bảo mật" (hoặc chuyển tài khoản tại header dropdown `bounds=[216,159][792,224]`) → lấy mã 10 số điền vào Chrome; (2) **ADB Google Prompt** — S7 rảnh, mở notification và tap số; (3) **Recovery Email** — S7 offline. Chi tiết tại `references/samsung-s7-google-settings-intent-and-security-code.md` và `references/google-prompt-s7-adb-and-recovery-flow.md`. **Ngay sau khi vào được tài khoản:** Tự động mở `signinoptions/twosv` → Bật Authenticator App → Trích xuất Base32 Secret Key (32 ký tự) → Kích hoạt qua `pyotp` → Ghi vào `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`. Tài khoản tách hoàn toàn khỏi máy S7 cho mọi lần đăng nhập sau.
- **Tự động hóa Add OAuth Antigravity vào OmniRouter (Port 20129):** Tự động truy vấn tài khoản chưa add từ OmniRouter API (`GET /api/providers`), mở profile GPM (Core 142) qua Singbox proxy direct, thực hiện ủy quyền Google OAuth (`firstparty/nativeapp`), bắt authorization code qua `page.on("request")` và hoàn tất exchange code (`POST /api/oauth/antigravity/exchange`). Khi gặp challenge S7, tự động bọc `acquire_device_lock` lấy Security Code 10 số từ Google Play Services. **Sau khi exchange thành công:** BẮT BUỘC gán proxy 1:1 theo port qua `PUT /api/settings/proxies/assignments` (`scope: "account"`), gọi `POST /api/providers/<connection_id>/sync-models` để kích hoạt danh mục models và cập nhật `token_expires_at = expires_at` trong SQLite `storage.sqlite` để tránh lỗi pre-dispatch `ALL_TARGETS_SKIPPED`. Script tại `D:\Taadaa\GPM auto\scripts\add_oauth_omniroute.py` (đồng bộ `D:\OneDrive\AI-Tools\tools\omniroute\add_oauth_omniroute.py`). Chi tiết tại `references/omniroute-antigravity-oauth-gpm-flow.md` và `references/s7-security-code-oauth-integration-discipline.md`.
- **Tự động hóa Add OAuth Codex vào OmniRoute (Port 20129) qua GPM Profiles (2026-09-05):** Khác với Antigravity, Codex dùng PKCE callback server trên fixed port 1455 (`GET /api/oauth/codex/start-callback-server`). Khi Chrome chạy qua proxy 4G ngoài (`test.taadaa.click:5101..5105`), redirect loopback `localhost:1455` có thể bị proxy chặn. Dùng cơ chế **Dual-Capture Callback**: bắt authorization code qua `page.on("request")` hoặc `page.url`, đồng thời script host chủ động gửi HTTP GET trực tiếp tới `http://127.0.0.1:1455/auth/callback?...` để đảm bảo callback server nhận params và kích hoạt exchange. Sau đó poll `POST /api/oauth/codex/poll-callback` lấy `connection.id` và gán proxy 1:1 qua `PUT /api/settings/proxies/assignments` với `scope: "account"`. **Lưu ý critical:** GPM API v3 start không trả `profile_path`; bắt buộc map trước `profile_path` để giải mã DPAPI/AES-GCM từ `Login Data`, đồng thời quét `account_deactivated` trên DOM để fail-fast không bị treo 120s. Chi tiết tại `references/codex-oauth-omniroute-gpm-flow.md`.
- **GPM API v3 Start Response Thiếu `profile_path` (2026-09-05):** Response của `GET /api/v3/profiles/start/{id}` chỉ trả về `remote_debugging_address` và `process_id`, hoàn toàn không có `profile_path`. Mọi script tự động cần giải mã DPAPI `Login Data` hoặc đọc thư mục profile BẮT BUỘC phải map trước `profile_path` từ SQLite `profile_data.db` (`SELECT ProfilePath FROM Profiles WHERE Id=?`) thay vì dựa vào response của API start.
- **Kỷ Luật Đăng Nhập Đúng Tài Khoản Codex 9Router Trên Profile GPM (User Invariant 2026-09-05):** Khi mở profile GPM để đăng nhập lại Codex OAuth vào OmniRoute, BẮT BUỘC chỉ đăng nhập đúng tài khoản tương ứng đã cấu hình trong 9Router (`bevels.vanity8s@icloud.com`, `dishes.66-panic@icloud.com`, `98.duper-comb@icloud.com`, `bulbous_elector_3m@icloud.com`, `quocthanhthao.962@outlook.com`, `quorum.nuggets-0i+4o4l5d@icloud.com`). Mỗi profile GPM đã được người dùng lưu sẵn thông tin tài khoản/mật khẩu trong Chrome (`Login Data`), khi mở lên chỉ cần chọn đúng tài khoản tương ứng đó để xác thực, tuyệt đối không đăng nhập chéo hay nạp tài khoản ngoài pool.
- **Quy trình Đối soát Inventory GPM Đã Login vs OmniRoute (3-Tier Verification Gate):** Khi cần audit hoặc tìm các profile GPM đã login Gmail hợp lệ nhưng chưa từng add vào OmniRoute: áp dụng cổng xác minh 3 tầng (DOM check `gpm_group1_verification_results.json` / `prompt_removal_results.json` -> SQLite cookie jar `Default/Network/Cookies` count >= 3, `expires_utc` còn hạn -> Master Excel 2FA secret + đã tắt Google Prompt). Lưu ý API OmniRoute `/api/providers` trả về dict `{"connections": [...], "total": N}` (không phải list). Chi tiết kỹ thuật tại `references/gpm-omniroute-inventory-reconciliation.md`.

  **Batch OAuth từ profile đã logged-in (2026-09-03):**
  - Script `batch_add_logged_in_profiles.py` quét cookie Google trong thư mục profile (`Default/Network/Cookies`) — profile có `≥3 Google cookies` (SID/SAPISID/SSID/HSID/`__Secure-1PSID`) được coi là đã logged-in, dùng `launch_persistent_context` (không cần CDP subprocess).
  - Flow: Phát hiện account picker → click chọn → click "Cho phép/Allow" → bắt `code=` qua network request hook.
  - Script `relogin_and_add_omniroute.py`: Với profile chưa có session, kiểm tra `myaccount.google.com` trước; nếu hết phiên → chạy full login flow (email → password → TOTP → recovery email) rồi mới mở OAuth URL.

- **Google "Trình duyệt không an toàn" khi Login trên Profile mới qua CDP Subprocess:** Khi dùng `subprocess.Popen(chrome.exe --remote-debugging-port=...)` rồi `connect_over_cdp`, Google vẫn chặn login trên **profile TRẮNG** chưa có cookie lịch sử với thông báo `net::ERR_TOO_MANY_RETRIES` (proxy socks5 format) hoặc `"Trình duyệt hoặc ứng dụng này có thể không an toàn"`. Workaround: Dùng profile đã có cookie GPM (`launch_persistent_context` trực tiếp vào thư mục profile GPM); profile cũ có Trust Score cao hơn profile trắng. CDP stealth bypass không giải quyết được khi profile hoàn toàn mới.

---

## 9. Google Session Verification via Playwright CDP (NEW: 2026-09-04)

### Mục đích
Xác minh nhanh tất cả profile GPM trong Group 1 (hoặc bất kỳ group nào) có **Google session hoạt động** và **email khớp với tên profile** hay không. Dùng cho:
- Inventory check hàng ngày/buổi
- Phát hiện profile hết hạn session (cookie expire, bị checkpoint, bị văng)
- Xác thực trước khi chạy batch OAuth / Antigravity

### Workflow chuẩn (Sequential - lần lượt từng profile)

```python
def verify_google_session(profile_id, expected_email):
    # 1. Start profile qua GPM API
    start_resp = requests.get(f"{GPM_BASE}/api/v3/profiles/start/{profile_id}", timeout=25).json()
    if not start_resp.get("success"):
        return {"match": "START_FAILED", "details": start_resp.get("message")}
    
    cdp_addr = start_resp["data"]["remote_debugging_address"]
    port = cdp_addr.split(":")[-1]
    time.sleep(2.5)  # CRITICAL: wait for Chrome to bind port
    
    # 2. Connect CDP with retry (race condition fix)
    for attempt in range(6):
        try:
            browser = pw.chromium.connect_over_cdp(f"http://{cdp_addr}", timeout=8000)
            break
        except:
            time.sleep(1.5)
    
    # 3. Navigate & check session
    ctx = browser.contexts[0]
    page = [p for p in ctx.pages if not p.url.startswith("chrome-extension://")][0]
    page.goto("https://myaccount.google.com/", wait_until="domcontentloaded", timeout=25000)
    time.sleep(3)
    
    current_url = page.url
    if "about" in current_url.lower() or "signin" in current_url.lower() or "servicelogin" in current_url.lower():
        # Redirected to Google About/SignIn = NO valid session
        browser.close()
        return {"match": "NO", "session": False, "details": f"Redirected to {current_url}"}
    
    # 4. Extract email from DOM
    emails = page.evaluate('''() => {
        const emails = new Set();
        const elements = document.querySelectorAll('a[href*="SignOutOptions"], [aria-label*="@"], [title*="@"], [data-email]');
        for (const el of elements) {
            [el.getAttribute('aria-label')||'', el.getAttribute('title')||'', el.getAttribute('data-email')||'', el.innerText||'']
                .forEach(t => (t.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+/g)||[]).forEach(m => emails.add(m.toLowerCase())));
        }
        if (document.body) (document.body.innerText.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+/g)||[]).forEach(m => emails.add(m.toLowerCase()));
        return Array.from(emails);
    }''')
    
    actual = [e for e in emails if not e.endswith('@google.com')]  # filter system emails
    match = "YES" if any(e.lower() == expected_email.lower() for e in actual) else "NO"
    
    browser.close()
    return {"match": match, "session": True, "actual_email": ", ".join(actual) or "None", "details": f"Found: {actual}"}

# 5. Finally: Stop profile + kill orphans
requests.get(f"{GPM_BASE}/api/v3/profiles/stop/{profile_id}", timeout=10)
time.sleep(0.5)
kill_orphaned_chrome(target_port=port)
```

### Key Points (BẮT BUỘC)

| Step | Rule |
|------|------|
| **CDP Connect** | Retry 5-6 lần, delay 1.5-2s — GPM API trả CDP address nhưng Chrome chưa bind port xong |
| **Wait Time** | `time.sleep(2.5)` sau start, `time.sleep(3)` sau goto — không rút gọn |
| **Extension Filter** | Luôn lọc `chrome-extension://` pages trước khi dùng `context.pages[0]` |
| **Session Check** | Redirect về `google.com/account/about` hoặc `signin` = **NO SESSION** (cookie hết hạn) |
| **Email Match** | So sánh case-insensitive với expected email từ tên profile |
| **Cleanup** | `finally` block: `stop_profile` + `kill_orphaned_chrome(port)` — KHÔNG bỏ qua |

### Pattern khái quát cho N profiles (Sequential)

```python
results = []
for p in profiles:
    expected = extract_email_from_name(p["name"])
    res = verify_google_session(p["id"], expected)
    res["profile_name"] = p["name"]
    results.append(res)
    # Save progress incrementally
    with open(OUT_FILE, "w") as f: json.dump(results, f, indent=2)
    time.sleep(1)  # nghỉ giữa các profile
```

### Output mẫu (JSON)

```json
{
  "profile_name": "01 - thanhdatbui19951@gmail.com - 5101",
  "expected_email": "thanhdatbui19951@gmail.com",
  "actual_email": "thanhdatbui19951@gmail.com",
  "match": "YES",
  "has_valid_session": true,
  "details": "Session active. Email(s): thanhdatbui19951@gmail.com"
}
```

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

### Backup Strategy (Implemented 2026-09-02 & Updated 2026-09-05):
1. **OneDrive (Microsoft Cloud)**: Auto-sync folder `D:\OneDrive\backup\GPM\` chứa:
   ### Backup Strategy (Implemented 2026-09-02, Updated 2026-09-05):
   1. **OneDrive (Microsoft Cloud)**: Auto-sync folder `D:\OneDrive\backup\GPM\` chứa:
      - `gpm_active_profiles_20260905.zip` (141 MB) — 28 profiles Farm S7 đợt chạy 04-05/09/2026 (áp dụng kỹ thuật nén chọn lọc loại trừ cache rác, bảo toàn 100% auth session/cookies).
      - `profile_data_backup_20260905.db` (1.75 MB) — Bản sao lưu metadata DB SQLite ngày 05/09/2026.
      - `gpm_active_16profiles_20260901.zip` (3.5 GB) — 16 profiles quan trọng cũ (AMZ_Main + 15 farm phones)
      - `gpm_hidden_240profiles_20260901.zip` (7.8 GB) — 240 profiles ẩn (GroupId=0)
      - `profile_data.db` (1.46 MB) — Database metadata toàn bộ 256 profiles
      - `profile_data.db` và `profile_data_backup_20260905.db` (1.75 MB) — Database metadata toàn bộ profiles
- **Quy trình sao lưu chọn lọc & dọn tiến trình khóa file (2026-09-05):** Xem chi tiết tại `references/gpm-profile-backup-and-lockfile-cleanup.md`. Lọc bỏ thư mục rác (`Cache`, `Code Cache`, `Crashpad`, `CacheStorage`, `GPUCache`, `DawnGraphiteCache`, `DawnWebGPUCache`, `BrowserMetrics`) giúp giảm 25-30% dung lượng; bảo toàn 100% `Default/Network/Cookies`, `Default/Preferences`, `Default/Login Data`, `Default/GPMSoft`, `Local State`. BẮT BUỘC kill orphan `gpm_browser` trước khi nén để tránh lỗi `[Errno 13] Permission denied`.
   - `gpm_active_profiles_YYYYMMDD.zip` (~200 MB) — Bản sao lưu tinh gọn (Lean Backup) các profile vừa login thành công (chỉ nén `Cookies`, `Preferences`, `Login Data`, `GPMSoft`, loại trừ thư mục cache rác). Chi tiết tại `references/gmail-trust-oauth-lifecycle-and-gpm-backup.md`.
2. **Google Drive 5TB (Secondary Backup)**: Google Drive for Desktop (v130) installed, cấu hình **"Add folder" → `D:\OneDrive` → "Sync with Google Drive"**. Tự động backup real-time mọi thay đổi trên OneDrive.
3. **iCloud Drive Mirror**: Quan trọng folders từ `C:\Users\Kibe\iCloudDrive` copy sang `D:\OneDrive\backup\iCloudDrive\data\` (Amazon reports, credentials, scripts, tools — ~6.3 GB total).
- **Credential & Session Inventory Scanner**: Script `scripts/scan_gpm_gmail_inventory.py` và hướng dẫn `references/gpm-credential-and-cookie-audit-technique.md` — quét non-destructive (`mode=ro`) toàn bộ profile SQLite (`Login Data`, `Cookies`, `Web Data`, `Preferences`) và zip backup, tính `expires_utc` chuẩn epoch 1601 để lọc profile còn live cookies / saved pass chưa map vào `GroupId=1`.
- **Khôi Phục Profile Mất Khỏi DB Qua `gpm_pi.dat` & Xác Minh Live (2026-09-04):** Khi các thư mục profile con còn trên đĩa nhưng mất dòng trong DB `profile_data.db`, trích xuất metadata Base64 tại `Default\GPMSoft\gpm_pi.dat` để lấy lại 100% ID, name và 124-key Fingerprint gốc mà không cần đoán hay tạo mới. Xác minh live qua CDP myaccount.google.com và chỉ đổi tên `{Machine} - {Verified_Email}` khi thực sự live session. Chi tiết tại `references/legacy-profile-import-and-gpm-pi-dat-recovery.md`.

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
{ "scope": "account", "scopeId": "<connection_id>", "proxyId": "<proxy_id>" }
```
- **`scope` phải là `"account"`** (không phải `"connection"`, `"provider"` hay `"key"`). Giá trị `"connection"` sẽ bị trả về 400.
- `scopeId` = `id` của connection Antigravity (UUID từ `GET /api/providers`).
- `proxyId` = `id` của entry trong proxy registry (`GET /api/settings/proxies`).
- **Sau khi gán proxy:** BẮT BUỘC gọi `POST /api/providers/<connection_id>/sync-models` để kích hoạt models và đồng bộ trạng thái token.
- **Chi tiết kỹ thuật luồng Google OAuth & Duyệt S7 Device Lock:** Xem `references/google-oauth-omniroute-and-s7-approval.md` (bao gồm xử lý nút "Cách xác minh khác", phân tách input Pin ootp vs TOTP 2FA, và điều hướng tab "Tất cả dịch vụ" trên S7).
- **Gán Proxy 1:1 Bắt Buộc Để Tăng Trust & Chống Checkpoint:** Khi thêm OAuth Antigravity vào OmniRouter, BẮT BUỘC gán cứng proxy tương ứng theo port của từng Gmail. Tài khoản gọi API Antigravity đều đặn qua đúng proxy sẽ được Google nâng cấp lên Cloud/Developer trust, chống checkpoint rất tốt cho cả mail mới reg. Chi tiết tại `references/gmail-trust-oauth-lifecycle-and-gpm-backup.md` và `references/omniroute-oauth-proxy-assignment-and-trust-boost.md`.
- **Quy trình Gán Proxy Farm S7 (`5101..5138`) & Sync Models:**
  1. Gọi `GET /api/settings/proxies`, duyệt `items` tìm item có `port == target_port` để lấy `proxy_id`.
  2. Gọi `PUT /api/settings/proxies/assignments` với body `{"scope": "account", "scopeId": "<connection_id>", "proxyId": "<proxy_id>"}`.
  3. Gọi `POST /api/providers/<connection_id>/sync-models` để đồng bộ 12 models Google Cloud Code / Antigravity.
- **Loại trừ 100% tài khoản `khoaleemagic@gmail.com`:** Tuyệt đối không mở profile, không chạy OAuth hay gán proxy cho các tài khoản dính khoalee (M34, M37, M71).
- **Kỷ luật ngân sách lượt gọi khi chạy Batch OAuth (Budget Discipline):** Khi nhận chỉ đạo nạp OAuth với script mẫu và danh sách tài khoản/port xác định: BẮT BUỘC viết file runner (`run_add_oauth_batch*.py`) và kích hoạt qua `terminal` trong 2–3 turn đầu tiên. CẤM dùng 10–15 tool calls để đọc/kiểm tra rà soát lặp đi lặp lại các API/DB gây cạn kiệt ngân sách lượt gọi (`max_iterations = 15`) trước khi sinh ra kết quả thực tế.

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
- **Bảo tồn Profile Đa Tài Khoản (Multi-Gmail) vs Profile Chuẩn 1:1 (2026-09-04):** Các profile cũ như `01_Rua` mang nhiều session Google (`thanhdatbui19951@gmail.com`, `duongkien12022001@gmail.com`...) cùng cookie lịch sử quý giá. Tuyệt đối KHÔNG ghi đè cấu hình profile đơn lẻ lên `01_Rua` — restore thành profile riêng biệt `01_Rua_Legacy` (`GroupId=1`, path `x_rua_jidbq`, 124-key original Fingerprint). Chi tiết tại `references/multi-gmail-preservation-and-extension-cdp-filter.md`.
- **Lỗi Page.goto `net::ERR_ABORTED` do Extension Offscreen Page (2026-09-04):** Khi connect over CDP vào browser có extension (MetaMask...), `context.pages[0]` thường là extension background/offscreen page khiến `page.goto()` bị abort. Luôn lọc `regular_pages = [p for p in context.pages if not p.url.startswith("chrome-extension://")]`. Chi tiết tại `references/multi-gmail-preservation-and-extension-cdp-filter.md`.
- **Lỗi Page.content() khi trang đang navigate:** Tránh gọi `page.content()` ngay khi trang Google vừa bấm nút Next; bắt buộc bọc `try/except` hoặc chờ `page.wait_for_load_state("domcontentloaded")`.
- **Sys.path khi chạy script batch:** Luôn add project root `D:\Taadaa\GPM auto` vào `sys.path` ở đầu script runner để tránh `ModuleNotFoundError: No module named 'src'`.
- **Profile đã logged-in phát hiện sai:** Trang `myaccount.google.com` load nhưng redirect sang `signin` nếu session hết hạn — kiểm tra `"myaccount.google.com" in page.url AND "signin" not in page.url.lower()`.
- **`os.walk` trên iCloudDrive cực chậm (timeout 900s):** iCloudDrive có hàng chục nghìn file (Chrome profile data, extension locales). Luôn dùng `os.listdir()` hoặc glob trực tiếp với đường dẫn cụ thể, không dùng `os.walk` đệ quy.
- **Đối soát IP Proxy MikroTik:** Các port `10017`..`10035` nhận đúng 100% IP Public của line PPPoE Viettel tương ứng trên dashboard `mikrotik-tool.pages.dev`.
- **GPM CONCURRENT PROFILES — KHÔNG cần đóng profile trước khi mở profile khác (user-corrected):** GPMLogin thiết kế mỗi profile Chrome chạy độc lập với `--user-data-dir` riêng biệt → cookie jar hoàn toàn isolated. Mở 20+ profile cùng lúc là bình thường, session của profile này KHÔNG ảnh hưởng session của profile khác. Lý thuyết "phải đóng profile A trước khi mở profile B" là SAI HOÀN TOÀN. Chỉ cần đóng profile khi done với nó để giải phóng RAM/CPU.
- **Cookie session mất do script chạy concurrent với schema fix (2026-09-03):** Khi batch runner khởi động Chromium với profile X trong lúc JsonData của profile đó đang bị sửa schema (fingerprint cloning, key injection) → Chrome nhận config fingerprint lệch so với cookie jar cũ → Google phát hiện device mismatch → invalidate session → Chrome ghi đè cookie jar rỗng (chỉ còn tracking cookies, 0 critical session cookies). **Nguyên tắc:** TUYỆT ĐỐI KHÔNG chạy batch login/start profile trong khi đang update schema `JsonData` hàng loạt trong DB. Thứ tự bắt buộc: (1) Stop tất cả Chrome/runner → (2) Update DB → (3) Verify DB → (4) Mới start lại Chrome/runner.
- **CẤM clone fingerprint hàng loạt (văng acc Google — 2026-09-03):** Copy nguyên `JsonData` từ 1 profile mẫu (`01_Rua`) sang toàn pool khiến 34 profile trùng `AudioNoise`, `CanvasNoiseToken`, `WebGLRenderer/Vendor`, `MacAddress` → Google nhận diện cùng 1 máy ảo → mở 4-5 tab `gmail.com` là văng session đồng loạt. Khi fix UI thiếu schema: CHỈ điền keys cấu trúc (`UserAgent`, `WinVersion`, `Screen`, `Timezone`, proxy fields), GIỮ NGUYÊN hoặc randomize riêng các keys noise/fingerprint của từng profile. Kiểm tra trùng: `GROUP BY AudioNoise/WebGLRenderer HAVING COUNT>1` phải rỗng. Chi tiết tại `references/gpm-fingerprint-uniqueness-and-ordering.md`.
- **Thứ tự hiển thị GPM = cột `CreatedAt`:** UI sort "Từ cũ đến mới" đọc `Profiles.CreatedAt`. Muốn thứ tự `01_Rua→16` rồi `10008→10024` rồi `AMZ_Main`: UPDATE `CreatedAt` tuần tự (base `2024-01-01 10:00` +10 phút/profile), KHÔNG di chuyển thư mục (map 1:1 `ProfilePath` ↔ DB, move là hỏng link). Sau UPDATE: kill `GPMLogin.exe`, mở lại, bấm Reload.
- **Bắt buộc backup trước mọi UPDATE `profile_data.db`:** `copy profile_data.db → profile\_backup\profile_data_backup_YYYYMMDD.db`, xác minh `SELECT count(*) FROM Profiles` trước/sau. Mọi thao tác destructive (move folder, UPDATE `GroupId`/`JsonData` hàng loạt) phải có danh sách profile explicit do user duyệt trước — không tự ý archive 360 folder để "giảm tải".
- **Khôi phục Profile Nguyên bản từ OneDrive Backup (3.5GB) & DB Backup:** Khi profile bị văng do lệch Fingerprint, xem quy trình chi tiết tại `references/profile-restoration-from-onedrive-backup.md` và `references/gpm-restore-from-backup-and-session-verification.md`. Giải nén đồng thời folder Chrome từ `gpm_active_16profiles_20260901.zip` VÀ nạp `JsonData` gốc từ `profile_data_backup.db` (chỉ đổi proxy S7, giữ nguyên 100% fingerprint).
- **Quy tắc "Check First" — Giữ nguyên profile làm tay (User Rule 2026-09-04):** Trước khi tự động login hay khôi phục profile bất kỳ, BẮT BUỘC kiểm tra trạng thái login qua Playwright CDP tới `https://myaccount.google.com/`. Nếu đã có session sống (do User làm tay) -> GIỮ NGUYÊN BẢN 100%, BỎ QUA NGAY, cấm can thiệp.
- **Bắt Buộc Giữ Device Lock Khi ADB Can Thiệp S7 Lấy Mã Bảo Mật (Tránh Xung Đột Cron 6h):** Khi script tự động điều khiển ADB máy S7 để lấy mã bảo mật Google 10 số (Google Settings $\rightarrow$ Security Code) hoặc tap Google Prompt, BẮT BUỘC dùng context manager `with acquire_device_lock(machine=str(may), serial=serial, project="gpm-recovery"):` từ `automation_core.device_lock`. Khi cron nuôi acc (6h sáng) quét tới, nếu thấy lock đang giữ sẽ tự động skip máy an toàn, tuyệt đối không tranh chấp ADB/màn hình.
- **Quy chuẩn Đặt tên Profile Multi-Gmail Khôi Phục:** Khi khôi phục profile cũ có nhiều Gmail (như `x_rua_jidbq`), nếu đã có profile mới mang Gmail chính (`01 - duongkien...`), profile cũ BẮT BUỘC đổi tên theo Gmail phụ đang hoạt động bên trong (ví dụ `01 - thanhdatbui19951@gmail.com`) để phân biệt rõ ràng và không bị trùng tên.
- **Đồng bộ Đổi Tên Profile Legacy & JsonData trong SQLite `profile_data.db` (2026-09-04):** Khi chuẩn hóa tên profile GPM (như profile legacy `2_r7clp` $\rightarrow$ `02 - luuhuong28022000@gmail.com`): Tên profile được lưu ở 2 vị trí trong SQLite: cột `Profiles.Name` và key `JsonData['Name']`. Bắt buộc cập nhật đồng thời cả hai vị trí, đồng thời bảo toàn 100% các trường hardware fingerprint trong `JsonData` (124/130 keys). Đồng bộ vào `master_gmail_manager.xlsx` (cột `Tên Profile GPM`, `Proxy Đang Dùng` và `Ghi Chú` ghi rõ thư mục vật lý `Profile 2_r7clp (Legacy - Máy 2)` để truy vết).
- **GPM Start Profile CDP Race Condition & ECONNREFUSED Fix (2026-09-04):** Khi gọi API `GET /api/v3/profiles/start/{id}`, API trả về ngay `remote_debugging_address` nhưng Chrome binary mất 2-3s để bind port. Kết nối `p.chromium.connect_over_cdp` ngay lập tức sẽ ném lỗi `connect ECONNREFUSED`. **Bắt buộc:** Đặt `time.sleep(3)` kèm retry loop 5 lần (delay 2s) khi kết nối CDP.
- **Master Excel Regex Matching Số Máy (Tránh Match Nhầm Substring):** Khi tìm tài khoản theo số máy trong `master_gmail_manager.xlsx`, TUYỆT ĐỐI KHÔNG dùng substring `f"máy {mid}" in text` (sẽ match nhầm Máy 1 vào Máy 15, Máy 2 vào Máy 25). **Bắt buộc:** Dùng regex word boundary `re.search(rf"\bmáy\s*0?{mid}\b", num_str)`.
- **ADB Shell Hang & Khắc Phục Bằng `adb reconnect`:** Khi lệnh `adb -s <serial> shell` bị treo hoặc timeout 5s, KHÔNG khởi động lại PC hay rút cáp điện thoại — chạy ngay `subprocess.run([ADB_EXE, "-s", serial, "reconnect"])` để adb reset kết nối socket tức thì.
- **reCAPTCHA Enterprise Multi-Step & Phone IAP Checkpoint (2026-09-04):** Khi đăng nhập profile sạch, Google có thể hiện màn hình trung gian "Xác nhận bạn không phải là rô-bốt" trước khi load URL `challenge/recaptcha`. BẮT BUỘC giải xong audio captcha rồi bấm "Tiếp theo" để sang trang password. CẤM BẤM "Thử cách khác" trên trang reCAPTCHA vì Google sẽ redirect sang `signin/rejected`. Khi gặp `challenge/iap` (Phone SMS Checkpoint không bypass được), thực hiện fail-closed: xóa profile tạm mode=2, cập nhật `DIE` vào `master_gmail_manager.xlsx`. Chi tiết tại `references/recaptcha-glif-multi-step-and-phone-iap-handling.md`.
- **Google Antigravity OAuth 403 `VALIDATION_REQUIRED` & QR Code Checkpoint (2026-09-04):** Sau khi hoàn tất OAuth cấp quyền Antigravity, nếu gọi API sinh nội dung bị chặn 403 `Verify your account to continue`: (1) Mở CDP kiểm tra `myaccount.google.com/notifications`, tự động click `"Yes, it was me"` trên *Critical security alert*; (2) Nếu Google tiếp tục chuyển sang `accounts.google.com/uplevelingstep/selection` yêu cầu *"Scan the QR code with your phone"* (`AUTHORIZATION_UPLEVELING`), đây là cơ chế chặn bot độc quyền cho Developer API (hoàn toàn không có nút "Thử cách khác"). **CẤM** mở link `devicephoneverification` trực tiếp vào máy S7 không có camera/SIM (Google sẽ báo *"We couldn't verify your info"*). **Bắt buộc** dùng Camera điện thoại cá nhân thật quét mã QR trên màn hình PC để Google xác thực thiết bị vật lý. Có thể dùng `zxingcpp.read_barcodes()` giải mã `img[alt*="QR"]` (base64) để trích xuất link verification.
- **Bật 2-Step Verification (2FA) Tự Động Cho Tài Khoản Google Qua GPM CDP:** Khi tài khoản chưa bật 2FA, mở CDP điều hướng `https://myaccount.google.com/signinoptions/two-step-verification` $\rightarrow$ Điền mật khẩu từ `master_gmail_manager.xlsx` $\rightarrow$ Tự động click `Turn on 2-Step Verification` $\rightarrow$ Bắt modal và click `Done` trên hộp thoại `You’re now protected with 2-Step Verification` để kích hoạt trạng thái bảo vệ 2FA (Phone/Passkey/Prompt) an toàn.
- **Android Device Lock Preemption (`force_preempt=True`):** Khi gọi `acquire_device_lock`, nếu các phiên trước bị gián đoạn để lại stale lock file trong `~/.codex/device-locks/`, luôn truyền `force_preempt=True` và `bypass_proxy_readiness=True` khi can thiệp UI S7 lấy mã bảo mật để dọn dẹp các dead locks an toàn mà không bị lỗi `DeviceLockUnavailable`.
- **Cấm Tạo Profile Admin MikroTik Trùng Email Với Farm S7 (2026-09-04):** Tuyệt đối không tạo hay gán profile MikroTik (Admin pool) cho các tài khoản đang thuộc quyền quản lý của dàn Kibe Farm S7 (`test.taadaa.click:5101..5138`). Nếu phát hiện profile duplicate cùng email, BẮT BUỘC xóa ngay profile MikroTik và giữ nguyên duy nhất profile Farm S7.
- **GPM Proxy Fail-Safe (Chống Rò Rỉ IP Thật Khi Proxy Lỗi 407 — 2026-09-04):** Khi proxy gán vào profile bị lỗi kết nối hoặc sai authentication (HTTP 407), API `/api/v3/profiles/start/{id}` sẽ trả về `success: false` và từ chối mở browser. Đây là hành vi đúng chuẩn của GPM. CẤM gỡ bỏ proxy để start bằng IP nhà. Bắt buộc kiểm tra lại proxy tương ứng trong `PROXYgandienthoai.xlsx`.
- **Google 2FA UI Localization & Re-Auth Password Challenge Gate (2026-09-04):** Trên profile có locale tiếng Việt, selector text tiếng Anh (`2-Step Verification`, `Authenticator app`) sẽ fail timeout 100%. Bắt buộc dùng href pattern: `a[href*="signinoptions/twosv"]` và `a[href*="two-step-verification/authenticator"]`. Khi click vào 2SV, Google luôn yêu cầu re-authenticate password (`signin/challenge/pwd`) — bắt buộc đọc mật khẩu từ `master_gmail_manager.xlsx` / `gmail_clean_v2.xlsx` điền vào ô password và bấm Next trước khi tiếp tục thiết lập TOTP. Chi tiết tại `references/google-2fa-totp-localization-and-concurrency.md`.
- **Google 2FA Password Redirect Race Condition & Navigation Interrupted Fix (2026-09-05):** Khi submit password challenge trên `signin/challenge/pwd`, Google bất đồng bộ redirect về URL đích (`continue=.../signinoptions/twosv`). Nếu gọi ngay `page.goto(".../authenticator")` sẽ ném ngoại lệ Playwright `Page.goto: Navigation is interrupted by another navigation`. Khắc phục bắt buộc: điều hướng trực tiếp tới `signinoptions/twosv`, điền password, đợi URL đổi khỏi `challenge/pwd` và `signin` (loop kiểm tra 25s) và đợi 3s cho trang ổn định TRƯỚC KHI chuyển sang `two-step-verification/authenticator`.
- **Selector Engine CSS/Text Mixed Syntax Pitfall trong Playwright (2026-09-05):** Tránh kết hợp selector CSS (`button:has-text(...)`) với Playwright pure text (`text="Thiết lập"`) trong cùng 1 chuỗi phân cách bởi dấu phẩy, vì Playwright sẽ parse toàn bộ chuỗi dưới dạng CSS selector và ném `Unexpected token "=" while parsing css selector`. Thay vào đó, dùng helper `find_first_visible(container, [list_selectors])` duyệt qua danh sách các selector độc lập.
- **CẤM TUYỆT ĐỐI Đăng Xuất Thiết Bị S7 Khỏi `device-activity` Để "Tắt Lời Nhắc" (Google Prompt — 2026-09-05):** Lời nhắc của Google (Google Prompt) tự động gắn chặt với mọi máy Android đang đăng nhập tài khoản. Google **HOÀN TOÀN KHÔNG CÓ** nút gạt tắt riêng cho thiết bị nếu máy vẫn giữ đăng nhập. **CẤM TUYỆT ĐỐI** bấm "Đăng xuất" (Sign out) trên `device-activity` vì sẽ làm văng tài khoản Google trên điện thoại Samsung S7 của Farm, gây lỗi "Yêu cầu xử lý tài khoản" làm tê liệt cron nuôi acc. **Cách decouple S7 chuẩn khi login PC:** Giữ nguyên đăng nhập S7 trên Farm $\rightarrow$ Bật 2FA Authenticator TOTP $\rightarrow$ Khi login trên GPM hiện nhắc S7, script tự động click **"Thử cách khác" (Try another way)** $\rightarrow$ Chọn **"Ứng dụng Authenticator"** $\rightarrow$ Điền mã 6 số từ Secret Key trong Excel. Hoàn toàn không cần đụng vào máy S7 và không làm ảnh hưởng Farm. Chi tiết tại `references/google-prompt-s7-never-signout-discipline.md`.
- **PowerShell Process Cleanup Pipeline & Bash Expansion Bug (2026-09-05):** `Get-CimInstance Win32_Process | Stop-Process` bị lỗi nuốt âm thầm vì tìm process theo name thay vì PID; ngoài ra khi chạy từ MSYS Bash, `$_` trong double quotes bị Bash mở rộng thành chuỗi `$HOME` làm hỏng câu lệnh. Chuẩn hóa bắt buộc: dùng single quotes `'... | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'` hoặc dùng script Python với `psutil` để dọn sạch 100% tiến trình Chrome GPM theo port.
- **Port-Targeted Chrome Cleanup Bảo Vệ Trình Duyệt Cá Nhân & Lỗi Pipe `Stop-Process` Im Lặng (2026-09-05):** Tuyệt đối không dùng `taskkill /f /im chrome.exe` vì sẽ đóng tất cả các tab trình duyệt cá nhân đang mở của người dùng. Luôn dùng lệnh PowerShell lọc đúng port CDP kết hợp `ForEach-Object`: `Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match "$port" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`. **Pitfall Critical:** Nếu pipe trực tiếp `Get-CimInstance ... | Stop-Process`, `Stop-Process` sẽ bind thuộc tính `.Name = 'chrome.exe'` thay vì PID, gây lỗi `Cannot find a process with the name "chrome.exe"`; khi có cờ `SilentlyContinue`, lỗi bị nuốt âm thầm khiến tiến trình không bao giờ bị dừng! Chi tiết tại `references/google-onboarding-multi-step-and-cim-cleanup-pitfall.md`.
- **Bypass Chuỗi Onboarding Google Đa Bước Qua CDP (2026-09-05):** Khi đăng nhập hoặc xác minh xong, Google chuyển hướng qua: (1) `gds.google.com/web/recoveryoptions` -> Bắt buộc click nút **"Huỷ"** (lưu ý dấu hỏi Unicode `Huỷ`, aria-label `Huỷ`); (2) chuyển tiếp sang `gds.google.com/web/homeaddress` -> Click nút **"Bỏ qua"**; (3) về `myaccount.google.com` -> Click **"Bỏ qua"** trên banner đề xuất; (4) trên hộp thoại 2SV click **"Skip"** và **"Done"** để đóng sạch các modal cản trở tự động hóa. Chi tiết tại `references/google-onboarding-multi-step-and-cim-cleanup-pitfall.md`.
- **Passkey Speedbump vs TOTP Selector Collision & Lỗi Query Parameter URL Callback (2026-09-05):** (1) Tránh dùng selector broad `input[type="tel"]` cho TOTP vì trên trang passkey enrollment (`speedbump/passkeyenrollment`), Google render input tel ẩn khiến script bấm nhầm `#totpNext` và treo timeout 35s — ưu tiên quét dismiss passkey trước, chỉ điền TOTP khi có `input#totpPin` hoặc URL mang chuỗi `totp`; (2) Lỗi substring check `"servicelogin" not in cur_url`: khi Google redirect về `myaccount.google.com/verification/selfie/precollection?next=https://accounts.google.com/ServiceLogin...`, query param chứa chuỗi `ServiceLogin` khiến script tưởng chưa login — bắt buộc dùng `urllib.parse.urlparse` kiểm tra `parsed.path` và `parsed.netloc`; (3) Luôn bọc `page.title()` trong `try/except` và kiểm tra `page.is_closed()` để tránh `TargetClosedError` khi Google redirect giữa chừng. Chi tiết tại `references/google-signin-v3-passkey-and-url-callback-pitfalls.md`.
- **CẤM TUYỆT ĐỐI Dùng `remove_google_prompt_batch.py` Hoặc Đăng Xuất S7 (User Rule 2026-09-05):** Thao tác đăng xuất S7 trên `device-activity` là sai lầm nghiêm trọng làm tê liệt máy S7 của Farm. Bắt buộc giữ nguyên thiết bị S7. Mọi nỗ lực "xóa lời nhắc" bằng cách sign-out thiết bị Farm đều bị cấm triệt để. File runner `remove_google_prompt_batch.py` không được phép sử dụng cho dàn Farm.
- **Quy Tắc Proxy Pairing & Tái Sử Dụng Port Theo Ca (Farm 2-Tier Topology):** Dàn Farm 80 máy dùng chung 38 port USB 4G Mobi (`5101..5138`): Tầng 1 (Máy 01-32) và Tầng 2 (Máy 39-70) cắm chung dải port. Khi login GPM: CẤM login nhiều Gmail trên cùng 1 proxy port trong cùng một batch hoặc cùng một thời điểm (Google sẽ kích hoạt checkpoint Phone SMS do nghi vấn spam IP). Nếu cần nạp máy tầng 2 dùng chung port với máy tầng 1, bắt buộc phải giãn cách theo ca (cách nhau tối thiểu vài tiếng).
- **Circuit Breaker (Ngắt Khẩn Cấp Khi Lỗi Hàng Loạt):** Khi chạy batch đăng nhập / 2FA hàng loạt (max_workers=3, stagger 15s): nếu gặp $\ge 2$ tài khoản liên tiếp bị checkpoint SMS (`challenge/iap`), sai mật khẩu, hoặc lỗi kết nối, BẮT BUỘC script phải DỪNG NGAY LẬP TỨC (Fail-Fast), đóng sạch profile và báo cáo cho user, tuyệt đối cấm chạy tiếp gây chết dây chuyền toàn bộ pool tài khoản.
- **Kẹt Mò Mẫm ADB & Bắt Buộc `acquire_device_lock(force_preempt=True)` Khi S7 Đang Chạy Cron Nuôi Acc (2026-09-05):**
  - **Triệu chứng & Cạm bẫy:** Khi gặp Google Prompt (`challenge/dp`) hoặc Security Code (`challenge/ootp`), subagent worker bị sa lầy 80-110+ turns chạy các lệnh `python -c` rời rạc trong terminal để tap/swipe dò màn hình S7 nhưng vẫn bị kẹt ở Launcher hoặc thư mục ứng dụng.
  - **Nguyên nhân cốt lõi:** Worker không gọi `acquire_device_lock`. Trong lúc đó cron nuôi acc (`run_tiktok.py` / GemPhone) đang chạy nền trên S7, liên tục chiếm lại foreground và cướp màn hình.
  - **Quy tắc bất biến:**
    1. CẤM TUYỆT ĐỐI worker "mò bấm tay" bằng lệnh terminal đơn lẻ. Bắt buộc dùng hàm đóng gói sẵn trong file script.
    2. Mọi tương tác ADB vào S7 BẮT BUỘC bọc trong `acquire_device_lock(machine=..., serial=..., project="gpm-login", bypass_proxy_readiness=True, force_preempt=True)` để tạm dừng cron TikTok. Lấy mã xong phải gửi `keyevent 3` (HOME) rồi mới nhả lock.
    3. Ưu tiên vượt challenge 2 tầng: Tầng 1 chọn Email khôi phục (`thanhdatbui1995@gmail.com`) qua IMAP `read_otp_mail.py` (100% web, không chạm điện thoại); Tầng 2 mới dùng S7 Security Code bọc trong Device Lock.
    4. Chi tiết tại `references/s7-device-lock-and-cron-preemption-discipline.md`.
- **Ba Cơ Chế Tự Động Vượt Challenge Google Sign-in & Quy Chuẩn Recovery Mail OTP (2026-09-05):** Khi Google yêu cầu xác minh bảo mật lúc login trên GPM:
  1. **Cơ chế 1 — IMAP Recovery Email OTP (`thanhdatbui1995@gmail.com`):** Dùng `fetch_latest_otp` từ `D:\Taadaa\add mail khoi phuc\read_otp_mail.py` với app password lưu trong Windows Registry/Env (`OTP_MAIL_APP_PASSWORD`). Khi gặp `challenge/selection`, click chọn mục *"Nhận mã xác minh tại email khôi phục"* $\rightarrow$ poll IMAP Gmail lấy OTP 6 số $\rightarrow$ điền vào ô pin để vượt qua.
  2. **Cơ chế 2 — S7 Security Code 10 Số Qua ADB (`GoogleSettingsLink`):** Khi gặp `challenge/ootp` hoặc Google Prompt `challenge/dp` (bấm *"Thử cách khác"*), kết nối ADB vào máy S7 tương ứng: khởi động intent `com.google.android.gms/.app.settings.GoogleSettingsLink`, chuyển tài khoản mục tiêu $\rightarrow$ *Tài khoản Google* $\rightarrow$ *Bảo mật và đăng nhập* $\rightarrow$ *Mã bảo mật* để trích xuất 2 mã 10 số (hiệu lực 15 phút). Nhập mã vào Chrome để vượt qua.
  3. **Cơ chế 3 — ADB Duyệt Trực Tiếp Google Prompt Trên S7 ("Có, Tôi Là Người Thực Hiện"):** Khi gặp `challenge/dp`, đánh thức S7 qua ADB, mở notification / dialog của Google Play Services, quét ATX Agent tìm và tap nút *"Có, tôi là người thực hiện"* (hoặc số khớp trên màn hình PC) để S7 duyệt phiên trực tiếp.
  4. **Quy tắc bảo vệ S7 bất biến:** Sau khi vào tài khoản, kích hoạt ngay 2FA Authenticator TOTP và lưu Secret Key vào Excel. **TUYỆT ĐỐI CẤM** vào `device-activity` đăng xuất thiết bị S7. Chi tiết tại `references/google-prompt-s7-preservation-and-challenge-recovery.md`.
- **Phân Loại Google Sign-in Challenges (`challenge/ootp`, `challenge/dp`, `challenge/selection`) & Kỷ Luật Circuit Breaker (2026-09-05):** Khi chạy batch tự động tài khoản cũ trên GPM, Google phân nhánh bảo mật: (1) `challenge/selection`: Màn hình menu chọn hình thức xác minh $\rightarrow$ bắt buộc click đúng node `li` / `div[data-challengetype="12"]` (Recovery Email) hoặc `div[data-challengetype="6"]` (Authenticator) trước khi tìm ô input tiếp theo; (2) `challenge/ootp`: Google yêu cầu mã bảo mật Offline OTP 10 số từ Android Settings của Samsung S7; (3) `challenge/dp`: Google gửi Device Prompt đẩy đến Samsung S7. Khi gặp $\ge 3$ tài khoản liên tiếp bị challenge/checkpoint, kịch bản kích hoạt Circuit Breaker dừng khẩn cấp ngay để bảo vệ toàn pool tài khoản và giữ nguyên trạng thái S7. Script mẫu chuẩn: `D:\Taadaa\GPM auto\scripts\run_batch_12_untouched_proxies.py`. Chi tiết tại `references/proxy-pairing-and-batch-circuit-breaker.md`.
- **Credential Fallback Khi Pass Bị Đổi (2026-09-05):** Khi Google báo `Your password was changed X days ago`, luôn quét đối chiếu cột Password giữa `Master_All`, `Gmail_Dat` và `Clean_V2` để truyền mảng mật khẩu dự phòng `pwd = ["N0spam@@", "old_pwd@Ks"]`. Sau khi xác thực thành công, tự động cập nhật lại password mới nhất vào cả hai file Excel.
- **Port Dynamic Resolution & Backward-Compatible API Signatures in `gpm_client.py` (2026-09-05):**
  - Tránh hardcode đường dẫn username (`C:\Users\Kibe\...`): Dùng `os.environ.get("LOCALAPPDATA")` kết hợp `Path.home() / "AppData" / "Local" / "Programs" / "GPMLogin" / "api_port.dat"`, ghi `logger.warning("Không tìm thấy api_port.dat, fallback về port 19995")` khi không đọc được file.
  - Backward compatibility cho caller cũ/mới: `create_profile` hỗ trợ đồng thời cả `browser_name` và `browser_type`, `group_id: Any = 1`, `note`; `start_profile` giữ lại toàn bộ các tham số cũ `skip_proxy_check=False, window_size=None, window_pos=None, remote_debugging_port=None, addition_args=None` (tránh `TypeError: unexpected keyword argument 'skip_proxy_check'`); `delete_profile` giữ mặc định `mode=1`.
  - `cdp_auth.py` graceful import: Bắt buộc wrap `playwright.sync_api` trong `try/except ImportError` (`sync_playwright = None`, `Page = Any`, `PlaywrightTimeoutError = Exception`) để module import an toàn trên mọi runtime; hỗ trợ cả `cdp_endpoint` và `ws_url` (`endpoint = ws_url if ws_url is not None else cdp_endpoint`).
  - Unit test Playwright CDP: Mock `time.sleep` bằng autouse fixture để test chạy trong 0.3-0.9s thay vì sleep hàng chục giây; cover các case `login_google_on_page` (already logged in, success, checkpoint, email not found) và test ném `ImportError` khi thiếu playwright.
  - Tránh quét đệ quy `grep`/`find` trên root repo `GPM auto`: Thư mục `checkmail_browser_data` chứa hàng trăm nghìn file cache Chromium gây nghẽn I/O và treo timeout 900s; luôn giới hạn quét cụ thể trên các thư mục code `src/`, `tests/`, `scripts/`.
- **WebSocket CDP 403 Forbidden Handshake Fix (`suppress_origin=True` — 2026-09-05):** Khi kết nối trực tiếp vào `webSocketDebuggerUrl` của Chrome Core 142 qua thư viện Python `websocket-client`, Chrome từ chối kết nối với lỗi 403 (`Rejected an incoming WebSocket connection from origin... Use flag --remote-allow-origins`). Khắc phục: truyền `suppress_origin=True` trong `websocket.create_connection(url, suppress_origin=True)` để Chrome cho phép kết nối ngay lập tức mà không cần sửa cờ khởi động của GPM.
- **Tự động đóng Popup "Khôi phục trang" (Restore Pages Bubble) bằng Win32 `WM_CLOSE` (2026-09-05):** Khi profile mở lại sau khi từng bị tắt đột ngột, Chrome thường bật popup con `"Bạn có muốn khôi phục trang không?"` che mất góc nhìn. Dùng `ctypes.windll.user32.PostMessageW(bubble_hwnd, 0x0010, 0, 0)` (với `0x0010 = WM_CLOSE`) để đóng sạch popup này trong background mà không ảnh hưởng cửa sổ chính.
- **Workflow Mở Profile Sẵn Cho User Nâng Gói / Thanh Toán (Gemini Pro / Google One — 2026-09-05):** Khi user yêu cầu mở profile để thao tác thanh toán/nâng cấp gói thủ công: Tuyệt đối KHÔNG gọi `stop_profile` hay đóng context; kiểm tra egress IP trên tab qua `api64.ipify.org` trước; kích hoạt tab `https://gemini.google.com/app` hoặc `https://one.google.com/ai`; sẵn sàng trích xuất password và Secret 2FA TOTP từ `master_gmail_manager.xlsx` để user bypass màn hình xác minh danh tính nhạy cảm của Google One.
- **Kỷ Luật Tích Hợp IMAP Recovery OTP & Preemptive S7 Security Code (2026-09-05):** CẤM TUYỆT ĐỐI chạy lệnh `python -c` mò mẫm toạ độ ADB trên terminal; tái sử dụng trực tiếp hàm chuẩn `get_s7_security_code` từ `run_batch_login_6machines.py`. Khóa máy bắt buộc bằng `acquire_device_lock(machine=str(mid), serial=serial, project="gpm-login", bypass_proxy_readiness=True, force_preempt=True)` để tạm dừng cron nuôi acc tranh chấp màn hình và gửi `keyevent 3` (HOME) trong `finally` trước khi nhả lock. Khi gặp `challenge/selection`, ưu tiên chọn gửi mã về recovery mail `thanhdatbui1995@gmail.com` rồi poll IMAP qua `fetch_latest_otp` (loại bỏ subject "Cảnh báo bảo mật" và tính dynamic timestamp lookback để tránh bắt nhầm mã rác) giúp vượt challenge nhanh gấp 10 lần và hoạt động được ngay cả khi máy S7 bị mất kết nối ADB (như Máy 30). Chi tiết tại `references/imap-recovery-otp-and-s7-preemption-discipline.md`.
- **Bẫy Nhận Diện Text Google Prompt `challenge/dp` vs Kích Hoạt "Thử cách khác" & Toạ Độ S7 Landscape (2026-09-05):**
  - **Bẫy text keyword:** Khi Google hiện Google Prompt, tiêu đề thường là `"Xác minh danh tính của bạn Để giữ an toàn..."` và trong body hoàn toàn KHÔNG chứa cụm từ `"kiểm tra điện thoại"` hay `"tap yes"`. Nếu script chỉ dựa vào text check sẽ bị miss 100%, kẹt loop và kích hoạt Circuit Breaker dừng batch oan.
  - **Quy tắc bắt buộc:** Bắt trực tiếp theo URL `"challenge/dp" in page.url.lower()` hoặc selector nút `"Thử cách khác"` / `"Try another way"`. Tự động bấm ngay nút này để chuyển hướng sang `challenge/selection` (chọn Recovery Email OTP hoặc S7 Security Code).
  - **Toạ độ vuốt S7 Landscape:** Thiết bị Samsung S7 trên farm thường ở orientation ngang (`width=1920, height=1080`). Khởi chạy trực tiếp intent `com.google.android.gms/.app.settings.GoogleSettingsLink` để vào thẳng menu *"Bảo mật và đăng nhập"*; sau đó thực hiện lệnh vuốt `input swipe 960 800 960 300` để cuộn xuống mở ngay mục *"Mã bảo mật"*. Chi tiết tại `references/google-prompt-s7-preservation-and-challenge-recovery.md`.
- **Google Video Selfie Speedbump `<a ...>Để sau</a>` & Tách Lỗi Hạ Tầng Proxy Trong Circuit Breaker (2026-09-05):**
  - **Bẫy thẻ `<a>` trên nút "Để sau" / "Bỏ qua":** Khi submit password thành công, Google chuyển hướng sang màn hình onboarding / speedbump *"Bảo vệ quyền truy cập bằng video selfie"* (`gds.google.com` hoặc `challenge/pwd`). Nút *"Để sau"* render dưới dạng thẻ `<a>` (`<a class="WpHeLc ..."><span ...>Để sau</span></a>`), không phải thẻ `<button>`. Bộ chọn cũ `button:has-text("Để sau")` fail 100% làm script kẹt chờ và báo sai login FAILED. Khắc phục: Mở rộng `dismiss_selectors` và `agree_selectors` quét đồng thời thẻ `a`, `button`, `span`.
  - **Phân tách `PROXY_ERROR` trong Circuit Breaker:** Khi GPM start profile fail do modem/proxy 4G rớt mạng (`{'message': 'Không thể kết nối tới proxy'}`), gán status `PROXY_ERROR` và TUYỆT ĐỐI KHÔNG tăng biến đếm `consecutive_failures`. Chỉ tăng biến đếm khi gặp lỗi từ phía Google (`CHECKPOINT`, `DIE`, `FAILED`) để tránh ngắt khẩn cấp toàn batch oan.
  - **Selector `challenge/selection`:** Các dòng lựa chọn phương thức xác minh là thẻ `li` hoặc `[role="link"]`. Dùng `li:has-text("email khôi phục"), div[data-challengetype="12"]` và `li:has-text("mã bảo mật"), div[data-challengetype="8"]`.
  - Chi tiết tại `references/google-signin-video-selfie-anchor-and-proxy-circuit-breaker.md`.
- **Bẫy Vòng Lặp "Thử Cách Khác" Do Từ Khoá "Xác Minh Danh Tính" & Re-Auth 2SV Authenticator (2026-09-05):**
  - **Bẫy Vòng Lặp Vô Tận trên `challenge/ootp`:** Tiêu đề trang Google challenge luôn chứa `"Xác minh danh tính của bạn"`. Nếu điều kiện bấm *"Thử cách khác"* (`Try another way`) chứa cụm từ này, khi trang đã vào `challenge/ootp` (nhập mã 10 số S7), script lại thấy nút *"Thử cách khác"* ở chân trang và tự click $\rightarrow$ quay ngược lại `challenge/selection` $\rightarrow$ tạo thành vòng lặp vô tận 15 bước. Khắc phục: (1) Bỏ hoàn toàn `"xác minh danh tính"` khỏi điều kiện bấm *"Thử cách khác"*, chỉ bấm khi URL là `challenge/dp` hoặc body chứa prompt điện thoại; (2) Quét và điền ô nhập mã (`code_inp` / `challenge/ootp`) TRƯỚC khối xử lý *"Thử cách khác"*.
  - **Re-Auth `challenge/dp` Khi Bật 2SV Authenticator & Fallback IMAP Khi ADB Socket Lag (2026-09-05):**
    - Khi vào `two-step-verification/authenticator`, Google thường bắt re-authenticate danh tính qua Google Prompt (`challenge/dp`). Nếu hàm chỉ kiểm tra `challenge/pwd` và reCAPTCHA, trang sẽ kẹt tại màn hình prompt và báo lỗi sai `UNKNOWN_UI` (như case M33).
    - Hàm thiết lập Authenticator BẮT BUỘC phải xử lý cả nhánh `challenge/dp`: bấm *"Thử cách khác"* (`Try another way`) $\rightarrow$ điều hướng vào `challenge/selection`.
    - Trên `challenge/selection`: Ưu tiên hàng đầu là click *"Nhận mã xác minh tại email khôi phục"* (`div[data-challengetype="12"]`) nếu `recovery` là `thanhdatbui1995@gmail.com` rồi poll OTP IMAP qua `fetch_latest_otp`. Việc này giúp bypass 100% qua web mà không chạm vào điện thoại S7, đặc biệt giải cứu được các máy S7 bị lag adb socket / timeout lệnh `adb shell` (như M33 serial `ce0616061a74682305`). Chỉ fallback sang ADB S7 Security Code khi không có IMAP recovery.
    - **Lỗi UnicodeEncodeError Trong IMAP Search Của Python `imaplib` (2026-09-05):** Thư viện chuẩn `imaplib` trong Python mã hóa chuỗi command search bằng ASCII mặc định. Việc truyền chuỗi Unicode tiếng Việt có dấu trực tiếp vào `imap.search()` (ví dụ `'SUBJECT', 'xác minh'`) sẽ gây crash ngay lập tức với lỗi `UnicodeEncodeError: 'ascii' codec can't encode character ...`. Khắc phục chuẩn: BẮT BUỘC chỉ search bằng tiêu chí ASCII an toàn như `SINCE <date>` hoặc `(FROM "accounts.google.com")`, sau đó decode MIME header và filter tiếng Việt bằng Python regex trong bộ nhớ.
  - **Kỷ Luật Dữ Liệu Excel — CẤM Ghi Chú Skip Vào Cột Nghiệp Vụ & Bỏ Qua 100% Tài Khoản Khoalee (User Invariant 2026-09-05):**
    - **BỎ QUA 100% GMAIL KHOALEE:** Khi chạy batch đăng nhập / 2FA trên GPM hoặc bất kỳ quy trình nuôi/login farm, nếu tài khoản có recovery email là `khoaleemagic@gmail.com` (hoặc mang định danh khoalee), **BỎ QUA 100%, TUYỆT ĐỐI KHÔNG KHỞI CHẠY GPM PROFILE, KHÔNG GÁN PROXY VÀ KHÔNG ĐĂNG NHẬP**.
    - **CẤM ghi đè vào Excel:** Khi lọc bỏ tài khoản cần bỏ qua, TUYỆT ĐỐI KHÔNG ghi đè chuỗi trạng thái (như `SKIPPED_KHOALEE`, `SKIP`) vào các cột nghiệp vụ như Cột F (SDT), Cột C (Password) hay Cột D (Recovery Email).
    - Bộ lọc bỏ qua BẮT BUỘC nằm 100% trong logic runtime của Python script (`if 'khoalee' in str(rec_email).lower(): continue`). Giữ nguyên 100% schema và dữ liệu người dùng trong `master_gmail_manager.xlsx`.
  - **Cơ Chế "Recent Fresh Auth" vs "Stale Auth" Khi Setup 2SV Authenticator (2026-09-05):**
    - Khi tài khoản vừa hoàn tất login tươi bằng mật khẩu trong vòng 1-2 phút (như case M55, M58, M59), Google cấp elevated trust cho session. Khi điều hướng ngay sang `two-step-verification/authenticator`, Google KHÔNG yêu cầu xác thực lại (`challenge/dp`), hiển thị ngay nút *"Thiết lập ứng dụng xác thực"* $\rightarrow$ kích hoạt 2FA thành công 100% chỉ trong vài giây.
    - Ngược lại, nếu tài khoản sử dụng lại profile cũ đã đăng nhập từ lâu (auth session đã nguội như case M33), Google kích hoạt re-auth `challenge/dp` và gây khó khăn khi vượt challenge. Vì vậy, với tài khoản chưa có 2FA, ưu tiên thực hiện luồng Login mới $\rightarrow$ Chuyển thẳng sang bật 2FA ngay trong cùng một lượt.
  - **Bẫy Onboarding `gds.google.com/web/recoveryoptions` & Selector Nút Cancel (2026-09-05):**
    - Khi submit password hoặc recovery email, Google chuyển hướng qua `https://gds.google.com/web/recoveryoptions?cardIndex=0...` hiển thị form "Account Recovery Options" với các nút `Learn more`, `Cancel`, `Save`.
    - Script không được treo chờ hay click Save gây đòi OTP; bắt buộc click nút `Cancel` / `Huỷ` để thoát onboarding và điều hướng vào live session `myaccount.google.com`.
    - Selector bắt buộc: `page.locator('button:has-text("Cancel"), a:has-text("Cancel"), button:has-text("Hủy"), button:has-text("Huỷ")')`.
  - **Đánh thức màn hình S7 tránh tắt máy (`keyevent 82` vs `26`):** `keyevent 26` là nút nguồn toggle, nếu màn hình đang sáng sẽ tắt và khóa máy. Dùng `keyevent 82` (Unlock) kết hợp vuốt để mở khóa an toàn vào intent `GoogleSettingsLink`.
  - **Nhận diện `challenge/ipe/verify` & `challenge/kpe` và Kỷ luật Giữ Profile LIVE (2026-09-05):**
    - `challenge/ipe/verify`: Màn hình xác minh danh tính mã bảo mật mới của Google (tương tự `ootp`). Nếu nhập mã không khớp nhiều lần, Google redirect về `https://www.google.com/account/about` (tín hiệu kết thúc flow login FAILED).
    - `challenge/kpe`: Nhập email khôi phục xác nhận (`input#knowledge-preregistered-email-response`) cho tỷ lệ vượt challenge 100% mà không cần chạm vào điện thoại S7.
    - Kỷ luật giữ Profile: Khi tài khoản đã đạt `myaccount.google.com` (login sống) nhưng khi điều hướng vào cài Authenticator 2SV vướng re-auth challenge chưa bật được 2FA, BẮT BUỘC đánh dấu `2FA_FAILED` nhưng giữ nguyên profile GPM và cập nhật `Status=LIVE, 2FA=False` vào Excel. TUYỆT ĐỐI KHÔNG xóa profile tài khoản đã login sống.
  - **Selector "Thử Cách Khác" Rộng & Fallback IMAP Khi S7 Security Code Thất Bại Trên `challenge/ootp` (2026-09-05):**
    - **Bẫy thẻ `div[role="button"]` / `span` trên nút "Thử cách khác" (Google Prompt `challenge/dp`):** Khi Google bắt xác minh lại lúc cài Authenticator 2SV (`challenge/dp`), nút *"Thử cách khác"* (`Try another way`) không render dạng `button` hay `a` đơn thuần mà là `div[role="button"]` hoặc `span`. Nếu chỉ dùng selector `button:has-text(...)` và `a:has-text(...)`, Playwright không tìm thấy nút (`count = 0`), khiến script lặp 15 bước không click được và fail `UNKNOWN_UI` (case Máy 33). Khắc phục: Mở rộng selector: `button:has-text("Thử cách khác"), button:has-text("Try another way"), a:has-text("Thử cách khác"), a:has-text("Try another way"), div[role="button"]:has-text("Thử cách khác"), div[role="button"]:has-text("Try another way"), span:has-text("Thử cách khác"), span:has-text("Try another way")`.
    - **Bẫy Treo 250s Trên `challenge/ootp` Khi S7 Không Lấy Được Mã & Thiếu Fallback:** Khi Google yêu cầu mã bảo mật thiết bị S7 (`challenge/ootp`), script gọi `get_s7_security_code`. Nếu S7 bị lag adb, khóa màn hình hoặc không lấy được mã (`s7_c is None`), script KHÔNG ĐƯỢC lặp lại việc gọi ADB ở các step tiếp theo (mỗi lần gọi tốn ~25s $\times$ 10-15 steps = 250-375s làm timeout lệnh batch 600s, như case Máy 61 chặn Máy 64). Khắc phục chuẩn: Giới hạn thử S7 tối đa 1-2 lần; nếu không lấy được mã, BẮT BUỘC bấm ngay *"Thử cách khác"* (`Try another way`) trên trang `challenge/ootp` để Google chuyển sang `challenge/selection`, rồi chọn Recovery Email OTP (`thanhdatbui1995@gmail.com`) qua IMAP để bypass 100% qua web.
  - **Tái Sử Dụng GPM Profile Đã Live Session & Đa Dạng Thẻ Nút "Thiết lập ứng dụng xác thực" (2026-09-05):**
    - **Tái sử dụng profile khi re-run 2FA:** Khi tài khoản đã đạt trạng thái LIVE nhưng chưa kích hoạt được 2FA (status `2FA_FAILED`), profile GPM mang session đăng nhập vẫn tồn tại trong GPM. Khi chạy lại, BẮT BUỘC kiểm tra profile đã tồn tại qua `GET /api/v3/profiles` theo tên chuẩn `f"{machine:02d} - {email} - {port}"` và khởi chạy trực tiếp ID cũ thay vì gọi `create_profile` tạo profile rỗng mới, giúp giữ nguyên cookie session và không phải đăng nhập lại từ đầu.
    - **Selector nút "Thiết lập ứng dụng xác thực":** Trên trang `two-step-verification/authenticator`, Google render nút thiết lập dưới dạng `button`, `div[role="button"]`, hoặc thẻ `a`. Bắt buộc dùng selector tổng quát: `page.locator('button, div[role="button"], a').filter(has_text=re.compile(r"(thiết lập|set up|thêm ứng dụng|add authenticator)", re.IGNORECASE))` để tránh rơi vào nhánh `UNKNOWN_UI`.
    - **Quản lý timeout ADB socket:** Khi chạy lệnh `adb shell`, luôn bọc timeout cụ thể (VD `timeout 5` hoặc Python `timeout=5`), tránh pipe sang tool grep trong shell không có timeout gây treo vĩnh viễn tiến trình khi socket thiết bị bận.
  - Chi tiết tại `references/google-signin-ootp-try-another-way-loop-fix.md` và `references/challenge-ootp-loop-and-authenticator-reauth-pitfalls.md`.
- **Lợi Thế "Recent Fresh Auth" vs "Stale Auth" & Kỷ Luật Điều Phối Worker Batch (2026-09-05):**
  - **Fresh Auth Elevation:** Khi vừa đăng nhập mật khẩu thành công trong vòng 1-2 phút, chuyển hướng ngay sang `two-step-verification/authenticator` sẽ được Google cấp elevated trust, bỏ qua 100% Google Prompt `challenge/dp` và Security Code, bật 2FA thành công trong vài giây (M55, M58, M59, M64, M68). Tránh dùng profile cũ đã login từ lâu vì luôn dính re-auth.
  - **Kỷ luật Worker Dispatch 3 bước:** Coordinator khi dispatch worker chạy batch bắt buộc đưa sẵn đoạn mã patcher và chỉ định đúng 3 bước: `write_file patcher -> py_compile -> chạy script batch -> báo cáo Excel`. Cấm giao prompt thăm dò/mở khiến worker đốt 35 turns đọc file và kiểm tra lặp. Chi tiết tại `references/fresh-auth-elevation-and-worker-dispatch.md`.
- **Google OAuth Account Chooser Selector Collision với Header Consent & ProfilePath Query (2026-09-05):**
  - **Account Chooser Header Collision:** Khi tự động hóa OAuth Antigravity (`add_oauth_omniroute.py`), selector `div[data-identifier="{email}"], div:has-text("{email}")` dùng `div:has-text` quá rộng. Khi Google chuyển sang màn hình Consent, email xuất hiện ở header chip (`<div>`), script liên tục click vào header và `continue`, gây kẹt lặp lại không bao giờ bấm được nút Consent (Tiếp tục/Allow) dẫn tới timeout 45s. Khắc phục: loại bỏ `div:has-text("{email}")`, chỉ dùng `div[data-identifier="{email}"]` và ưu tiên quét nút Consent trước.
  - **Khớp Profile GPM theo ProfilePath:** Trong SQLite `profile_data.db`, mã hash như `OaQGVGQ0XU-05092026` nằm ở cột `ProfilePath`, không phải `Name` hay `Id`. Lọc profile bắt buộc đối soát `target in p['profile_path'].lower()`.
  - Chi tiết tại `references/google-oauth-account-chooser-and-profilepath-pitfalls.md`.
- **Bypass 2FA TOTP Tự Động & Decouple Google Prompt Khi Add OAuth Antigravity (2026-09-05):**
  - Khi app gọi OAuth cấp quyền Antigravity, Google kích hoạt Google Prompt (`challenge/dp`) đẩy về Samsung S7.
  - **Nguyên nhân canary kẹt:** Điều kiện `if "challenge" in current_url: break` coi `challenge/dp` là checkpoint không giải quyết được và ngắt sớm.
  - **Chuẩn hóa luồng bypass & Selector "Cách xác minh khác":**
    1. `CredentialLookup` nạp `totp_secret` từ cột 5 (`master_gmail_manager.xlsx`) và cột 4 (`gmail_clean_v2.xlsx`).
    2. Thứ tự selector Playwright: BẮT BUỘC kiểm tra và điền mã vào ô `input#totpPin` TRƯỚC nút "Thử cách khác" / "Cách xác minh khác" (tránh click nhầm link ở chân trang TOTP làm văng ngược về selection).
    3. Chống lệch chu kỳ TOTP 30s: nếu `time.time() % 30 >= 28` thì `time.sleep(3)` trước khi sinh mã `pyotp.TOTP.now()`.
    4. Màn hình Google Prompt (`challenge/dp`): Google đã đổi text từ "Thử cách khác" sang **"Cách xác minh khác"** (hoặc "More ways to verify"). Selector bắt buộc quét cả button, div[role="button"], a, span cho cả hai cụm từ.
    5. Màn hình chọn phương thức (`challenge/selection`): Selector `auth_opt` mở rộng `div[data-challengetype="6"], li:has-text("xác thực"), div[role="link"]:has-text("xác thực"), div[role="button"]:has-text("xác thực"), div:has-text("Google Authenticator")`.
    6. **Điều kiện tiên quyết (Preflight Gate):** Tài khoản BẮT BUỘC phải được bật 2FA Google Authenticator từ trước. Nếu tài khoản chưa bật 2FA Authenticator, màn hình `selection` CHỈ hiển thị 2 tùy chọn: (1) Prompt trên điện thoại; (2) Mã bảo mật 10 số (hoàn toàn không có tùy chọn Authenticator), dẫn đến timeout.
    7. Tăng default timeout lên 60s và tự động gán Proxy 1:1 theo port + sync-models sau exchange.
  - Chi tiết tại `references/omniroute-oauth-totp-bypass-and-prompt-handling.md`.
- **Xóa Dữ Liệu Tách Biệt Theo Domain (Surgical Site Cache Clearing) & Codex OAuth OmniRoute (2026-09-05):** Khi tài khoản dịch vụ AI bên thứ ba (như ChatGPT/OpenAI) bị vô hiệu hóa (`account_deactivated`), CẤM xóa toàn bộ profile hay clear all browser data vì sẽ làm mất session Google/Gmail quý giá. Dùng kỹ thuật SQLite offline: xóa chọn lọc trong `Default/Network/Cookies` (`DELETE FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%'`) và `Default/Login Data`, xóa folder IndexedDB của domain đó. Giữ nguyên 100% cookies Google (đã kiểm chứng 75/75 cookies nguyên vẹn, `myaccount.google.com` sống). Giữ nguyên fingerprint GPM để bảo vệ session Gmail và vượt Cloudflare Turnstile khi reg lại tài khoản mới. Chi tiết tại `references/surgical-site-cache-clearing-and-codex-oauth.md`.
- **Lỗi `[Errno 13] Permission Denied` Khóa File Cookie Khi Nén Backup Profile GPM (2026-09-05):**
  - **Triệu chứng:** Khi chạy script nén zip các thư mục profile GPM, `zipfile` ném lỗi `[Errno 13] Permission denied` trên các file `lockfile`, `Default\Network\Cookies`, `Default\Sessions\...`, `ShaderCache` khiến file cookie/session bị bỏ qua hoặc bản backup bị lỗi.
  - **Nguyên nhân:** Có một hoặc nhiều tiến trình Chrome của GPM (`gpm_browser`) vẫn đang chạy ngầm / mồ côi (chưa thoát sạch hoặc bị kẹt) đang giữ lock độc quyền trên các file SQLite và LevelDB của profile đó.
  - **Giải pháp bắt buộc:** Trước khi nén, luôn quét và kill sạch các tiến trình Chrome thuộc GPM bằng lệnh PowerShell:
    ```powershell
    Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match 'gpm_browser' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    ```
    Lệnh này chỉ đóng đúng các browser của GPMLogin, hoàn toàn không chạm vào Chrome cá nhân của người dùng, giúp giải phóng toàn bộ file lock tức thì và đảm bảo 100% dữ liệu cookie được nén an toàn. Chi tiết tại `references/gpm-profile-backup-and-lockfile-cleanup.md`.
- **Google OAuth Antigravity Device Privilege Gate & Nút "Cách xác minh khác" (2026-09-05):**
  - **Đổi nhãn nút:** Google đổi text từ *"Thử cách khác"* (`Try another way`) sang *"Cách xác minh khác"* (`More ways to verify`). Bộ chọn Playwright bắt buộc quét cả: `button:has-text("Cách xác minh khác"), button:has-text("Thử cách khác"), div[role="button"]:has-text("Cách xác minh khác"), a:has-text("Cách xác minh khác")`.
  - **Khóa thiết bị vật lý trên luồng OAuth Developer:** Khi tài khoản cấp quyền Antigravity (Google Cloud Developer), Google ưu tiên thiết bị Android vật lý (Galaxy S7). Trên màn hình `challenge/selection`, Google chỉ cung cấp: (1) Prompt tap số trên điện thoại; (2) Mã bảo mật ngoại tuyến 10 số (không hiển thị tùy chọn Authenticator TOTP 6 số như khi đăng nhập web thông thường).
  - **Bẫy nhầm lẫn input `name="Pin"`:** Trên `challenge/ootp` (mã 10 số), input mang thuộc tính `name="Pin" type="tel"`. Script tuyệt đối KHÔNG được nhận nhầm là ô TOTP 6 số (sẽ bị từ chối gây kẹt vòng lặp timeout). Bắt buộc phải duyệt trên máy Galaxy S7 tương ứng hoặc lấy mã 10 số từ intent `GoogleSettingsLink`. Chi tiết tại `references/omniroute-antigravity-oauth-gpm-flow.md` và `references/s7-security-code-oauth-integration-discipline.md`.
- **Tự động hóa Lấy S7 Security Code Qua Device Lock Trong OAuth Flow (2026-09-05):**
  - **Khóa thiết bị an toàn:** Khi lấy mã từ S7 qua ADB, bắt buộc dùng `acquire_device_lock(machine=str(mid), serial=serial, project="gpm-login", bypass_proxy_readiness=True, force_preempt=True)`.
  - **Đánh thức & Mở khóa:** Dùng `input keyevent KEYCODE_WAKEUP` và `wm dismiss-keyguard` trước khi khởi động `GoogleSettingsLink` để tránh kẹt màn hình tắt/khóa.
  - **Chuyển Account trên UI Google Play Services mới:** Khi mở `GoogleSettingsLink`, avatar/email đang chọn ở header. Nếu khác `target_email`, click vào avatar/email `[60,758][204,902]` để mở popup account chooser -> chọn `target_email` -> click **"Tài khoản Google"** -> chọn tab **"Bảo mật"** -> click **"Mã bảo mật"** -> regex trích xuất 10 số. Trong `finally`, gửi `input keyevent 3` (HOME) trước khi nhả lock. Chi tiết tại `references/s7-security-code-oauth-integration-discipline.md`.

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
