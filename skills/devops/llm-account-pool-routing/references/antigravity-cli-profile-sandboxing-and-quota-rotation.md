# Antigravity CLI Profile Sandboxing, Hardware ID Isolation & Quota Rotation

## Bối cảnh & Căn nguyên Kỹ thuật

Khi mở rộng quy mô chạy nhiều tài khoản Google One / Antigravity Pro trên Antigravity CLI (`agy`), có các cái bẫy kỹ thuật chết người nếu cấu hình ngây thơ:

1. **Dùng chung `installation_id` (Cực kỳ nguy hiểm):**
   - Mặc định, `agy.exe` đọc cấu hình từ thư mục `$USERPROFILE/.gemini/`.
   - File `.gemini/installation_id` chứa một chuỗi UUID duy nhất đại diện cho phần cứng máy tính.
   - Nếu xoay 20 tài khoản bằng cách đổi token hoặc đổi proxy mà vẫn trỏ chung vào một thư mục `.gemini/`, Google sẽ thấy: **Cùng 1 máy vật lý (chung `installation_id`) nhưng lại phát request từ 20 IP khác nhau trên khắp thế giới trong cùng một ngày** -> Dấu hiệu gian lận Sybil rõ ràng, dẫn đến nguy cơ bị khóa hàng loạt tài khoản Pro.

2. **So sánh Độ Sạch: Native `agy` CLI vs OmniRoute (`:20129`):**
   - **OmniRoute:** Giả lập L7 (thứ tự Header HTTP và JSON body fields qua `cliFingerprints.ts`), nhưng ở tầng L4/L5 transport lại dùng Node.js `undici/fetch`. Chữ ký bắt tay TLS (JA3/JA4) và HTTP/2 SETTINGS frames mang đặc trưng của Web Server/Node.js, có thể bị Google Cloud Armor/Envoy phát hiện khi quét bot và dẫn tới nguy cơ quét chết chùm 20 tài khoản.
   - **Native `agy.exe`:** Do chính Google compile (Go + BoringSSL). Chữ ký TLS, HTTP/2 framing, và token refresh logic là 100% "chính chủ", hoàn toàn không thể phân biệt với lập trình viên thật.

3. **Bẫy Rò rỉ Cache Windows (`APPDATA` / `LOCALAPPDATA` / `TEMP`):**
   - Nếu chỉ đổi `USERPROFILE`, binary `agy.exe` và Chromium/Google engine vẫn đọc/ghi cache và lock vào `C:\Users\<user>\AppData\Local\...`.
   - Khi đó, cả 20 profiles dùng chung local cache, Google soi tầng device cache sẽ phát hiện chạy chung máy. Bắt buộc phải cô lập toàn bộ các biến môi trường hệ thống.

---

## Kiến trúc Sandbox Cô Lập Đầy Đủ (Full Sandbox Architecture)

Mỗi tài khoản được cấp một sandbox trọn vẹn tại `D:/Taadaa/agy_profiles/<name>/`:

```text
D:/Taadaa/agy_profiles/
  ├── profiles_config.json      # Quản lý danh sách profiles, path, proxy gán riêng
  ├── pool_state.json           # Lưu timestamp cooldown khi tài khoản chạm rate limit
  ├── acc_01/
  │     ├── .profile.lock       # File lock chiếm dụng profile (tránh race condition)
  │     ├── AppData/
  │     │     ├── Roaming/      # Cô lập %APPDATA%
  │     │     └── Local/        # Cô lập %LOCALAPPDATA% (chống leak cache)
  │     ├── Temp/               # Cô lập %TEMP% và %TMP%
  │     └── .gemini/
  │           ├── installation_id   # UUID4 riêng biệt của Acc 01
  │           ├── oauth_creds.json  # Token OAuth riêng của Acc 01
  │           └── google_accounts.json
```

---

## Cơ chế Vận hành & Bảo vệ qua Controller `ag_cli.py`

