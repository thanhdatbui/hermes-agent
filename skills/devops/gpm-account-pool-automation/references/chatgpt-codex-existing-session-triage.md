# ChatGPT/Codex Existing-Session Triage

## User-correction gates

- OAuth Codex yêu cầu session ChatGPT sống. Khi gặp profile bị văng session (OpenAI redirect về `auth.openai.com/log-in`), BẮT BUỘC chạy quy trình Auto-Relogin tự động bằng credentials chính chủ (PASS CHATGPT từ Cột 12 workbook hoặc nhận mã OTP 6 số qua Microsoft Graph API Hotmail). CẤM TUYỆT ĐỐI dừng sớm hoặc báo BLOCKED khi chưa chạy auto-relogin.
- CẤM dùng Google SSO (`Continue with Google`), đoán pass mò, hoặc tạo tài khoản mới đè lên.
- Filter OmniRoute by provider: `chatgpt-web` and `codex` are separate. Exclude any ChatGPT account that already has an active `provider=codex` connection.
- A provider row or account picker is not proof of login. Fresh UI evidence must show no Login/Sign-up controls and must show account identity/package.

## Evidence classification

- `chatgpt-web` 403 + `Sentinel/Turnstile required` proves a provider block, not permanent deletion.
- OpenAI UI saying account deleted/disabled is stronger account-state evidence, but do not map it to an email unless the screenshot/log identifies the account.
- Never claim spam without request-level history: timestamp, count/rate, concurrency, retries/fallback, proxy/IP/session-affinity, and status code. Empty or retired access logs mean the cause is unproven.
- Separate `confirmed`, `plausible`, and `unknown` findings.

## Codex pool diagnosis

Quota is not capacity. Read `/api/providers`, `/api/resilience`, and `/api/health` together. Classify active usable targets vs inactive/expired/banned targets; global concurrency, queue depth, cooldown and breaker state; runtime health and watchdog restart window; and direct route/combo targets rather than aggregate historical usage. Historical aggregate usage cannot prove current quota or capacity. Do not diagnose a Codex failure from ChatGPT-Web inventory. Distinguish process interruption (which can break streams) from provider/auth/capacity errors.

## OmniRoute restart and proxy evidence

A watchdog restart proves repeated health failure, not the root cause. Read the exact failure window and runtime stderr/app log; unrelated `adb.exe` crashes are not OmniRoute evidence. When direct-IP fallback is disabled, verify both persisted flags and runtime reload after controlled restart; health 200 alone does not prove effective environment variables.

## GPM teardown and parallel inspection

Always close Playwright contexts/browser before the exact GPM stop endpoint. Only report `GPM_STOPPED` after checking the stop response. Never kill arbitrary Chrome/GPM processes. For parallel profile checks, assign one worker/owner per profile, detect races, capture fresh screenshots before teardown, and stop only the owned profile.

## Automated Codex OAuth Execution via GPM & OmniRoute

### Flow Architecture
1. **Start Callback Server**: Call `GET http://localhost:20129/api/oauth/codex/start-callback-server` -> retrieves `authUrl` and binds local listener on port `1455`.
2. **Launch GPM Profile**: Call GPM API `start/{profile_id}` -> connect Playwright over CDP debugging port.
3. **Navigate to `authUrl`**:
   - Intercept requests matching `1455` or `code=` to forward directly to `http://127.0.0.1:1455/auth/callback`.
4. **Handle Account Chooser (`choose-an-account`)**:
   - URL: `https://auth.openai.com/choose-an-account` or Title: `Welcome back - OpenAI`.
   - **CRITICAL SELECTOR PITFALL**: DO NOT click `div:has-text('<email>')` as it matches non-interactive parent containers and fails silently. MUST click interactive elements: `button:has-text('<email>'), [role='button']:has-text('<email>'), a:has-text('<email>')` with `force=True`.
5. **Handle Consent Screen (`sign-in-with-chatgpt/codex/consent`)**:
   - URL contains `/sign-in-with-chatgpt/codex/consent`.
   - **BUTTON PITFALL**: The action button on the consent page is labeled **"Continue"** or **"Tiếp tục"** (NOT just "Authorize"). Selector must include: `button:has-text("Continue"), button:has-text("Tiếp tục"), button:has-text("Authorize")`. Missing "Continue" causes 120s timeout on an already-authenticated profile.
6. **Handle "Session Expired" Screen**:
   - Title contains *Phiên của bạn đã kết thúc* / *Session expired*.
   - Click `button:has-text('Đăng nhập')` or `button:has-text('Log in')` to proceed to the credentials form.
7. **Polling Callback**: Poll `POST http://localhost:20129/api/oauth/codex/poll-callback` every 3s until `success: true` and `connectionId` returned.
8. **Teardown**: Always close Playwright page/browser and call GPM `stop/{profile_id}` in `finally`.

