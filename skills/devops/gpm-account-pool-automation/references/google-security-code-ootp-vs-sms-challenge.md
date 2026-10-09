# Phân Biệt Màn Hình Xác Minh 2 Bước Google: Security Code (OOTP) vs SMS OTP & Đổi Tài Khoản Trên S7

## 1. Triệu chứng & Bẫy nhầm lẫn tai hại (Pitfall Nhập Nhầm SĐT Vào Ô Nhập Mã)
- **Hiện tượng**: Màn hình đăng nhập Google xuất hiện card xác minh với tiêu đề *"Xác minh 2 bước"*, văn bản hướng dẫn:
  > *"Nhận Galaxy S7 của bạn -> Mở ứng dụng Cài đặt -> Nhấn vào Google -> Quản lý Tài khoản Google của bạn -> Chọn tab Bảo mật -> Trong phần 'Đăng nhập vào Google', hãy nhấn vào Mã bảo mật -> Nhập mã"*
- **Bẫy nhầm lẫn**: 
  - Input field hiển thị placeholder/floating label: `"Nhập mã"` (hoặc `"Enter code"`), có selector `input[name="Pin"]`, `input#security-code-input`, `input[type="tel"]`.
  - **LỖI NGHIÊM TRỌNG**: Agent hoặc runner thấy `input[type="tel"]` hoặc URL có challenge liền nhận nhầm là "màn hình yêu cầu điền số điện thoại", sau đó fill số điện thoại (ví dụ: `0906746624`) vào ô này và bấm Tiếp theo -> Google báo lỗi đỏ rực: `"Sai mã. Hãy thử lại."` (Wrong code. Try again) hoặc script chuyển trạng thái nhầm sang `AWAITING_SMS_OTP`.
  - **Quy tắc code trong pipeline**: Tuyệt đối KHÔNG bắt `input[type="tel"]` chung chung khi đang ở luồng `challenge/ootp` hoặc khi DOM có placeholder/text "Nhập mã" / "Mã bảo mật". Chỉ trigger nhánh điền SĐT khi URL thực sự là `challenge/iap` hoặc trang có text yêu cầu nhập số điện thoại để nhận SMS ("nhập số điện thoại", "tin nhắn văn bản cùng mã xác minh").
  - Đây KHÔNG phải là màn hình gửi SMS, mà là màn hình yêu cầu **Mã bảo mật offline 10 chữ số (Google Security Code - challenge/ootp)** được tạo trực tiếp từ thiết bị Android Samsung S7!

## 1.1. Xử Lý Màn Hình Google Identity Verification Đòi Xác Nhận Số Điện Thoại Đuôi 24 (Tad)
- **Hiện tượng**:
  - Màn hình hiển thị: *"Xác minh danh tính của bạn -> Nhận mã xác minh tại ••••••••24 -> Nhận cuộc gọi đến số ••••••••24"* hoặc sau khi click chọn gửi SMS sẽ hiện:
    > *"Nhận mã xác minh: Để có được mã xác minh, đầu tiên hãy xác nhận số điện thoại bạn đã thêm vào tài khoản của mình ••••••••24. Bạn có thể phải trả cước phí tin nhắn và dữ liệu tiêu chuẩn."*
  - UI có ô nhập: `input[type="tel"]#phoneNumberId` hoặc `input[name="phoneNumber"]` và nút `Gửi` (Send).
- **Quy tắc an toàn Farm & User Instruction**:
  - **SĐT đuôi 24 là số cá nhân của Tad (User)**.
  - Khi gặp màn hình này:
    1. BẮT BUỘC KHÔNG ĐƯỢC TỰ ĐỘNG BỊA NGUYÊN NHÂN LÀ TIMEOUT/NGHẸN MẠNG. Phải chạy OCR đọc nội dung ảnh để xác nhận.
    2. Nếu chưa có số điện thoại đầy đủ: Hỏi user để xin số đầy đủ điền vào ô xác nhận để Google phát mã OTP về máy user.
    3. Sau khi bấm "Gửi", Google sẽ chuyển sang màn hình nhập mã OTP 6 số (`input#idvPin` hoặc `input[name="Pin"]`). Runner tạo file chờ `C:\Users\Kibe\waiting_otp.json` và polling file `C:\Users\Kibe\otp_code.txt` trong 120s-180s để user đưa mã nạp vào.
    4. Nếu gặp số điện thoại lạ không phải đuôi 24 của user: Đánh dấu `SMS_CHECKPOINT` và ngâm 24-48h, tuyệt đối không spam request làm khóa tài khoản vĩnh viễn.

