# Quy Tắc Ngâm Gmail (Soak Aging), Tự Động Cứu Phiên (Session Recovery) & An Toàn Thiết Bị S7

**Thời điểm chuẩn hóa:** 2026-09-25  
**Phạm vi áp dụng:** Hệ thống Gmail Farm Taadaa, GPMLogin Chromium, Samsung Galaxy S7 và các cronjob liên quan (`post_evening_gpm_login_watchdog.py`, `cron_gpm_gmail_nurture.py`, `run_oauth_s7_pipeline.py`).

---

## 1. Kỷ Luật Ngâm Gmail (Soak Aging) Trước Khi Lên GPM

### 1.1. Bản Chất Rủi Ro An Ninh Google (Risk-Based Authentication - RBA)
- **Chuyển dịch môi trường đột ngột:** Khi chuyển từ Android S7 (App Native, vi kiến trúc ARM, IP 4G) sang GPM Chromium trên Windows (x86_64, môi trường PC mới), Google kích hoạt cơ chế đánh giá rủi ro thiết bị mới.
- **Tài khoản non ngày (< 7 ngày tuổi):** Nếu mang lên GPM PC quá sớm, Google coi đây là hành vi bàn giao/mua bán acc tự động $\rightarrow$ **Ép thẳng vào Phone SMS Checkpoint (`challenge/iap`)**. Không có SIM thật là tài khoản chết đứng (DIE).
- **Tài khoản đã ngâm $\ge$ 7 ngày trên S7:** Google đã ghi nhận lịch sử đồng bộ mailbox và tương tác nền ổn định trên IP proxy của máy. Khi đăng nhập GPM qua đúng proxy 4G tương ứng, Google xếp vào nhóm *Trusted Session Transition*, cho phép đăng nhập mượt mà bằng mật khẩu.

### 1.2. Kiểm Tra Chặn Cứng Trong Code Thực Tế (`post_evening_gpm_login_watchdog.py`)
Hàm `get_candidates()` đối soát tuổi tài khoản qua 2 nguồn trước khi chọn:
```python
# 1. Bảng gmail_clean_v2.xlsx (Cột G - Ngày tạo):
if (d_today - c_date).days < 7:
    log(f"[CANDIDATE-FILTER] {em_l}: clean_map soak < 7 days ({(d_today - c_date).days}d)")
    continue

# 2. Bảng master_gmail_manager.xlsx (Cột O - Ngày cập nhật):
if (d_today - d_updated).days < 7:
    log(f"[CANDIDATE-FILTER] {em_l}: master updated soak < 7 days ({(d_today - d_updated).days}d)")
    continue
```
*Nguyên tắc:* Tuyệt đối không nới lỏng hay bypass điều kiện 7 ngày này cho các tài khoản mới reg.

---

## 2. Quy Trình Tự Động Cứu Phiên Bị Rớt (Auto Session Recovery)

### 2.1. Phát Hiện Rớt Phiên Khi Nuôi (`cron_gpm_gmail_nurture.py`)
- Định kỳ mỗi 2 giờ, khi mở profile GPM để lướt YouTube / Google News, script kiểm tra các cookie bảo mật cốt lõi: `SID`, `SSID`, `HSID`, `SAPISID`.
- Nếu tìm thấy `< 2` cookie Google (phiên bị hết hạn hoặc đăng xuất):
  - Dừng phiên nuôi ngay lập tức để tiết kiệm tài nguyên.
  - Ghi cờ cảnh báo vào `gpm_gmail_nurture_state.json`: `"status": "NEEDS_LOGIN"`.

### 2.2. Xếp Hàng Ưu Tiên Số 1 (Priority 1) Trong Watchdog Ca Tối
- `post_evening_gpm_login_watchdog.py` đọc `gpm_gmail_nurture_state.json`.
- Mọi tài khoản có trạng thái `NEEDS_LOGIN` được gán:
  - `priority = 1`, `reason = "nurture_reported_needs_login"`.
  - **Bypass `seen_emails`**: Được phép thử lại trong ngày để kịp thời cứu phiên.
  - **Bypass `omniroute_success`**: Không bị chặn bởi cờ đã từng lên OmniRoute.
  - Đẩy lên đầu danh sách xử lý trước toàn bộ tài khoản mới.
- Sau khi đăng nhập lại thành công:
  - Cập nhật trạng thái `gpm_gmail_nurture_state.json` thành `"status": "LOGIN_RECOVERED"`.
  - Cập nhật profile GPM `GroupId = 10`.
  - Chuyển tài khoản sang trạng thái `GPM_SOAKING` để tiếp tục nuôi tự nhiên.