### Singleton PKCE Port 1455 & Sequential Lock (FIFO)
- **Cơ chế Singleton**: OmniRoute (`:20129`) mở callback server PKCE tại cổng cố định `http://localhost:1455/auth/callback` và lưu trạng thái duy nhất trong bộ nhớ (`globalThis.__pkceCallbackStates["codex"]`).
- **Bắt buộc tuần tự (FIFO)**: Khâu kích hoạt Codex OAuth và ver số bắt buộc phải chạy tuần tự qua khóa độc quyền `CodexOAuth1455Lock`. Nếu 2 profile chạy đồng thời, profile sau sẽ ghi đè `codeVerifier` của profile trước, dẫn đến lỗi `state mismatch` hoặc mất mã ủy quyền.
- **Mô hình Hybrid**: Các bước nặng như Hotmail Login và Reg ChatGPT chạy song song 5 workers độc lập; chỉ khi bước vào chặng lấy token Codex OAuth mới xếp hàng tuần tự qua port 1455.

### 5SIM Balanced Score Pool Optimization, Lazy Cache Refresh (1h Cooldown) & Country Dropdown
- **Công thức Điểm Cân Bằng (Balanced Score)**:
  $$\text{Score} = \frac{\text{Rate24h} \times 0.7 + \text{Rate72h} \times 0.3}{\text{Cost}}$$
  Sắp xếp danh sách pool tự nhiên theo `(-score, -rate24, cost)`.
- **Bộ lọc điều kiện cứng (User Mandate)**:
  - Giá rẻ loanh quanh $0.05 - $0.12 (ví dụ: Philippines `virtual58` ~$0.10, Argentina `virtual62` ~$0.05, Việt Nam `virtual34` ~$0.10).
  - Tỉ lệ thành công 24h: `rate24h >= 15% - 20%`, số dư trong kho `count > 20`.
- **Lazy Cache Refresh (1h Cooldown — User Directive 2026-10-09)**:
  - Khi chạy 5 worker song song, nếu lần nào worker khởi động cũng gửi request quét API giá 5SIM thì sẽ kích hoạt ngay lỗi **HTTP 429 Too Many Requests** và làm chậm script. Ngược lại, nếu cache cứng 24h thì không bắt kịp các đợt số mới.
  - **Mô hình Lazy Refresh 1 giờ (`CACHE_TTL_SECONDS = 3600`)**: Khi script chạy, kiểm tra `time.time() - updated_at < 3600`. Nếu cache còn hạn, đọc ngay từ file `5sim_best_pools.json` (0.001s). Nếu cache cũ hơn 1 giờ, chỉ 1 worker đầu tiên quét lại API cập nhật cache, các worker khác dùng chung, triệt tiêu 100% lỗi 429.
- **Kỷ luật thử số & Xoay tua quốc gia**:
  - Tối đa 3 số/quốc gia (`country_tries = 3`), tối đa 3 quốc gia/phiên.
  - Nếu không nhận OTP trong vòng 45-90s hoặc OpenAI từ chối số, **LẬP TỨC gọi endpoint `/v1/user/cancel/{order_id}` để hoàn tiền 100% về ví 5SIM**.
  - Sau khi cancel hoàn tiền, bốc tiếp số thứ 2, thứ 3 của chính quốc gia đó. Đủ 3 số không được mới chuyển sang quốc gia tiếp theo.
- **Xử lý Dropdown Quốc gia React Aria trên `auth.openai.com/add-phone` (Typeahead Match)**:
  - Dropdown quốc gia trên OpenAI là React Aria component ảo hóa (`button[aria-haspopup="listbox"]`), các phần tử option không render sẵn hết trong DOM nên tìm theo `data-key` hoặc scroll rất dễ bị timeout.
  - **Kỹ thuật Typeahead chuẩn**: Mở dropdown (`click(force=True)`), sau đó gõ từ khóa tiếng Việt không dấu (với delay 40-50ms) rồi ấn `Enter`:
    * `"Viet"` $\rightarrow$ Việt Nam (+84)
    * `"Vuong"` $\rightarrow$ Vương quốc Anh (+44)
    * `"Phil"` $\rightarrow$ Philippines (+63)
    * `"Argen"` $\rightarrow$ Argentina (+54)
    * `"Thai"` $\rightarrow$ Thái Lan (+66)
    * `"Hy Lap"` $\rightarrow$ Hy Lạp (+30)
  - Sau khi chọn xong, kiểm tra text trên button (`inner_text()`) chứa đúng tiền tố `+{pfx}`. Nếu không khớp thì hủy số, tránh gửi nhầm mã vùng gây tốn tiền.