### Bắt Bệnh O(1) Khi User Hỏi "Máy nào / Script nào vừa gửi mã Google về SĐT":
1. **Kiểm tra file chờ OTP ngay lập tức**: `C:\Users\Kibe\waiting_otp.json`. File này lưu trực tiếp `email`, `mid` (mã máy), `phone`, `status`, timestamp và ảnh màn hình checkpoint.
2. **Kiểm tra tiến trình đang chạy**: `powershell "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_oauth_s7_pipeline*' } | Select ProcessId, CommandLine"`.
3. **Đối chiếu Master Excel**: Tra cứu email trong `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`) để lấy chính xác số Máy, Model máy, Serial ADB.
4. **Cơ chế Chống False-Alert Đòi OTP SĐT 24 (Strict Anti-False-Alert Gate)**:
   - **Bẫy False Alert (Nguyên nhân làm phiền User)**:
     Khi Google hiển thị màn hình yêu cầu mã bảo mật S7 10 số (`challenge/ootp` hoặc header "Get your Galaxy S7..."), ô nhập mã thường mang thuộc tính `name="Pin"`, `type="tel"`, hoặc `id="security-code-input"`.
     Nếu script bắt chung selector `Pin` hoặc `type="tel"` trước khi loại trừ S7, nó sẽ nhầm tưởng Google đã gửi SMS về số cá nhân đuôi 24 của User và bắn Farm Alert Telegram đòi OTP!
   - **Chốt chặn bắt buộc (`is_real_sms_24_challenge`)**:
     Chỉ được phép kích hoạt alert SMS 24 khi thỏa mãn đồng thời cả 3 điều kiện:
     1. `not is_s7_sec`: URL không chứa `challenge/ootp` VÀ text không chứa các từ khóa thiết bị (`"galaxy s7"`, `"security code"`, `"mã bảo mật"`, `"get your galaxy"`, `"use your phone"`).
     2. Text hiển thị thực tế trên body phải có số đuôi của User (`"••24"` hoặc `"24"`).
     3. Phải có từ khóa xác nhận gửi SMS bằng regex biên từ: `re.search(r"(tin nhắn|text message|gửi mã|verification code|mã xác minh|\bsms\b)", body_lower)`.
     Thiếu bất kỳ điều kiện nào -> TUYỆT ĐỐI CẤM gọi `send_telegram_otp_alert` và CẤM tạo `waiting_otp.json`.
5. **Thứ tự ưu tiên Challenge Selection chuẩn hóa (`classify_s7_challenge_selection`)**:
   - Tại màn hình chọn phương thức (`challenge/selection`), thứ tự ưu tiên bắt buộc:
     1. `TOTP`: Google Authenticator (100% tự động nội bộ qua secret key).
     2. `PROMPT`: Google Prompt trên S7 (bấm "Có" / "Yes" qua ADB).
     3. `S7_SECURITY_CODE`: Mã bảo mật S7 10 số (trích xuất qua ADB Google Play Services).
     4. `FARM_SMS`: SIM gắn trên Farm.
     5. `PHONE24_SMS`: SĐT đuôi 24 của User — **CHỈ ĐƯỢC CHỌN KHI TUYỆT ĐỐI KHÔNG CÒN CÁCH NÀO KHÁC**.
6. **Kỷ luật Farm Safety khi thiết bị S7 hết hạn phiên (Session Expired)**:
   - Khi điều hướng lấy mã trên S7, nếu phát hiện màn hình `"phiên của bạn đã kết thúc"` hoặc `"chưa đăng nhập"`:
     TUYỆT ĐỐI CẤM dùng ADB shell gõ mật khẩu mù (`input text <pwd>`) vào EditText vì dễ lệch layout hoặc lộ mật khẩu.
     BẮT BUỘC: Safe-exit ngay lập tức, trả về `None` để pipeline rơi vào `BLOCKED_S7_CODE_FAILED` kèm `reason="SESSION_EXPIRED_OR_NO_CODE"` và ghi structured telemetry. Cấm chuyển nhầm sang alert SMS 24.
7. **Defensive Locator trong Playwright**:
   - Khi quét các option challenge, luôn bọc trong hàm phòng thủ `_is_loc_ready(loc)` với `try...except` quanh `.count()` và `.is_visible()` để tránh Playwright nổ runtime error làm đứt gãy luồng điều phối.