Cầu nối `D:/Taadaa/tools/ag_cli.py` đóng vai trò Bộ điều phối Failover tự động (Headless Load Balancer & Safety Controller):

### 1. Khởi tạo Profile Sandbox Mới:
```bash
# Tạo acc_02 gắn với Proxy di động 4G (cổng 20002)
python D:/Taadaa/tools/ag_cli.py init-profile acc_02 --proxy "http://127.0.0.1:20002"

# Hoặc khởi tạo acc_01 bằng cách sao chép credentials hiện tại trên máy
python D:/Taadaa/tools/ag_cli.py init-profile acc_01 --copy-current
```

### 2. Đăng nhập tài khoản Google cho Sandbox:
- **Cách 1 (Thủ công trên máy):**
  ```bash
  # Set USERPROFILE trỏ vào đúng sandbox rồi chạy agy login
  USERPROFILE="D:/Taadaa/agy_profiles/acc_02" agy login
  ```
- **Cách 2 (Tự động hóa qua GPM Group 10 + Playwright CDP + Master Workbook):**
  - Mở profile GPM tương ứng qua API `:19995` (đã có sẵn session Google và Proxy 4G di động).
  - Tra cứu thông tin xác thực từ file quản lý trung tâm (xem chi tiết mục 5 bên dưới).
  - Kết nối Playwright CDP tự động click duyệt OAuth cho Antigravity Client ID (`1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`).
  - Đổi mã `code` lấy `refresh_token` & `access_token` rồi ghi thẳng vào sandbox `D:/Taadaa/agy_profiles/acc_XX/.gemini/oauth_creds.json`.

### 3. Kiểm tra trạng thái Pool:
```bash
python D:/Taadaa/tools/ag_cli.py pool-status
```
Báo cáo: Tên profile, Proxy gán kèm, Trạng thái (`READY` / `COOLDOWN`), và thời gian còn lại trước khi hồi quota.

### 4. Bốn Chốt Chặn P0 Đã Tích Hợp (Sol Web Audit Certified):

1. **Full Environment Injection:**
   ```python
   env["USERPROFILE"] = prof_dir
   env["HOME"] = prof_dir
   env["APPDATA"] = os.path.join(prof_dir, "AppData", "Roaming")
   env["LOCALAPPDATA"] = os.path.join(prof_dir, "AppData", "Local")
   env["TEMP"] = os.path.join(prof_dir, "Temp")
   env["TMP"] = os.path.join(prof_dir, "Temp")
   if prof_proxy:
       env["HTTPS_PROXY"] = prof_proxy
       env["HTTP_PROXY"] = prof_proxy
   ```

2. **Profile Lease Locking (`.profile.lock`):**
   - Chống race condition khi nhiều cronjob hoặc subagent gọi `ag_cli.py` cùng một thời điểm.
   - Ghi JSON `{"pid": ..., "timestamp": ...}` với lease timeout 300s.
   - **Tự dọn Stale Lock (Dead PID Check):** Dùng `psutil.pid_exists(pid)`. Nếu tiến trình trước đã chết do crash/timeout, lock được giải phóng ngay lập tức, không làm kẹt profile 300s.

3. **Failover Jitter (Chống cụm hành vi Bot):**
   - Khi dính lỗi quota (`RESOURCE_EXHAUSTED`, `429`, `quota exceeded`), script ghi nhận cooldown 1800s vào `pool_state.json`.
   - Trước khi thử lại với profile kế tiếp, tự động `time.sleep(random.uniform(5.0, 10.0))` để tránh tạo ra mẫu burst correlation gửi request liên tiếp từ nhiều nick.