- **Cơ Chế Ngâm An Toàn 48h Cho Token Mới (`is_active = 0` & No-Agent Cronjob)**:
  - Khi tài khoản mới vừa hoàn tất OAuth, tuyệt đối KHÔNG để token nhận request API dồn dập ngay vì Risk Engine của OpenAI sẽ gắn cờ bot velocity.
  - Ngay sau khi bắt được `connection_id`, script tự động thực thi SQLite:
    `UPDATE provider_connections SET is_active = 0 WHERE id = ?`
    để đưa token vào trạng thái "ngủ" ngâm 48h.
  - Cronjob quét kích hoạt sau 48h (`omni-activate-soaked-codex`) **BẮT BUỘC cấu hình `no_agent: True`**: Vì đây là tác vụ chạy script Python thuần túy kiểm tra timestamp trong SQLite, cấu hình `no_agent: True` giúp tốn 0 token LLM và chống triệt để lỗi dừng job do drift model (`Skipped to prevent unintended spend: global inference config drifted`).

### Quy Trình Xử Lý `invalid_auth_step` & Kỷ Luật Thử Đủ 9 Lần (User Directive 2026-10-01)
- **Bản chất `invalid_auth_step`**: Khi OpenAI từ chối số (hoặc số bị ép WhatsApp nhưng SIM ảo không nhận được), backend OpenAI hủy transaction OAuth hiện tại.
- **KỶ LUẬT BẤT BIẾN — CỨ GẶP INVALID LÀ LẤY LINK MỚI, THỬ ĐỦ 9 LẦN (User Directive 2026-10-01)**:
  - **TUYỆT ĐỐI CẤM DỪNG SỚM**: Không bao giờ thấy `invalid_auth_step` ở lần thử đầu mà vội đóng profile hay đưa vào ngâm 24h! Làm vậy là vi phạm nghiêm trọng chỉ đạo của User.
  - **Quy trình 4 bước bắt buộc khi gặp `invalid_auth_step`**:
    1. **Hủy số hoàn tiền 100%**: Gọi `/v1/user/cancel/{order_id}` trên 5SIM ngay lập tức.
    2. **Lấy link OAuth mới từ OmniRoute & Bẫy Form Ma (Ghost/Dead Form Trap)**:
       - Gọi `reset_to_add_phone(page)` -> lấy `authUrl` mới từ `http://localhost:20129/api/oauth/codex/start-callback-server` (`prompt=consent`), điều hướng và click chọn lại thẻ tài khoản để mở lại form `add-phone` sạch với transaction backend hoàn toàn mới.
       - *Bẫy DOM 1*: Khi có popup đỏ `invalid_auth_step`, URL vẫn là `add-phone` và ô `input[type="tel"]` vẫn còn, nên `is_phone_verification_page(page)` trả về `True`. BẮT BUỘC kiểm tra `any(x in body_text for x in ("invalid_auth_step", "bước ủy quyền không hợp lệ"))` để ép gọi `reset_to_add_phone(page)`, cấm chỉ clear input gõ tiếp vào transaction đã chết.
       - *Bẫy DOM 2 (Bẫy Form Ma / Ghost Form khi văng Session)*: Khi tài khoản bị văng session ChatGPT, nạp `authUrl` sẽ bị redirect về `https://auth.openai.com/log-in`. TUYỆT ĐỐI CẤM fallback bằng lệnh `page.goto("https://auth.openai.com/add-phone")`! Khi chưa có session đăng nhập, `add-phone` chỉ render ra giao diện React rỗng (form ma); submit bất kỳ số nào cũng bị backend từ chối và ném `invalid_auth_step`.
       - *Bẫy False-Positive Cookie & Cơ chế Tự động Đăng nhập lại (Auto-Relogin)*: Trên trang `auth.openai.com/log-in`, OpenAI luôn tạo cookie `auth-session-minimized`. TUYỆT ĐỐI CẤM kiểm tra cookie chứa chuỗi `session` hay `auth` để ngộ nhận là đã đăng nhập rồi ép nhảy vào form rỗng `/add-phone`. Ngược lại, khi phát hiện URL chứa `/log-in` hoặc `/login`, đây là tín hiệu OpenAI yêu cầu đăng nhập lại tài khoản để khôi phục session.
       - *KỶ LUẬT AUTO-RELOGIN (User Correction 2026-10-01)*: TUYỆT ĐỐI CẤM dừng lại và báo BLOCKED khi thấy màn hình login! Hệ thống bắt buộc chạy quy trình Auto-Relogin 2 nấc (`handle_auto_relogin`):
         1. **Nấc 1 (Email + Password)**: Điền email $\rightarrow$ Bấm Tiếp tục. Ở form mật khẩu (`/log-in/password`), điền mật khẩu từ Cột 12 `PASS CHATGPT` trong workbook `taikhoan_dat_v2_updated .xlsx` (thử cả mật khẩu gốc lẫn bản `normalize_password` `>= 12` ký tự `<pwd>@Taadaa2026`).
         2. **Nấc 2 (OTP Email qua Graph API)**: Nếu OpenAI yêu cầu mã xác minh hòm thư (`/email-verification`) hoặc sai mật khẩu: Tự động gọi `MicrosoftGraphOTPProvider` đọc mã OTP 6 số qua Microsoft Graph API Hotmail và điền submit.
         3. **Tiếp nối luồng OAuth & Bẫy Chuyển hướng Sau OTP**: 
            - Khi xác thực OTP thành công trên domain `auth.openai.com`, backend OpenAI thường tự động chuyển hướng thẳng sang `https://auth.openai.com/add-phone` với transaction OAuth còn sống nguyên vẹn.
            - **BẮT BUỘC**: Kiểm tra `if "add-phone" in page.url.lower():` thì TUYỆT ĐỐI KHÔNG nạp lại `clean_auth_url` (nạp lại sẽ hủy transaction hiện tại và ép quay lại `choose-an-account`), mà giữ nguyên form sạch để đi thẳng vào vòng lặp mua số 5SIM. Chỉ nạp lại `clean_auth_url` khi URL không tự nhảy sang `add-phone`.
            - **Bẫy Invalid State khi chuyển nấc OTP thủ công**: Nếu đang ở form mật khẩu mà bấm vào link "Đăng nhập bằng mã dùng một lần" có thể kích hoạt lỗi `invalid_state (Phiên đã kết thúc)`. Giải pháp tối ưu: Reload lại link OAuth từ đầu (`page.goto(clean_auth_url)`), nhập email để OpenAI tự động chuyển sang trang `/email-verification` sạch.
         4. **Chỉ báo BLOCKED khi**: Cả mật khẩu lẫn Graph API đều bất khả thi (ví dụ hòm thư dính cờ khóa `AADSTS70000: service abuse mode`) hoặc dính Cloudflare captcha cứng.
       - *Kỷ luật Nghiệm thu Luồng Phục hồi (Recovery Canary Discipline - User Correction 2026-10-01)*:
         * Khi nghiệm thu một cơ chế sửa lỗi / tự động phục hồi session (`handle_auto_relogin`): **TUYỆT ĐỐI CẤM** lấy profile đang có session đăng nhập sẵn hoặc vừa được thao tác thủ công để test rồi vội kết luận là thành công (*"Ủa là chạy success luôn chứ có gặp lỗi đâu mà biết liệu có thành công hay k"*). Làm như vậy chỉ đi qua happy path thông thường, hoàn toàn không kiểm chứng được năng lực tự phục hồi của code.
         * BẮT BUỘC phải tái hiện đúng hiện trường lỗi (ví dụ chủ động xóa cookie trên profile để OpenAI đá về `auth.openai.com/log-in`), sau đó kích hoạt runner tự động để kiểm chứng toàn bộ quá trình: phát hiện văng session $\rightarrow$ tự điền email $\rightarrow$ tự đọc mã OTP qua Microsoft Graph API $\rightarrow$ tự phục hồi form `add-phone` sạch $\rightarrow$ mua số 5SIM $\rightarrow$ hoàn tất Codex OAuth.
         * **Kiểm thử khôi phục lỗi số / invalid_auth_step (User Directive 2026-10-01 & 2026-10-02)**: BẮT BUỘC test trên **tài khoản CHƯA TỪNG OAuth** (đang ở `WAIT_24_48H`). Phải inject đúng pha lỗi (số đầu bị từ chối / ép WhatsApp khiến transaction OAuth bị hủy), sau đó gọi `reset_to_add_phone` lấy link OAuth mới và chứng minh form mới khôi phục là form SỐNG (cho phép submit tiếp số thứ 2 mà không bị văng lỗi đỏ `invalid_auth_step`). Tuyệt đối không nghiệm thu trên nick pass thẳng mà không qua bước văng lỗi ("Ủa là chạy success luôn chứ có gặp lỗi đâu mà biết liệu có thành công hay k").
       - *Bẫy DOM OpenAI tự động nhảy chọn sang WhatsApp khi điền số (WhatsApp Auto-Select Trap — User Correction 2026-10-02)*:
         * **Hiện tượng 1 (Auto-swap của React form)**: Trên form `auth.openai.com/add-phone`, khi mới load trang, radio option mặc định là `Tin nhắn văn bản (SMS)`. Tuy nhiên, khi runner điền chuỗi số điện thoại vào ô `input[type="tel"]` (đặc biệt là đầu số Argentina `+54` hoặc các nước Nam Mỹ), mã script frontend React của OpenAI tự động format số và **TỰ ĐỘNG TRÁO CHỌN SANG WHATSAPP** (`val=whatsapp checked=True, val=sms checked=False`).
         * **Hiện tượng 2 (Backend carrier SMS block banner)**: Với một số dải số ảo (như Argentina ảo 5SIM), OpenAI hiển thị thẳng banner màu vàng/đỏ: *"Chúng tôi không gửi tin nhắn SMS tới số này nên đã chuyển sang Tiếp tục để xác minh WhatsApp."* Đây là chính sách từ chối kênh SMS của OpenAI với nhà mạng đó.
         * **Hậu quả nghiêm trọng**: Nếu automation click chọn SMS *trước khi* điền số, thao tác gõ số sẽ xóa mất lựa chọn SMS và ép OpenAI gửi OTP qua WhatsApp. Vì SIM ảo 5SIM chỉ nhận SMS thông thường, OTP WhatsApp sẽ không bao giờ tới $\rightarrow$ timeout $\rightarrow$ tốn tiền / hỏng luồng.
         * **Kỷ luật thứ tự thao tác DOM (Invariant Execution Order)**:
           1. Chọn mã quốc gia trong dropdown (`button[aria-haspopup="listbox"]`).
           2. Gõ số điện thoại vào ô `input[type="tel"]` (sau khi đã `Control+A` + `Backspace`).
           3. **BẮT BUỘC CHỌN SMS SAU CÙNG (Hàm `enforce_sms_channel`)**: Click vào `label:has-text("Tin nhắn")` / `label:has-text("Text message")` và gọi script JS ép `smsRadio.checked = true` **SAU KHI ĐÃ ĐIỀN XONG SỐ**.
              - Phải module hóa thành hàm độc lập `def enforce_sms_channel(page, country: str = "", attempt: int = 1) -> bool:` thay vì viết inline block.
              - Gọi tại callsite trong loop: `enforce_sms_channel(page, country, total_attempts)`.
           4. **Kỷ luật nuốt lỗi & Telemetry**: CẤM nuốt ngoại lệ bằng `pass` trần trong khối chọn radio; bắt buộc ghi log warning `logging.getLogger(__name__).warning(...)` và phát telemetry event `log_telemetry_event("sms_channel_enforced", {"country": country, "attempt": attempt, "confirmed": bool(sms_confirmed)})`.
           5. Kiểm tra chắc chắn `smsRadio.checked == True` và `whatsappRadio.checked == False` trước khi bấm Submit.
           6. **Quy chuẩn Closeout Mock Test (`test_enforce_sms_channel_runtime_behavior`)**:
              - Đạt >= 85 điểm trên `closeout_gate.py` đòi hỏi mock test phải test hành vi thực tế của `enforce_sms_channel`: mock `page.locator().is_visible()`, `click()`, `page.evaluate()`, và `log_telemetry_event`.
              - CẤM mock hời hợt kiểu `mock_page.evaluate.return_value = True; self.assertTrue(...)` không gọi qua hàm thật.
           7. **Quy tắc Guard môi trường trong `D:\Taadaa\GPM auto`**:
              - Tránh dùng `search_files` với root `D:/Taadaa/GPM auto` (dính cờ `[GUARD_SEARCH_FILES_ROOT]`).
              - Mọi lệnh `terminal` foreground bắt buộc có flag `timeout <= 60` (tránh dính cờ `[GUARD_FOREGROUND_TIMEOUT_MISSING]`).
         * **Cơ chế Hủy Hoàn Tiền & Xoay Tua Quốc Gia (Carrier SMS Fallback)**:
           - Khi gặp banner WhatsApp hoặc trang chuyển sang màn hình mã WhatsApp: Lập tức gọi 5SIM API `/v1/user/cancel/{order_id}` để hoàn tiền 100% về ví, giữ nguyên phiên browser.
           - Sau khi thử 3 số Argentina liên tiếp đều bị ép WhatsApp: Runner tự động xoay tua sang quốc gia tiếp theo trong danh sách có tỷ lệ nhận SMS cao (ví dụ: South Africa `+27`), nơi OpenAI cho phép nhận SMS mượt mà để hoàn tất kích hoạt.
       - *Bẫy is_phone_verification_page với Popup Lỗi*: Khi OpenAI ném lỗi `invalid_auth_step`, ô `input[type="tel"]` vẫn còn trong DOM nên hàm check phone page trả về `True`. BẮT BUỘC kiểm tra loại trừ nếu DOM chứa `invalid_auth_step`, `bước ủy quyền không hợp lệ`, hoặc `lỗi không xác định` thì trả về `False` ngay lập tức.
       - *Microsoft Graph API Abuse Lock (`AADSTS70000`)*: Khi refresh token trả về `AADSTS70000: User account is found to be in service abuse mode`, hòm thư Hotmail đã bị Microsoft khóa dịch vụ bên ngoài, không thể lấy OTP qua Graph API. BẮT BUỘC dừng luồng tự động và kích hoạt quy trình Migration thay Hotmail mới (sau khi xin phép User).
    3. **Tiếp tục thử số cùng quốc gia**: Thử tiếp số 2, số 3 của chính quốc gia đó (`c_try = 1..3`, cấm dùng `break`).
    4. **Duyệt đủ trần 9 lần**: Mỗi quốc gia 3 số, tối đa 3 quốc gia (tổng ngân sách 9 lần thử). CHỈ chuyển sang quốc gia tiếp theo khi đã thử đủ 3 số của nước hiện tại hoặc 5SIM báo hết số.
  - **CHỈ ĐƯỢC PHÉP ĐƯA VÀO NGÂM COOLDOWN 24H KHI**: Đã thử hết đủ cả 3 quốc gia (trần 9 lần) mà đều không nhận được OTP, hoặc gặp Cloudflare Turnstile / Captcha cứng.