8. **Pitfall Nghịch Đảo Thứ Tự Ưu Tiên (Priority Inversion Trap)**:
   - Trong `run_oauth_s7_pipeline.py`, tại màn hình `challenge/selection`, nếu `phone24_opt` được check TRƯỚC `totp_secret`, runner sẽ click xin SMS về SĐT user dù tài khoản đã có sẵn TOTP secret trong Excel.
   - BẮT BUỘC: Luôn ưu tiên `totp_opt` (Google Authenticator) lên hàng đầu khi `totp_secret` tồn tại. Chỉ fallback về Phone 24 khi không có TOTP secret.
5. **CẤM IM LẶNG KHI XIN MÃ OTP SĐT 24 (Silent Polling Anti-Pattern & Hot-Inject Re-run Flow)**:
   - **Vấn đề**: Khi runner bấm xin SMS về SĐT 24, nếu chỉ ghi `waiting_otp.json` rồi ngồi chờ 180s trong im lặng mà không báo Telegram, user nhận SMS sẽ hoàn toàn không biết tài khoản nào/máy nào gửi. Sau 180s script timeout và tự đóng profile, lãng phí lượt SMS và khiến user ức chế ("Ủa thì phải báo t đưa mã chứ im im sao mà biết. Profile đó còn mở k").
   - **Kỷ luật điều phối & Hook cảnh báo**:
     - Khi runner trigger gửi SMS về SĐT 24: BẮT BUỘC bắn alert Telegram ngay lập tức qua hàm `send_telegram_otp_alert(email, mid, shot_path, correlation_id)`.
     - **Quy chuẩn Architecture & Anti-Hardcode**:
       - Tuyệt đối KHÔNG hardcode chat_id fallback `"-5373649734"` rải rác trong scripts. Nguồn cấu hình alert duy nhất là `automation_core.alerts.DEFAULT_ALERT_CHAT_ID` (tự nhận diện máy Kibe vs Admin), fallback duy nhất là biến môi trường `TELEGRAM_ALERT_CHAT_ID`.
       - Tách biệt logic lấy cấu hình (`get_alert_config`) và định dạng nội dung thông báo (`format_otp_alert_caption`) để dễ bảo trì và test độc lập.
       - Chuẩn hóa `correlation_id` xuyên suốt toàn bộ lifecycle của tài khoản:
         ```python
         # Sinh 1 session correlation_id duy nhất trong process_account:
         session_correlation_id = f"m{mid:02d}_{int(time.time())}"
         send_telegram_otp_alert(email, mid, shot_path, correlation_id=session_correlation_id)
         captured_code_res, otp_code = wait_for_otp_or_code(mid, otp_file, waiting_file, lambda: captured_code, timeout=180, correlation_id=session_correlation_id)
         ```
       - Cả `send_telegram_otp_alert` và `wait_for_otp_or_code` đều nhận `correlation_id: str = ""` và chuẩn hóa fallback:
         ```python
         cid = correlation_id or f"m{mid:02d}_{int(time.time())}"
         ```
         Mọi dòng log telemetry (bắt code, đọc file, dọn file tạm, gửi Telegram) đều gắn `correlation_id={cid}` thống nhất, không dùng `mid` trần làm mất tính liên kết trace.
     - **Kỷ luật Unit Test cho Alert & Automation Pipeline (`test_run_oauth_s7_pipeline.py`)**:
       - Mọi hàm gửi alert Telegram phải có unit test độc lập dùng `pytest` + `unittest.mock` bao phủ 100% các nhánh:
         1. *Photo alert success*: Mock file ảnh tồn tại, `requests.post` trả về HTTP 200 -> assert endpoint gọi `/sendPhoto`, data chứa chat ID và files có ảnh.
         2. *Text alert success*: Không có file ảnh -> assert endpoint gọi `/sendMessage`.
         3. *Network / HTTP exception*: `requests.post` nổ `RequestException` -> bắt ngoại lệ an toàn, log warning, tuyệt đối không làm crash luồng chính.
         4. *Token missing*: Không có token trong `.env` hay env var -> return sớm an toàn, không gọi `requests.post`.
         5. *Correlation ID trace test*: Xác nhận `wait_for_otp_or_code` và `send_telegram_otp_alert` propagate đúng `correlation_id` vào log telemetry và payload.
         6. *Playwright BrowserContext Integration test*: Giả lập `BrowserContext` chuẩn Playwright (`pages`, `new_page`, `close`) để xác minh các module cắm ngoài như `trigger_hot_chatgpt_oauth` tương thích hoàn toàn, không gây rò rỉ context hoặc xung đột lifecycle với runner.
     - **Quy trình Hot-Inject Re-run khi profile đã đóng**:
       1. Dọn dẹp cờ cũ: Xóa `C:\Users\Kibe\waiting_otp.json` và `C:\Users\Kibe\otp_code.txt`.
       2. Chạy lại pipeline nền: `python "D:\Taadaa\GPM auto\scripts\run_oauth_s7_pipeline.py" <target_email>`.
       3. Polling log/file đến khi xuất hiện trạng thái `WAITING_OTP`.
       4. Gửi ngay ảnh màn hình `MEDIA:<shot_path>` về Telegram yêu cầu user gửi mã 6 số.
       5. Ngay khi user gửi mã: Ghi vào `C:\Users\Kibe\otp_code.txt` để pipeline fill và submit form trước khi hết hạn 180s.