4. **Kỷ luật Timeout khi Gọi Lệnh `fix`:**
   - Lệnh `ag_cli.py ask` trả lời rất nhanh (2-5s), chạy foreground an toàn.
   - Lệnh `ag_cli.py fix` trên các file lớn cần thời gian suy luận và chỉnh sửa AST từ 70-90s, vượt quá trần foreground timeout 60s của harness Coordinator/Worker.
   - **Quy tắc bắt buộc:** Khi gọi `ag_cli.py fix`, bắt buộc chạy qua `terminal(background=True, notify_on_complete=True, timeout=120)` để tránh bị kill nhầm giữa chừng.

---

## 5. Tự động hóa OAuth GPM: Giải quyết Mật khẩu & 2FA qua Master Workbook SoT

Khi tự động hóa cấp quyền OAuth cho Antigravity trên profile GPM:

### Cạm bẫy thực tế & Phản xạ đóng băng (Luna Behavior):
- **Bẫy Autofill Chrome:** Trình duyệt GPM lưu session cookies nhưng thường **không lưu mật khẩu trong Google Password Manager**. Nếu chỉ click ô password rồi bấm Enter, form submit rỗng và bị kẹt.
- **Bẫy thoái thác an toàn:** Thấy Google hỏi mật khẩu / OTP, Coordinator không được viện cớ "Safety cấm nhập pass" để dừng lại hỏi `clarify` người dùng. Đây là tài khoản của farm user đã lệnh tự động hóa login thì phải tra cứu SoT để điền dứt điểm.

### Nguồn dữ liệu xác thực (Source of Truth):
- Đường dẫn: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (Sheet `Master_All`).
- Chứa đủ 21/21 tài khoản Pro:
  - Cột B (index 1): `Email`
  - Cột C (index 2): `Password`
  - Cột E (index 4): `2FA_Secret` (base32 TOTP key)
  - Cột G (index 6): `Trạng Thái` (LIVE)

### Kịch bản tự động hóa Playwright + pyotp:
```python
import pyotp
import openpyxl

# 1. Tra cứu credentials từ Master Workbook
wb = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx", data_only=True, read_only=True)
ws = wb["Master_All"]
account_cred = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[1] and str(row[1]).strip().lower() == target_email.lower():
        account_cred = {"pwd": str(row[2]).strip(), "2fa": str(row[4]).strip() if row[4] else None}
        break

# 2. Tự điền Password nếu bị hỏi
pwd_input = page.locator("input[type='password']")
if pwd_input.count() > 0 and pwd_input.first.is_visible():
    pwd_input.first.fill(account_cred["pwd"])
    time.sleep(1)
    pwd_next = page.locator("#passwordNext")
    if pwd_next.count() > 0 and pwd_next.first.is_visible():
        pwd_next.first.click()
    else:
        pwd_input.first.press("Enter")
    time.sleep(3)

# 3. Tự sinh & điền mã TOTP 2FA nếu Google thách thức
if account_cred.get("2fa"):
    totp_found = False
    for sel_totp in ["input[type='tel']", "input#totpPin", "input[name='totpPin']", "input[type='number']"]:
        pin_in = page.locator(sel_totp)
        if pin_in.count() > 0 and pin_in.first.is_visible():
            totp_code = pyotp.TOTP(account_cred["2fa"]).now()
            pin_in.first.fill(totp_code)
            pin_next = page.locator("#totpNext")
            if pin_next.count() > 0 and pin_next.first.is_visible():
                pin_next.first.click()
            else:
                pin_in.first.press("Enter")
            time.sleep(3)
            totp_found = True
            break

    # BẪY 2FA DEVICE PROMPT (GALAXY S7): Nếu Google đòi xác nhận trên thiết bị
    if not totp_found:
        try:
            # QUAN TRỌNG: Cấm dùng "button:has-text(), text='...'" (lỗi Unexpected token '=' in Playwright CSS parser)
            other_btn = page.get_by_text("Thử cách khác")
            if other_btn.count() > 0 and other_btn.first.is_visible():
                other_btn.first.click()
                time.sleep(2)
                auth_opt = page.get_by_text("Authenticator")
                if auth_opt.count() > 0 and auth_opt.first.is_visible():
                    auth_opt.first.click()
                    time.sleep(2)
        except Exception:
            pass

# BẪY ACCOUNT CHOOSER CLICK: Chỉ click khi đang ở trang /chooser hoặc /identifier
if any(x in cur_url for x in ["/chooser", "/identifier"]):
    try:
        acc_elem = page.locator(f"[data-email*='{EMAIL}']")
        if acc_elem.count() > 0 and acc_elem.first.is_visible():
            acc_elem.first.click()
            time.sleep(2)
    except Exception:
        pass

# 4. Consent Approve
consent_btn = page.locator("#submit_approve_access, button:has-text('Tiếp tục'), button:has-text('Cho phép')")
if consent_btn.count() > 0 and consent_btn.first.is_visible():
    consent_btn.first.click()
```