## Historical request audit

Use only targeted known OmniRoute storage/API paths. If `call_logs`, `request_detail_logs`, traffic inspector, and usage history contain no incident-window records, report the missing observability explicitly instead of inferring spam. Redact API keys, cookies, tokens, full phone numbers, and OTPs. No provider test, login, SSO, GPM opening, or paid 5SIM action is needed for read-only diagnosis.

## Morning Pool Healer Watchdog Architecture (ChatGPT-Web + Antigravity + Codex)

The morning watchdog (`cron_chatgpt_web_pool_watchdog.py`) executes daily at 05:00 AM, unifying healing for all 3 key providers via GPM profiles:
1. **ChatGPT-Web**: Runs with **5 parallel workers** (`ThreadPoolExecutor(max_workers=5)` — user mandate: GPM desktop is isolated from phone farm, never throttle to 1 worker).
   - **Bắt buộc Auto-Relogin khi văng session (Anti-Cry Invariant — User Directive 2026-10-04)**: Khi kiểm tra session hiện có hoặc gọi `/api/providers/validate` mà thất bại (`HTTP 400 Bad Request`, `401 Unauthorized`, hoặc DOM văng ra màn hình Log in/Session expired), TUYỆT ĐỐI CẤM dừng sớm rồi báo lỗi khóc lóc! Watchdog BẮT BUỘC chuyển tiếp ngay sang hàm Auto-Relogin (`perform_auto_login_and_extract_cookies`):
     * **Bẫy Python venv vs Host Python (`py -3`)**: Lệnh `python` trong shell mặc định trỏ vào virtualenv của Hermes (`hermes-agent/venv`), thiếu các thư viện automation của host (`requests`, `playwright`). BẮT BUỘC gọi script GPM bằng `py -3` hoặc đường dẫn tuyệt đối `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe`.
     * **Bẫy Báo Xong Ảo Khi Chưa Chạy Canary Live (User Correction 2026-10-05)**: Tuyệt đối CẤM lấy kết quả 20/20 test mock (pytest offline) hay trigger cron ngầm (`execution_success: true`) để khẳng định đã fix xong khi chưa chạy canary live trên đúng target. Phải chạy thực tế, đọc log/report (`chatgpt_login_report.json`), OCR ảnh chụp màn hình nghiệm thu (`WinRT OCR`), và đối soát trạng thái connection trên OmniRoute.
     * **Bẫy Cookie Cũ Tồn Lưu (Stale Cookie Jar Trap)**: Nếu không gọi `context.clear_cookies()`, browser vẫn lưu chunk cookie cũ `__Secure-next-auth.session-token`. Sau khi navigate `chatgpt.com/auth/login`, script trích xuất lại đúng cookie chết và ném tiếp lỗi 400! BẮT BUỘC xóa cookie cũ trước khi re-login.
     * **Bẫy Nút Log In Landing Page**: Trang `chatgpt.com/auth/login` thường hiển thị landing page với nút `[data-testid="login-button"]` hoặc `button:has-text("Log in")`. Phải click nút này để mở form nhập email/pass, không được giả định form đã hiện sẵn.
     * Điền `PASS CHATGPT` từ Cột L workbook (hoặc OTP qua Graph API/Gmail), thu hoạch session token mới, thẩm định lại `1+1=2` rồi mới kết luận.
   - **Dual Auth & Password Resolution**: Supports both Early Cohort (Google SSO `Continue with Google`) and Later Cohort (Direct Email + Password).
     * **CRITICAL PASSWORD SOURCE**: Mật khẩu ChatGPT chính chủ phải đọc từ **cột L (`PASS CHATGPT`)** trong file `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (hoặc `taikhoan_dat_v2_updated.xlsx`), KHÔNG dùng pass mail trừ khi là fallback.
   - **Cookie Overlay Dismissal**: Bắt buộc click `[Chấp nhận tất cả]` / `[Accept all]` / `[Allow all]` ngay khi vào trang để tránh bị lớp overlay cookie che nút bấm gây lỗi `Locator.click: Timeout 30000ms exceeded`.
   - **Onboarding Age Bypass**: Fills `input[name="age"] = 24` to prevent 60s session timeouts on new UI.
   - **False-Positive Cookie Jar Trap & DOM Validation**: URL `https://chatgpt.com/` xuất hiện cả khi tài khoản đã bị văng session (logged out). Trình duyệt vẫn lưu cookie cũ `__Secure-next-auth.session-token`. BẮT BUỘC kiểm tra DOM không chứa "Your session has expired" / "Log in" / "Đăng nhập" trước khi trích xuất token.
   - **Ground-Truth Inference Validation**: Tuyệt đối không tin tưởng token thô; bắt buộc bắn 1 request kiểm chứng động `1+1=?` trả về đúng số `2` qua OmniRoute mới bật `is_active = 1`, `test_status = 'active'`.
   - **Detection of Deactivated Accounts**: Bắt mã lỗi URL `payload=` chứa `account_deactivated` hoặc `AccountDeactivated` để set `is_active = 0`, `test_status = 'banned'` vĩnh viễn, tránh retry vô ích.