6. **BẪY KẸT VÒNG LẶP CHỜ OTP KHI USER NHẬP TRỰC TIẾP (Manual Input & Early Break Trap)**:
   - **Hiện tượng**: User thấy SMS OTP gửi về máy nên đã tự nhập mã trực tiếp trên cửa sổ trình duyệt Chromium đang mở. Google phê duyệt và chuyển hướng sang URL callback bắt được `Authorization Code` (`captured_code`).
   - **Bẫy code**: Vòng lặp chờ OTP `while time.time() - start_wait < 180` chỉ chăm chăm kiểm tra file `otp_code.txt`. Vì user nhập trực tiếp trên web nên file `otp_code.txt` không bao giờ xuất hiện -> Script tiếp tục chờ đủ 180 giây rồi nhảy vào nhánh `else:` kết luận `SMS_TIMEOUT` và đóng profile, vứt bỏ toàn bộ mã xác thực vừa bắt được!
   - **Khắc phục chuẩn hóa**:
     - Trong vòng lặp chờ OTP, BẮT BUỘC chèn điều kiện:
       ```python
       while time.time() - start_wait < 180:
           if captured_code:
               logger.info(f"[M{mid:02d}] 🎉 Bắt được Authorization Code trong lúc chờ OTP (user đã tự thao tác)!")
               break
           if os.path.exists(otp_file):
               # ... read and validate otp_code ...
               break
           time.sleep(1)
       ```
     - Ngay sau vòng lặp: nếu `captured_code` đã có, dọn sạch `waiting_otp.json` / `otp_code.txt` rồi tiếp tục luồng (`continue`) để sang bước `requests.post(.../exchange)`:
       ```python
       if captured_code:
           try:
               if os.path.exists(otp_file): os.remove(otp_file)
               if os.path.exists(waiting_file): os.remove(waiting_file)
           except Exception:
               pass
           continue
       ```
7. **CẨN TRỌNG TÊN BIẾN PLAYWRIGHT BROWSER CONTEXT (ctx vs context)**:
   - Trong Playwright persistent context (`ctx = p.chromium.launch_persistent_context(...)`), khi gọi các module phụ trợ (như `trigger_hot_chatgpt_oauth(page, ctx, ...)`), phải truyền đúng biến `ctx`.
   - Nếu truyền `context` sẽ nổ `NameError: name 'context' is not defined`, làm ngắt pipeline ngay sau khi OAuth Google thành công và không kịp ghi nhận trạng thái vào database/status json.

## 2. Quy trình bóc tách mã 10 số trên Samsung Galaxy S7 qua ATX-Agent
Khi tài khoản dính `challenge/ootp`, thiết bị Android chứa tài khoản mục tiêu (được gán trong farm) có thể tạo mã xác minh một lần (offline, hiệu lực 15 phút).

### Bước 1: Mở mục Cài đặt Google trên S7 (Fast-Path O(1))
- **CẢNH BÁO**: Trên Samsung Galaxy S7 (Android 7), lệnh cũ:
  ```bash
  am start -n com.google.android.gms/.app.settings.GoogleSettingsLink
  ```
  thường kích hoạt nhầm Activity `"Tự động điền bằng Google"`, làm kẹt toàn bộ chuỗi tìm kiếm tab Bảo mật!
- **Đường dẫn chuẩn hóa O(1)**:
  1. Mở Cài đặt hệ thống:
     ```bash
     am start -a android.settings.SETTINGS
     ```
  2. Vuốt lên 1 nhịp:
     ```bash
     input swipe 500 1500 500 400
     ```
  3. Tap vào mục **Google** (`Cài đặt Google`): tọa độ `(400, 580)`.