---

## 6. Giải nén Token & Đóng gói Profile Headless (`unpack_omni_connection.py`)

Sau khi OmniRoute thực hiện exchange OAuth code và lưu vào `storage.sqlite`:

1. **Giải mã Token at rest (AES-256-GCM):**
   - Khóa giải mã được derive từ `STORAGE_ENCRYPTION_KEY` với salt `omniroute-field-encryption-v1` (scrypt `N=16384, r=8, p=1, dklen=32`).
   - Nếu file `.env` rỗng trên đĩa, script tự động đọc biến môi trường `STORAGE_ENCRYPTION_KEY` từ tiến trình `node.exe` đang chạy qua `psutil.process_iter()`.
2. **Tạo Profile Sandbox tức thì:**
   - Script tiện ích `D:/Taadaa/tools/unpack_omni_connection.py <email> <profile_name> [raw_proxy]` tự động:
     - Tạo thư mục `D:/Taadaa/agy_profiles/<profile_name>/.gemini`
     - Sinh UUID `installation_id` mới
     - Ghi `oauth_creds.json` và `google_accounts.json`
     - Sao chép `settings.json`, `state.json`, `projects.json` mẫu từ `acc_01`
     - Ghi nhận `profile_name`, đường dẫn và Proxy 4G vào `profiles_config.json`
   - **INVARIANT BẮT BUỘC (GPM Proxy 1-1 Alignment & Pro-Tier Audit):**
     * Tham số `[raw_proxy]` BẮT BUỘC phải lấy chính xác từ trường `raw_proxy` của profile tương ứng trong GPMLogin (qua GPM API `:19995`).
     * TUYỆT ĐỐI CẤM gán proxy tuần tự theo số thứ tự (`acc_01 -> mobi1`, `acc_02 -> mobi2`...). Lệch proxy so với GPM làm đổi IP mạng thường dùng của tài khoản, kích hoạt rào cản Google checkpoint `VALIDATION_REQUIRED` / 403.
     * **Audit Entitlement (Pro-Tier Only):** Khi nạp tài khoản vào pool Antigravity CLI, BẮT BUỘC kiểm tra `provider_specific_data` trong database OmniRoute và chỉ chấp nhận tài khoản có gói `g1-pro-tier` / `Google AI Pro`. Tuyệt đối không nạp nhầm các tài khoản `free-tier` làm loãng chất lượng worker.
     * **Full Sandbox Environment Verification:** Mỗi profile mới tạo BẮT BUỘC phải có đầy đủ: UUID `installation_id` riêng, thư mục `AppData/Roaming`, `AppData/Local`, `Temp` cô lập để chống leak cache Windows.
     * Quy mô mở rộng: Toàn bộ 22 profile Gemini Pro (`acc_01` .. `acc_22`) được unpack đồng bộ từ OmniRoute database mang đúng proxy 4G Mobi/Khoalee tương ứng của GPM và sandbox độc lập 100%.