2. **Antigravity**: Google OAuth consent screen automation + token exchange.
   - **Liên thông S7 Phối hợp Bắt buộc (S7 Coordination Invariant — User Directive 2026-10-04)**: Khi tài khoản bị thu hồi token (`401` / `unrecoverable_refresh_error`) và re-auth gặp màn hình xác minh danh tính của Google (`challenge/dp`, `challenge/ootp`, `challenge/selection`), TUYỆT ĐỐI CẤM ngồi chờ thụ động đến hết 90s rồi báo `Timeout bắt OAuth code`! Watchdog BẮT BUỘC kích hoạt cơ chế phối hợp với thiết bị Samsung S7 (gọi sang `run_oauth_s7_pipeline.py` hoặc ATX-Agent port `7912`):
     * Google Prompt (`challenge/dp`): Duyệt nút "Có" / "Yes" hoặc bấm mã PIN tương ứng qua ADB shell.
     * Security Code 10 số (`challenge/ootp`): Tự động vào Cài đặt Google Play Services trên máy S7 chứa nick (tra từ `master_gmail_manager.xlsx`) để trích xuất 2 mã bảo mật 10 chữ số offline điền vào PC.
     * TOTP Secret: Nếu tài khoản có sẵn TOTP 2FA trong Excel, tự tính mã qua `pyotp.TOTP(secret).now()` điền trực tiếp, ưu tiên cao hơn S7.