---

## 3. Xử Lý Khi Đăng Nhập Lại Bị Đòi SĐT (Phone Checkpoint `challenge/iap`)

Trong `run_oauth_s7_pipeline.py`:
1. **Thử Phương Thức Thay Thế Duy Nhất 1 Lần:**
   - Script tự động tìm nút *"Thử cách khác"* (`Try another way`) để chuyển sang:
     + Google Prompt ("Nhấn Có trên Samsung S7").
     + Mã bảo mật 10 số trên S7 (`challenge/ootp`).
     + Mã 2FA Authenticator TOTP.
2. **Kỷ Luật Fail-Fast Khi Google Ép Cứng SĐT Mới:**
   - Nếu không có phương thức thay thế hoặc đã bấm *"Thử cách khác"* mà Google vẫn giữ màn hình nhập SĐT mới:
   - **DỪNG NGAY LẬP TỨC (FAIL-FAST)**, cấm click thử liên tục (chống bị Google gắn cờ spam phá hủy dải IP proxy).
   - Tự động chụp ảnh màn hình lưu vào `SCREENSHOT_DIR` (`oauth_{email}_hard_phone_checkpoint_<ts>.png`).
   - Trả về `status = "PHONE_CHECKPOINT"`.
   - Ghi nhận vào `processed` trong ngày để không thử lại vô ích trong cùng ngày, nhường chỗ cho tài khoản khác và ngâm cooldown tiếp.
   - **Cấm Tuyệt Đối:** Cấm thuê SIM ảo ngoại (SMS pool quốc tế) để xác minh cho IP Việt Nam.

### 3.1. Bẫy Ngáo Phân Loại Nhầm Mã Bảo Mật S7 Thành SMS OTP (SMS vs Security Code Collision Trap) & Anti-False-Alert Gate
- **Hiện tượng alert ngáo:** Màn hình Google trên GPM PC hiện *"Verify it’s you: Get your Galaxy S7 -> Settings -> Google -> Manage your Google Account -> Security -> Security code -> Enter code"*, nhưng hệ thống lại phát Farm Alert Telegram:
  `⚠️ [FARM ALERT] [MÁY N] 📱 Google gửi mã xác minh SMS về SĐT đuôi 24 (Tad)! Vui lòng nhắn/nhập mã OTP 6 số (hạn 180s)`.
- **Căn nguyên cốt lõi:**
  1. **Trùng Selector `name="Pin"`:** Ô nhập Security Code ngoại tuyến trên Google Identity v3 mang thuộc tính `name="Pin"`, nhưng URL challenge không chứa chuỗi `"ootp"`. Bộ chọn SMS OTP lỏng lẻo (`input#idvPin, input[name="Pin"], input[name="idvPin"]`) đặt trước nhánh Security Code, dẫn đến việc `name="Pin"` kích hoạt luồng chờ SMS OTP ảo và bắn alert sai cho người dùng.
  2. **Bẫy Ưu Tiên Nhầm Phone 24 Trong Selection:** Tại màn hình `challenge/selection`, script cũ tìm `data-challengetype="9":has-text("24")` TRƯỚC S7 Prompt và S7 Security Code, khiến Google chủ động gửi SMS về máy Tad dù S7 và TOTP có sẵn!