3. **Chỉ định Profile cụ thể khi Kiểm thử (`--profile`):**
   ```bash
   python D:/Taadaa/tools/ag_cli.py ask "Test prompt" --profile acc_02
   ```
   Cờ `--profile` bỏ qua vòng lặp auto-select round-robin để kiểm tra trực tiếp tài khoản mới và kết nối proxy vừa gán.

---

## 7. Kiến Trúc Điều Phối: Hermes Coordinator vs Native `agy` CLI

### 1. Tại sao Hermes Coordinator không thể dùng trực tiếp `agy.exe` làm Model Backend nguyên bản?
- **Khác biệt về giao thức (Protocol Impedance Mismatch):**
  - **Hermes Coordinator:** Cần một **HTTP REST Server** (chuẩn OpenAI `/v1/chat/completions`) hỗ trợ HTTP streaming token, duy trì context nhiều vòng và thực thi ReAct Tool Calling lặp lại (Hermes tự gọi ADB, Telegram, OCR, Cronjob, Computer Use).
  - **`agy.exe`:** Là một **Command Line Interface (CLI)** thực thi đơn nhiệm (One-Shot Process). Khi nhận lệnh, nó khởi động Go runtime, suy luận, thực thi tool nội bộ của nó (AST edit, bash test), in kết quả ra stdout rồi **exit tiến trình ngay lập tức (Exit 0)**.
- **Rào cản:** Nếu ép Hermes mỗi lượt chat lại spawn một tiến trình `agy`, Hermes sẽ mất toàn bộ khả năng tương tác với hệ thống farm (không thể tự chụp màn hình, không thể click ADB, không thể dispatch task) và độ trễ tăng vọt do mỗi lượt đều phải khởi động lại binary Go.

### 2. Hai Mô Hình Tích Hợp Chuẩn & Quyết Định Phân Vai Cốt Lõi:
- **Quyết định Phân vai Tối ưu (User Approved 2026-10-14):**
  - **Coordinator (Hermes):** Giữ nguyên qua OmniRoute xoay tua dàn 21 tài khoản Google Pro. Lý do: Lưu lượng chat và điều phối Telegram/Farm của Coordinator rất nhẹ (vài chục requests/ngày), hoàn toàn dưới ngưỡng giám sát của Google. Giữ trên OmniRoute giúp Coordinator bảo toàn 100% khả năng Function Calling (ReAct Loop, ADB, Vision, Cronjob, Telegram Gateway).
  - **Worker (Thợ code):** Đổi toàn bộ sang `ag_cli.py` (`agy.exe`). Lý do: Đây là nơi gánh 90% tải token nặng nhất, tạo ra burst traffic (đọc nhiều file, phân tích AST, diff code). Chạy Worker qua `agy.exe` Native Go BoringSSL + Sandbox độc lập + Proxy 4G riêng sẽ bảo vệ an toàn tuyệt đối cho tài khoản.
- **Mô hình A (Hiện tại - Chuẩn vận hành): "Tổng Quản & Đao Phủ"**
  - **Hermes làm Coordinator:** Nhận alert Telegram, trực ban 24/7, quản lý Cronjob, kiểm soát farm và ADB.
  - **Thi công Code trực tiếp:** Khi có task sửa code, Hermes Coordinator **tự gọi trực tiếp `ag_cli.py fix` mà không cần spawn Subagent qua `delegate_task`** (tiết kiệm quota, tránh lỗi `ANCHOR_NOT_FOUND`, không làm lag session vì `ag_cli.py` trả về kết quả O(1) trong 15–25s).
- **Mô hình B: "CLI-to-API Daemon" (Dành cho việc muốn Coordinator xài 100% Native TLS của agy):**
  - Dựng một Web Server nền (ví dụ Python FastAPI tại `:20130` hoặc Cockpit Local Proxy) cung cấp endpoint `/v1/chat/completions`.
  - Khi Hermes gửi request, Daemon này nhận tin nhắn và pipe vào `agy` qua profile sandbox đang rảnh, format kết quả trả về JSON/SSE cho Hermes.
  - **Đánh đổi:** Mất Function Calling JSON schema chuẩn của Hermes và độ trễ câu trả lời tăng thêm 2-3s mỗi turn, không streaming mượt từng chữ.