### Bước 2: Chuyển đổi sang đúng tài khoản mục tiêu (Fast-Path O(1))
- Sau khi vào màn hình `"Các dịch vụ của Google"`, nếu avatar/header đang hiển thị tài khoản mục tiêu (`target_email`):
  1. Tap vào khung tài khoản: tọa độ `(400, 850)`.
  2. Màn hình bung menu với nút **"Tài khoản Google"** (`bounds [276,648][715,792]`): Tap tọa độ `(490, 720)`.
  3. Màn hình trang Tài khoản hiển thị ngay mục **"Mã bảo mật"** (`bounds [252,798][516,870]`): Tap tọa độ `(400, 830)`.

### Bước 3: Kiểm tra dropdown tài khoản trên màn hình Mã bảo mật & Lấy mã
- **CỰC KỲ QUAN TRỌNG (Multi-Account Dropdown Trap)**:
  - Trên Android 7, ngay cả khi vừa mở từ tài khoản mục tiêu, màn hình *"Dịch vụ Google Play - Mã bảo mật của bạn"* vẫn có thể hiển thị mặc định tài khoản khác (ví dụ tài khoản đầu tiên của máy).
  - Kiểm tra node TextView hiển thị email dưới tiêu đề "Dịch vụ Google Play" (`bounds [216,159][792,224]`):
    - Nếu email khác `target_email`, tap vào email header này `(500, 190)` để mở dropdown popup danh sách tài khoản.
    - Trong popup dropdown, tìm node có text chứa `target_email` và tap vào (ví dụ `(500, 430)`).
    - **BẮT BUỘC SLEEP 2.0s - 2.5s**: Phải chờ Google Play Services refresh UI và cập nhật 2 mã 10 số mới trước khi dump XML lại.
- Màn hình sẽ hiển thị 2 mã 10 số:
  - **Mã 1** (ví dụ: `8479 325 720`)
  - **Mã 2** (ví dụ: `7761 187 613`)
- Bóc tách chuỗi số, lọc bỏ dấu cách và các ký tự unicode ẩn (`\u202d`, `\u202c`), lấy chuỗi 10 chữ số sạch: `8479325720`.
- Điền mã 10 số vào ô `"Nhập mã"` trên trình duyệt PC và nhấn Enter / Tiếp theo để hoàn tất xác minh danh tính.

## 3. Quản Lý Pool OmniRoute (:20129) & Xử Lý Badge "Business" Màu Vàng

### Hiện tượng nhãn "Business" (Warning vàng) trên Dashboard
- **Triệu chứng**: Giao diện OmniRoute hiển thị một loạt accounts Antigravity/Gemini có tag **"Business" màu vàng khè**.
- **Bản chất code UI**:
  - Tại `src/app/(dashboard)/dashboard/usage/components/ProviderLimits/utils.tsx`:
    ```typescript
    if (upper.includes("BUSINESS") || upper.includes("STANDARD") || upper.includes("BIZ"))
      return { key: "business", label: "Business", variant: "warning", rank: 5, raw };
    ```
  - Khi Google API trả về gói cá nhân `standard-tier` (Antigravity default tier), parser bắt chuỗi `"STANDARD"` và tự động gán nhãn `"Business"` với kiểu hiển thị `variant: "warning"` (màu vàng).
  - **Kết luận**: Đây là nhãn hiển thị phân cấp tier bình thường của OmniRoute, **KHÔNG PHẢI LỖI** và không ảnh hưởng đến khả năng gọi API của tài khoản. Tài khoản vẫn phục vụ chat completions 200 OK.

### Ưu tiên nạp tài khoản Farm S7: TOTP Authenticator vs Mã S7 10 số
- **Chiến lược tối ưu**: Khi nạp mở rộng pool Antigravity/Gemini vào OmniRoute:
  - Tài khoản chỉ có xác thực S7 (Google Prompt / Security Code 10 số): Dễ bị Google từ chối do lệch session Play Services hoặc bị checkpoint bắt ngâm 24h.
  - **Ưu tiên hàng đầu**: Quét bảng tính master lấy các tài khoản đã bật **2FA TOTP (Google Authenticator 6 số)**. Runner tự động tính mã qua `pyotp.TOTP(secret).now()` và điền thẳng vào ô xác thực trên PC -> 100% tự động, ổn định tuyệt đối và không phụ thuộc vào màn hình thiết bị S7.