- **Kỷ luật xử lý & Bộ 4 Chốt Chặn Bắt Buộc:**
  1. **Anti-False-Alert Gate (Cổng Xác Minh Bằng Chứng SMS 24 Thật Sự):**
     - CẤM TUYỆT ĐỐI gọi `send_telegram_otp_alert` nếu thiếu positive proof (`is_real_sms_24`).
     - Bắt buộc kiểm tra đồng thời:
       `is_real_sms_24 = not is_s7_sec and ("24" in b_txt_l or "••24" in b_txt_l) and any(w in b_txt_l for w in ["tin nhắn", "sms", "text message", "gửi mã", "verification code", "mã xác minh"])`
     - Bỏ `input[name="Pin"]` khỏi selector SMS OTP chung (chỉ giữ `input#idvPin, input[name="idvPin"]`).
  2. **Đảo Ngược Thứ Tự Ưu Tiên Trong `challenge/selection`:**
     - Đưa SĐT đuôi 24 xuống hàng cuối cùng (phương án đường cùng khi không còn cách nào khác).
     - Thứ tự ưu tiên chuẩn hóa:
       (1) Google Authenticator (TOTP) nếu có secret key trong sổ cái.
       (2) Google Prompt trên Galaxy S7 (`challenge/dp`, "Nhấn vào Có / Tap Yes").
       (3) Mã bảo mật Galaxy S7 (10 số, `challenge/ootp`, "Use your phone or tablet to get a security code").
       (4) SIM Farm (nếu có `phone_number`).
       (5) TUYỆT ĐỐI CUỐI CÙNG: SĐT đuôi 24 của Tad (chỉ click khi KHÔNG CÒN phương thức nào khác).
  3. **Tự Động Bốc Mã Qua ADB & Khắc Phục Lỗi Điều Hướng S7:**
     - Mọi màn hình `is_s7_sec == True` phải chuyển tiếp ngay vào `get_s7_security_code(mid, serial, email)` để lấy mã 10 số từ điện thoại thật, **TUYỆT ĐỐI CẤM** bắn alert đòi OTP từ User.
  4. **Fail-Safe Khi S7 Thất Bại:**
     - Nếu không lấy được mã từ S7, tự động bấm *"More ways to verify"* / *"Thử cách khác"* để chuyển sang Authenticator/phương thức khác, hoặc dừng an toàn với `status = "BLOCKED_S7_CODE_FAILED"`.
     - **CẤM TUYỆT ĐỐI** việc không lấy được mã S7 mà tự ý nhảy trôi sang alert đòi OTP số 24 của Tad.
  5. **Kỷ Luật Sol Auditor Closeout Gate & Structured Telemetry Rubric:**
     - Khi sửa luồng phân loại challenge và fallback S7 Security Code, Sol Reviewer chấm gắt gao tiêu chí Telemetry & Observability, Logic Test và An Toàn Code. Nếu thiếu, reviewer sẽ trừ điểm (xuống <85 REJECTED) với key findings:
       + *'chưa thấy bổ sung metric, event tracking hoặc audit detail cho việc phân tích tỷ lệ thành công/thất bại'*.
       + *'cần thêm test cho thứ tự fallback và các biến thể ngôn ngữ/UI'*.
       + *'injection tiềm tàng qua biến pwd truyền trực tiếp vào shell command'*.
       + *'xóa entry khỏi config/status mà không có justification / test chứng minh'*.
       + *'hàm classify được thêm để test nhưng không thấy gọi trực tiếp trong pipeline runtime'*.
     - **Chuẩn hóa Telemetry Logging**:
       Mọi nhánh phân nhánh challenge bắt buộc phát structured telemetry:
       `logger.info(f"[M{mid:02d}] [TELEMETRY] correlation_id={session_cid} event=S7_SECURITY_CODE_EXTRACTED status=SUCCESS code_len={len(code10)}")`
       `logger.warning(f"[M{mid:02d}] [TELEMETRY] correlation_id={session_cid} event=BLOCKED_S7_CODE_FAILED status=FAILED reason='Could not extract S7 security code and no fallback'")`
     - **Kỷ Luật Shell Injection Trong Lệnh ADB**:
       TUYỆT ĐỐI CẤM gom chuỗi shell có password: `adb shell "input ... && input text {pwd} && input keyevent 66"` (dễ bị shell injection khi mật khẩu chứa ký tự đặc biệt như `$`, `` ` ``, `;`, `&&`).
       BẮT BUỘC gọi từng lệnh argv riêng biệt:
       `subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "tap", str(x), str(y)], capture_output=True, timeout=5)`
       `subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "text", pwd], capture_output=True, timeout=5)`
       `subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "66"], capture_output=True, timeout=5)`
     - **Kỷ Luật Phạm Vi Commit (Code Surgery vs State Config)**:
       CẤM TUYỆT ĐỐI trộn lẫn việc xóa/sửa dữ liệu trạng thái (`oauth_pipeline_status.json`, cooldown records) vào chung commit sửa code logic automation. Sửa code chỉ commit đúng file code và test tương ứng; việc nhả cooldown cấu hình phải thực hiện riêng hoặc có test chứng minh rõ ràng.
     - **Kiến Trúc 2 Tầng Cho Challenge Selection (Detection vs Classification)**:
       Tách rời tầng quét DOM locator khỏi tầng quyết định nghiệp vụ:
       + `detect_challenge_options(page, totp_secret: bool, has_phone: bool)`: Quét và gom toàn bộ selector của các challenge vào `locs` dict, trả về `(avail_tuple, locs)`. Giúp hàm `process_account` cực kỳ tinh gọn, không nhồi nhét inline locator.
       + **Defensive Locator Check (`_is_loc_ready`)**: Trong `detect_challenge_options`, bọc kiểm tra `count()` và `is_visible()` trong `try...except Exception: return False` để tránh Playwright crash khi DOM bị thay đổi động giữa các frame render.
       + `classify_s7_challenge_selection(*avail)`: Hàm pure Python xác định thứ tự ưu tiên (TOTP -> Prompt -> S7 Code -> Farm SIM -> Phone 24).
       + Trong `process_account`: Bắt buộc gọi `avail, locs = detect_challenge_options(...)` và `choice = classify_s7_challenge_selection(*avail)`, sau đó dispatch click theo `locs.get(choice)`.
     - **Kỷ Luật Regex Word Boundary Cho Từ Khóa SMS**:
       TUYỆT ĐỐI CẤM kiểm tra substring lỏng lẻo `"sms" in text` vì dễ match nhầm câu phủ định hoặc chuỗi rác (như `"không có từ khóa sms"`).
       BẮT BUỘC dùng regex word boundary `\bsms\b`:
       `has_sms_keyword = bool(re.search(r"(tin nhắn|text message|gửi mã|verification code|mã xác minh|\bsms\b)", b_l))`
     - **Structured JSON Metric & Reason Tracking Cho Toàn Bộ Vòng Đời Challenge**:
       Bổ sung `log_telemetry_metric` dạng JSON schema cho cả sự kiện phát hiện & chọn challenge thành công lẫn nhánh thất bại (kèm trường `reason` rõ ràng như `NO_FALLBACK_AVAILABLE`, `NO_CODE_EXTRACTED`):
       `log_telemetry_metric("challenge_selected", {"machine_id": mid, "email": email, "correlation_id": session_cid, "status": choice})`
       `log_telemetry_metric("s7_security_code_failed", {"machine_id": mid, "email": email, "correlation_id": session_cid, "status": "BLOCKED_S7_CODE_FAILED", "reason": reason})`
     - **Bộ Unit Tests Focused Bắt Buộc Trong `tests/test_run_oauth_s7_pipeline.py`**:
       (a) Test `is_real_sms_24` gate: Verify các chuỗi text chứa `"galaxy s7"`, `"security code"`, `"mã bảo mật"` trả về `False` (không bao giờ alert). Chỉ trả về `True` khi text chứa `"••24"` và từ khóa gửi tin nhắn SMS thật sự.
       (b) Test Edge Cases: URL rỗng `""`, body rỗng `""`, `None`, body có số `"24"` nhưng không có từ khóa SMS -> Bắt buộc trả về `False`.
       (c) Test Selection Priority & Mapping: Verify thứ tự ưu tiên các selector và mapping của `detect_challenge_options` qua MockPage/MockLocator (cho cả trường hợp đủ quyền lẫn khi tất cả bị ẩn `avail == (False, False, False, False, False)`).
       (d) Test Fallback Blocker: Verify khi S7 trả về `None` và không có nút 'Thử cách khác' thì trả về đúng status `BLOCKED_S7_CODE_FAILED` kèm trường `reason`, log telemetry và JSON metric trong stderr, không được văng exception hay kích hoạt luồng SMS.
       (e) Test Device Error Branch & Expired Session Safety: Verify khi ATX dump XML trả về lỗi 500 hoặc rỗng, hoặc khi S7 báo hết hạn phiên nhưng tài khoản thiếu mật khẩu trong cache thì `get_s7_security_code` xử lý êm thuận và trả về `None` an toàn thay vì crash.

### 3.2. Kỹ Thuật Đọc Mã Bảo Mật Trên S7 (FLAG_SECURE & Session Expiry Triage & UI Layout S7)
- **Bẫy FLAG_SECURE (Ảnh Đen 12 Bytes):** Màn hình hiển thị mã bảo mật của Google Play Services (`com.google.android.gms`) bật cờ `FLAG_SECURE`. Lệnh `screencap` ADB sẽ chỉ ra file 12 bytes / ảnh đen rỗng. BẮT BUỘC trích xuất mã qua ATX-Agent / Accessibility hierarchy dump (`/dump/hierarchy`), strip ký tự Unicode định hướng `\u202d` / `\u202c` và khoảng trắng để lấy chuỗi 10 chữ số chuẩn `re.match(r"^\d{10}$", text)`.
- **Bẫy Điều Hướng Trên Google Settings S7 Mới (Account Card Popup Trap):**
  + Trên Google Play Services mới của S7, nút *"Tài khoản Google"* **KHÔNG hiển thị trên màn hình chính** của `GoogleSettingsLink`.
  + Nó nằm ẩn bên trong popup tài khoản: BẮT BUỘC tap vào thẻ tài khoản (`[60,758][204,902]`, content-desc mang text `"tài khoản và các chế độ cài đặt"` hoặc `@gmail.com`) để bung bottom sheet, sau đó mới tap nút *"Tài khoản Google"* (`[276,648][715,792]`).
  + Sau đó cuộn tìm `"Bảo mật và đăng nhập"` $\rightarrow$ cuộn tìm `"Mã bảo mật"` $\rightarrow$ kiểm tra spinner email nếu hiển thị tài khoản khác thì switch về đúng email mục tiêu $\rightarrow$ đọc mã 10 số.
- **Quy Trình Tự Động Cứu Phiên Hết Hạn Trên S7 (Session Expiry A-Z Recovery):**
  + Nếu S7 báo *"Bạn chưa đăng nhập / Phiên của bạn đã kết thúc vì không có hoạt động. Hãy thử đăng nhập lại"* hoặc *"Xác minh danh tính của bạn"*:
    1. Tap `THỬ LẠI` / `TIẾP THEO`.
    2. Tra cứu mật khẩu từ `master_gmail_manager.xlsx` (qua `CredentialLookup._cache` hoặc `get_creds(email)`).
    3. Nhập mật khẩu qua ADB: `adb -s <serial> shell input text '<password>'` và tap `TIẾP THEO` / Enter.
    4. Sau khi đăng nhập phục hồi, mở `com.google.android.gms/.app.settings.GoogleSettingsLink` $\rightarrow$ tap thẻ tài khoản $\rightarrow$ `Tài khoản Google` $\rightarrow$ vuốt sang tab `Bảo mật và đăng nhập` $\rightarrow$ `Mã bảo mật`.
    5. Nếu màn hình mã bảo mật hiển thị tài khoản khác, tap vào dropdown spinner chọn đúng email mục tiêu.
    6. Trích xuất 2 mã 10 số khả dụng (hiệu lực 15 phút), điền vào ô challenge `ootp` / `Pin` trên GPM browser.
- **Xóa Cooldown Oan Trong Cấu Hình:**
  + Khi tài khoản bị alert ngáo kích hoạt nhầm cơ chế chờ SMS OTP, script cũ có thể tự động ghi nhận vào `D:/Taadaa/GPM auto/config/oauth_pipeline_status.json` mục `cooldown_7days` với lý do `RATE_LIMIT_SMS_PHONE_24`.
  + Sau khi vượt challenge thành công, BẮT BUỘC xóa bỏ entry của tài khoản đó khỏi `cooldown_7days` để nhả cooldown ngay lập tức, đưa tài khoản về trạng thái sẵn sàng nuôi.

---

## 4. Xử Lý Khi Thiết Bị S7 Đang Bận Nuôi Hoặc Chạy Tác Vụ Khác

Để tránh phá vỡ phiên nuôi TikTok hoặc gây xung đột ADB trên máy thật, hệ thống áp dụng **Bộ 3 Cổng An Toàn (3-Gate Safety)** trong `post_evening_gpm_login_watchdog.py`:

1. **Cổng 1 — Device Lock Vật Lý (`is_machine_idle`):**
   - Quét thư mục `~/.codex/device-locks/`. Nếu tồn tại lock `machine_<mid>.*.lock.json` đang hoạt động $\rightarrow$ **SKIP NGAY**.
2. **Cổng 2 — Lịch Nuôi Manifest & Bộ Đệm 45 Phút (`MIN_IDLE_BUFFER_MIN = 45`):**
   - Đọc lịch phân ca trong `assignment-v1-*.json`.
   - Nếu máy S7 đang trong slot nuôi (`st <= now < et`) HOẶC **sắp bắt đầu slot nuôi mới trong vòng 45 phút tới** (`now <= st < now + 45m`) $\rightarrow$ **SKIP NGAY** để bảo vệ phiên nuôi.
3. **Cổng 3 — Trạng Thái ADB Online:**
   - Nếu serial máy không có trong danh sách `adb devices` $\rightarrow$ **SKIP NGAY**, log cảnh báo.

### Cơ Chế Nhả Hàng Đợi Tự Nhiên
- Khi một máy bị SKIP vì bận: **Tài khoản đó KHÔNG bị tính là lỗi (FAIL)**.
- Tài khoản vẫn giữ nguyên vị trí trong hàng đợi Priority 1.
- Watchdog ca tối quét lặp **5 phút / lần**. Khi máy S7 kết thúc phiên nuôi, nhả lock và thỏa mãn bộ đệm 45 phút, watchdog sẽ tự động bốc tài khoản đó lên xử lý mượt mà.