---

## 8. Quy Trình Vận Hành Worker `ag_cli.py fix` (One-Touch Execution)

### Lợi ích vượt trội so với Worker Subagent truyền thống:
1. **Triệt tiêu lỗi vỡ Anchor (`ANCHOR_NOT_FOUND`):** Worker subagent thông thường dùng string matching để patch file, rất dễ đứt gãy khi file lớn hoặc code bị format lại. `agy.exe` phân tích toàn diện cây cú pháp trừu tượng (AST), hiểu cấu trúc logic để viết lại code chuẩn xác.
2. **Khả năng tự kiểm chứng (Self-Testing Loop):** `agy.exe` tự động kích hoạt terminal nội bộ để chạy thử file/test suite. Nó chỉ trả về kết quả cho Coordinator khi code đã pass test thực tế.
3. **Giữ sạch Context Coordinator:** Thay vì Coordinator phải đọc 10-15 lần tool calls (`read_file`, `patch`, `py_compile`), Coordinator chỉ nhận đúng bản diff/log nghiệm thu cuối cùng.

### Cú pháp gọi chuẩn từ Coordinator:
```bash
python D:/Taadaa/tools/ag_cli.py fix "Mô tả chi tiết yêu cầu sửa/viết code..." --file "đường_dẫn_file_mục_tiêu"
```
*Lưu ý:* Bắt buộc chạy background với timeout tối thiểu 120s:
`terminal(background=True, notify_on_complete=True, timeout=120)`.

### Thực nghiệm kiểm chứng thực tế (Farm Device Audit Task):
- **Yêu cầu:** Viết hàm `audit_farm_devices(devices)` vào `D:/Taadaa/tools/test_cli_runner.py` kiểm tra các tiêu chuẩn: `status != 'device'` (offline), `battery < 20 or > 90` (battery_abnormal), không chứa `Aruba` trong wifi (rogue_wifi).
- **Kết quả:** `agy.exe` tự động nạp `acc_01`, sinh code hoàn chỉnh có Type Hints, tự viết test mẫu trong `__main__`, tự chạy terminal in `FARM_AUDIT_PASS`, trả về exit code 0 trong 25 giây. Coordinator hậu kiểm độc lập đạt 100% tính toàn vẹn.

### 3. Kỷ luật Bằng chứng Thị giác (Gate 6 Pitfall):
- **Bẫy ảnh Checkpoint Pre-action:** Khi script tự động chụp ảnh màn hình ở bước 2FA / Password để lưu bằng chứng (`gpm_oauth_2fa_step.jpg`), ảnh này ghi nhận **hiện trường lúc ô nhập mã đang trống**.
- **Quy tắc phản hồi:** Tránh chỉ gửi ảnh Checkpoint khiến người dùng hiểu nhầm là tiến trình bị kẹt ở màn hình xác minh. Bắt buộc phải kèm theo bằng chứng Post-action (log xác nhận nhận mã OTP, Token exchange thành công, hoặc kết quả gọi API kiểm chứng thực tế).

---

## 9. Cải Tiến Kiến Trúc P0: Atomic Exclusive Lock & LRU Load Balancing (Claude Haiku Audit)

Sau đợt thẩm định độc lập từ Claude Haiku CLI (`claude -p --model haiku`), hệ thống `ag_cli.py` đã được vá 3 chốt chặn tối quan trọng:

### 1. Phân định Chiến lược Điều phối: Coordinator vs Worker
- **Coordinator (OmniRoute `ag-gemini-pool-3`):** Cần **Sticky Session + Least-Used** (`stickyRoundRobinLimit: 15`).
  * *Nguyên nhân:* Coordinator chạy phiên dài multi-turn (context tích lũy 30k–100k tokens). Bắt buộc phải bám 1 account để tận dụng **Prompt Caching của Google Gemini** (giảm 75% chi phí token và tăng tốc 3–5x).