3. **Codex**: Detects accounts with revoked upstream tokens (`401 / Token invalid or revoked` or `testStatus != 'active'`):
   - Opens the 1:1 GPM profile for the account.
   - Binds local callback on port 1455 via `start-callback-server`.
   - Strictly enforces **NO Google SSO** (hides `Continue with Google`), fills Direct Email + Password + TOTP from `gmail_clean_v2.xlsx`.
   - Handles consent ("Continue" / "Tiếp tục" / "Authorize") and forwards port 1455 callback to `127.0.0.1`.
   - Re-enables connection in SQLite (`is_active = 1`, `test_status = 'active'`, resets error flags) and returns account to rotation.
   - **Soak Protection**: Accounts ending in `@hotmail.com` or marked in `WAIT_48H` soak state are explicitly bypassed by the morning healer to protect the 48-hour cooldown window.

## Inactive Toggle (is_active = 0) Triage Matrix

When inspecting disabled connections (`is_active = 0`) on OmniRoute:
- **`SOAKING_48H`**: Newly registered/verified Hotmail via 5sim. Probe `/api/providers/{id}/test` returns `valid: true`. Do NOT re-auth or manually toggle ON; cronjob `omni-activate-soaked-codex` will auto-activate after 48 hours.
- **`TOKEN_REVOKED_401`**: Upstream OpenAI token revoked. Probe test returns HTTP 401 `Token invalid or revoked`. Tokens **NEVER** spontaneously recover. Toggling ON manually without re-auth immediately breaks downstream requests and triggers pool cascading failures. Must be healed via GPM OAuth.
- **`QUOTA_EXHAUSTED`**: Account has 0% remaining quota. Token remains valid (`valid: true`). Quota resets on a rolling 30-day (monthly) schedule for Codex Free, not weekly. Do NOT set `is_active = 0` for quota exhaustion; OmniRoute's combo router handles exhaustion dynamically via `is_exhausted = 1`. Setting `is_active = 0` permanently disables the account because there is no automated cron to turn it back on after quota resets.