## 4. Phân Biệt 2 Script OAuth & Bản Chất Cooldown Google (Tránh Nhầm Lẫn Điều Phối)
> **Chi tiết bẫy Recovery Email Challenge**: Xem `references/google-recovery-email-challenge-and-unavailable-options.md` (Xử lý option bị khóa "Unavailable because of too many attempts", kỷ luật Form-First Invariant và fallback `thanhdatbui1995@gmail.com`).

### 4.1. Phân biệt & Liên thông `cron_gpm_oauth_full_pool.py` vs `run_oauth_s7_pipeline.py`
- **`cron_gpm_oauth_full_pool.py`**:
  - Là cronjob định kỳ chạy tự động quét pool GPM nạp lên OmniRoute.
  - **Liên thông S7 Security Code 10 số**: Tự động nhận diện `challenge/ootp` hoặc `challenge/selection` (option 8 - Mã bảo mật trên điện thoại), trích xuất `machine_id` và `serial` qua `CredentialLookup`, gọi `get_s7_security_code(machine_id, serial, email)` từ S7 qua ADB để điền mã 10 chữ số offline, tránh bị Google đẩy vào Cooldown 72h.
- **Nối Nurture sau Login (`post_evening_gpm_login_watchdog.py`)**:
  - Ngay sau khi login Gmail thành công (GroupId = 10), lập tức nối tiến trình nền gọi `cron_gpm_gmail_nurture.py --email <email>` lướt YouTube / Google News 90-120s để tăng Trust Score tự nhiên trước khi bước vào chu kỳ OAuth.
- **`run_oauth_s7_pipeline.py`**:
  - Là pipeline chuyên dụng **PHỐI HỢP TRỰC TIẾP GIỮA GPM PC VÀ SAMSUNG S7 QUA ADB**.
  - Tự động bắt Google Prompt (`challenge/dp`) -> ADB duyệt nút "Có" + PIN trên S7.
  - Tự động bắt Mã bảo mật 10 số (`challenge/ootp`) -> ADB vào Cài đặt Google Play Services trên S7 bốc mã 10 số điền vào PC.
  - **Quy tắc điều phối**: Khi xử lý các tài khoản biết rõ đang còn LIVE trên máy S7, Coordinator BẮT BUỘC dùng `run_oauth_s7_pipeline.py` (hoặc lệnh canary 1 máy), CẤM nhầm lẫn cho chạy `cron_gpm_oauth_full_pool.py` rồi báo bế tắc đòi người dùng bấm tay!

### 4.2. Bản chất Cooldown Google: Khi Nào Ngâm Cứu Được vs Khi Nào Ngâm Vô Nghĩa?
- **Ngâm Cooldown (72h - 7 ngày) CỨU ĐƯỢC 100%**:
  - Khi dính lỗi **Rate-limit IP** hoặc **Sensitive Action (`signin/rejected?rrk=77`)**: Google tạm khóa tính năng do phát hiện nhiều thao tác nhạy cảm liên tiếp. Sau 48h - 72h - 7 ngày hạ nhiệt, điểm rủi ro (Risk Score) tự động reset về 0, mở lại bình thường (đã chứng minh cứu thành công 10/10 tài khoản M42, M58, M69, M64...).
- **Ngâm Cooldown HOÀN TOÀN VÔ NGHĨA (ĐÉO BAO GIỜ TỰ HẾT)**:
  - Khi dính lỗi **Phone Checkpoint (`challenge/iap` - bắt nhập số điện thoại để nhận SMS)**: Đây là cờ bảo mật cấp tài khoản (Account Security Flag) gắn vĩnh viễn trên server Google. Dù ngâm 14 hay 30 ngày mở lại vẫn trơ trơ màn hình đòi SĐT. Dạng này chỉ có 2 cách: nhập SIM nhận mã SMS hoặc dùng chính thiết bị gốc (S7) để khôi phục.
- **Tại sao Google không gửi Prompt về S7 khi mở trên GPM PC**:
  - Trên trình duyệt GPM PC điều khiển qua CDP, Google Enterprise reCAPTCHA đánh giá Risk Score cao ngay từ cửa sổ đầu tiên ("Xác nhận bạn không phải rô-bốt").
  - Google chặn cứng ở tầng Anti-bot, không bung `bframe` (audio) và không kích hoạt luồng push về S7. Bấm "Thử cách khác" bị đá sang trang từ chối đăng nhập. Muốn qua phải dùng proxy sạch hoặc pipeline phối hợp S7 đúng chuẩn.