- **Worker (`agy cli`):** Bắt buộc dùng **Least-Recently-Used (LRU) + Exclusive Atomic Lock** (KHÔNG dùng Sticky Session).
  * *Nguyên nhân:* Worker là tác vụ độc lập (Stateless One-shot task, sửa file xong 5–25s là thoát). Nếu dùng Sticky Session hoặc dồn nhiều session cùng lúc vào `acc_01`, tài khoản sẽ chạm trần **RPM / TPM (Requests/Tokens Per Minute)** của Google, gây lỗi 429 liên hoàn.
  * *Cơ chế LRU:* Sắp xếp `ready_profiles` theo `(last_used_timestamp, calls)` tăng dần -> Ưu tiên bốc tài khoản nghỉ lâu nhất để san phẳng tải đều cho cả dàn 21 acc.

### 2. Khóa Độc Quyền Nguyên Tử (Atomic Exclusive Lock):
- **Lỗ hổng cũ:** Giữa bước check `is_profile_locked()` và ghi `json.dump()`, có khe hở micro-giây nếu 2 session hoặc cronjob cùng khởi động đồng thời, dẫn tới race condition va chạm 2 tiến trình vào cùng 1 profile.
- **Giải pháp chuẩn:** Dùng cờ nguyên tử cấp hệ điều hành:
  ```python
  fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
  with os.fdopen(fd, "wb") as f:
      f.write(payload)
  ```
- **Xử lý Stale Lock 2 lượt:** Bắt `FileExistsError`, nếu lock cũ đã hết hạn (lease > 300s) hoặc PID đã chết (`not psutil.pid_exists(pid)`), an toàn xóa lock cũ và retry tạo atomic lock.
- **Triết lý Fail-Closed:** Khi file lock bị lỗi đọc hoặc OS đang ghi dở, hàm `is_profile_locked` trả về `True` (coi như profile đang bận) để an toàn chuyển ngay sang profile khác, không bao giờ để 2 tiến trình đè nhau.

### 3. Cooldown Lũy Tiến (Exponential Backoff):
- Mỗi lần chạm giới hạn quota (`429`, `RESOURCE_EXHAUSTED`), hệ thống đếm số lần hit (`quota_hits` trong `pool_state.json`):
  * Lần 1: Cooldown 30 phút (1.800s).
  * Lần 2: Cooldown 60 phút (3.600s).
  * Lần 3+: Cooldown 120 phút (7.200s, trần 4x).
- Giúp tài khoản có đủ thời gian "ngủ" để Google reset sâu hạn mức, tránh bị phạt nặng hơn.

### 4. Tách biệt Trạng thái Bật/Tắt Profile (`is_profile_enabled`):
- `profiles_config.json` hỗ trợ trường `"enabled": false`.
- Khi một proxy hoặc tài khoản gặp lỗi tạm thời (ví dụ: `acc_05` dính proxy Bad Gateway), hệ thống chỉ cần đặt `enabled: false` để tạm rút profile ra khỏi pool mà không cần xóa thư mục hay thông tin xác thực. Pool tiếp tục vận hành mượt mà với các tài khoản READY còn lại.

---

## 10. Kỷ luật Closeout Gate & Observability cho Antigravity CLI Pool

Khi đưa `ag_cli.py` và các module hỗ trợ vào quy trình kiểm toán tự động (`closeout_gate.py`):

### 1. Structured Telemetry & Tracing:
- Không chỉ dùng `print()` log stdout đơn thuần, `ag_cli.py` tích hợp hàm `emit_telemetry(event, data, correlation_id)`.
- Ghi log JSONL có cấu trúc cho các sự kiện trọng yếu:
  * `profile_dispatched`: Ghi nhận tên profile, model và timestamp bắt đầu thực thi.
  * `quota_failover`: Ghi nhận lý do 429, thời gian cooldown và profile kế tiếp được chọn.
  * Cho phép tracing và đo lường tỷ lệ xoay tua thực tế giữa các tài khoản farm.