## Pre-Codex Web Session Token Extraction Pipeline (Dual-Duty Provisioning)

- **Nguyên tắc kép (User Directive 2026-09-30)**: Khi đăng ký mới hoặc đăng nhập tài khoản ChatGPT trên profile GPM, **BẮT BUỘC trích xuất cookie session-token nạp vào `chatgpt-web` TRƯỚC KHI chạy luồng ver số 5SIM cho Codex**.
- **Mục đích**: Một tài khoản sinh ra phục vụ đúp cả 2 mục đích:
  1. Làm tài nguyên cho Sol High (`chatgpt-web/gpt-5.6-sol-high`) đi lập Plan T2 và Review code với **chi phí 0đ quota Codex**.
  2. Cung cấp token OAuth Codex cho Worker Luna High (`codex/gpt-5.6-luna-high`) thi công code.
- **Quy trình chuẩn**:
  1. Ngay khi profile GPM vừa đăng nhập/onboarding vào màn hình chính `chatgpt.com` thành công: Trích xuất cookie `__Secure-next-auth.session-token` (ghép chuỗi chunk `.0`, `.1` nếu có).
  2. Nạp/cập nhật vào OmniRoute `provider_connections` (`provider: 'chatgpt-web'`), gán `is_active = 1`, `test_status = 'active'`, gán proxy di động 4G 1:1 tương ứng từ profile, và thêm vào cả 2 combo `gpt-web-sol` + `chatgpt-web-pool`.
  3. Sau khi xác nhận Web session đã nạp thành công, mới chuyển sang bước kích hoạt `authUrl` Codex và gọi 5SIM API lấy OTP.
- **Cân bằng tải & An toàn Pool Web (P2C + 1:1 Proxy)**:
  - Duy trì thế cân bằng quân số giữa 2 pool (~27-31 tài khoản active song song).
  - Combo `gpt-web-sol` áp dụng thuật toán `p2c` (Power of Two Choices) kết hợp `disableSessionStickiness: true` và `disablePromptCacheAffinity: true`, rải đều request qua 27+ IP MobiProxy 4G khác nhau, ngăn chặn hoàn toàn việc dính cờ bot hay lạm dụng từ OpenAI.

## Root Cause of OpenAI Account Bans (`AccountDeactivated`) vs SSO Myth & Payload Size Discipline

- **Sự thật về Google SSO vs Ban nick (User Directive & Audit 2026-09-30)**:
  * Google Gmail có độ trust tự nhiên cao hơn Hotmail rất nhiều. Việc các tài khoản Gmail cũ (`hakha`, `thaidiem`, `hoangvy`) bị OpenAI khai tử với thông báo `AccountDeactivated` **KHÔNG PHẢI do bản thân cơ chế Google SSO**.
  * **NGUYÊN NHÂN GỐC RỄ TỪ LỊCH SỬ SỬ DỤNG (Trước 25/09/2026)**:
    1. **Bắn dồn dập (Single-account hammer)**: Combo cũ thiếu cơ chế cân bằng tải P2C, dồn 147 request/ngày vào một vài tài khoản (như `luunhu`, `hoangvy`), gửi request liên tục cách nhau 5-10 giây khiến OpenAI đánh dấu bot abuse.
    2. **Consecutive HTTP 413 (Payload Too Large)**: Agent nạp các payload quá khổ (>100KB - 500KB diff/logs/context) tọng thẳng vào Web API. Cổng ChatGPT Web (`/backend-api/conversation`) chỉ chấp nhận context <= 64KB - 128KB; việc dính lỗi 413 liên tiếp kích hoạt hệ thống phát hiện lạm dụng tự động của OpenAI.
    3. **Bỏ qua cờ Cloudflare Sentinel HTTP 403**: Tiếp tục spam HTTP request khi Cloudflare đã đòi Turnstile/browser verification.
- **Kỷ luật Giới hạn Kích thước Payload (Payload Size Clamping)**:
  * `closeout_gate.py`: Trần trích xuất diff `max_bytes` BẮT BUỘC hạ từ 512KB xuống <= 64KB (hoặc 40.000 ký tự). Vì diff T2 thi công trong lồng <= 30 dòng chỉ vài KB, giữ mức 512KB là vi phạm kỷ luật an toàn của Web API.
  * Prompt Planner T2 cho Sol High: Bắt buộc cắt tỉa log/context quá dài (> 32KB), chỉ giữ lại header + 50 dòng context quanh anchor lỗi.
- **Cơ chế Dual-Death khi bị Deactivated**:
  * Khi OpenAI vô hiệu hóa tài khoản (`AccountDeactivated`), cả 2 cổng đều chết: Web văng ra URL chứa `payload=` báo lỗi, còn Codex trả về `[401] Encountered invalidated oauth token for user`.
  * Xử lý: Phải tắt công tắc vĩnh viễn (`is_active = 0, test_status = 'banned'`) trên **CẢ 2 provider `chatgpt-web` LẪN `codex`** trong OmniRoute SQLite để tránh các worker khác bốc nhầm acc chết.

## OpenCode Bridge (:20130) Fallback Timeout Safety

- **Hiện tượng**: Khi Hermes gặp rớt mạng cục bộ với OmniRoute và fallback sang OpenCode (`opencode/muse-spark-1.3-contributor-free`), request bị hủy ngang với lỗi: `[Error: OpenCode opencode/muse-spark-1.3-contributor-free request timed out after 35s]`.
- **Nguyên nhân**: File `D:\Taadaa\tools\opencode_bridge.py` đặt cứng `timeout = 35` (hoặc 45 với ảnh). Cụm model miễn phí trên đám mây của OpenCode có hàng đợi và cần 40-50s để suy nghĩ; script tự tay ngắt kết nối trước khi model kịp trả lời.
- **Quy chuẩn cấu hình**:
  * BẮT BUỘC cấu hình `timeout = 90` (cho prompt văn bản) và `timeout = 120` (cho prompt có hình ảnh).
  * Kiểm tra tiến trình bằng `netstat -ano | grep 20130` và restart service an toàn sau khi vá code.