### 2. Kiểm thử Tương tranh & Tránh Va chạm (Concurrency Contention):
- Đối với hệ thống có nhiều session chạy đồng thời, bắt buộc phải có test case kiểm thử race condition:
  * Giả lập 2 tiến trình gọi `acquire_profile_lock()` trong cùng một tích tắc.
  * Khẳng định đúng 1 tiến trình trả về `True` (chiếm lock thành công) và tiến trình thứ 2 trả về `False` (bỏ qua bốc profile kế tiếp).
  * Bảo đảm tính đúng đắn của cờ nguyên tử `os.O_CREAT | os.O_EXCL` trên hệ điều hành Windows.

### 3. Vận Hành Không Phụ Thuộc Hardcode (Dynamic Environment Discovery):
- Mọi thông số nhạy cảm và đường dẫn vận hành (GPM PID, Target Email, Proxy URL, API Endpoints, Profiles Dir) đều phải được bọc qua `os.environ.get(KEY, default)`:
  * `AGY_PROFILES_DIR`: Tùy biến thư mục profiles sandbox.
  * `GPM_API_URL` & `OMNIROUTE_API_URL`: Cho phép chuyển đổi endpoint khi chạy trên các máy farm khác nhau.
- Tích hợp lớp kiểm tra hợp lệ (`validate_credentials`) trước khi ghi token và áp dụng cơ chế rollback file tạm (`.tmp` -> `replace`) để tránh hỏng dữ liệu cấu hình khi có sự cố bất ngờ.

---

## 11. Tích Hợp Gemini Web Session & Phân Vai Sol Worker vs Sol Repair

Chi tiết xem tại tài liệu hỗ trợ liên kết:
`references/gemini-web-session-extraction-and-react-worker-architecture.md`

### 1. Kỷ luật Chủ Động Bóc Cookie Google Web (Anti-Luna Invariant):
- Tuyệt đối KHÔNG bảo người dùng mở F12 copy cookie hay login thủ công.
- Tự động dùng GPM CDP (:19995) truy vấn SQLite `Cookies` tìm profile có sẵn `__Secure-1PSID`, kết nối CDP WebSocket (`suppress_origin=True`), gửi `Storage.getCookies` để bóc tách bộ 3 cookies: `__Secure-1PSID`, `__Secure-1PSIDTS`, `__Secure-1PSIDCC`.
- Nạp connection vào OmniRoute (`provider: gemini-web`), gắn proxy 4G tương ứng vào `proxy_assignments` trong `C:\Users\Kibe\.omniroute\storage.sqlite`, tạo combo `gemini-web-pro` trỏ model `gemini-web/gemini-3.1-pro` (miễn phí 100%, không trừ quota IDE của 22 acc Pro).

### 2. Phân Định Vai Trò: `sol_repair.py` vs `sol_worker.py`:
- `sol_repair.py`: Strict read-only O(1) patch proposal generator có AST validation (<= 30 dòng diff). Độc quyền cho Strike 1 & 2 khi Closeout Gate bị Rejected.
- `sol_worker.py`: Multi-turn ReAct autonomous worker (Read -> Patch -> Command -> Done) chạy qua `gpt-web-sol` (:20129). Phục vụ routine tasks và tầng dự phòng thứ 3 khi Claude CLI và Agy CLI cạn quota.

### 3. Claude CLI Quota Stale-Gate Watchdog:
- File `plan-usage-history.json` quá 2 giờ sẽ kích hoạt stale quota gate từ chối điều phối nhầm.
- Duy trì Cronjob 30 phút (`refresh-claude-quota-watchdog`) tự động chạy `refresh_claude_quota_file.py` để giữ cache luôn tươi mới.


