# GPMLogin Local API, SQLite DB & Verification Quirks

## 1. GroupId 0 vs GroupId 1 & Tra cứu Profile trong GPMLogin
- **Tạo Profile qua API**: Endpoint `/api/v3/profiles/create` nhận payload với `"group_id": 1` (Group "All" trong UI).
- **Hiện tượng Profile bị 'ẩn' khỏi API listing**:
  - `GET /api/v3/profiles?per_page=...` có thể không trả về các profile có `GroupId = 0` (thường là profile tạo từ trước hoặc tạo bởi tool khác).
  - Do đó, nếu gọi API danh sách không thấy profile theo tên hoặc email, KHÔNG vội kết luận profile chưa tồn tại.
- **Tra cứu cứu cánh trực tiếp từ SQLite**:
  - Đường dẫn DB: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
  - Bảng: `profiles`
  - Lưu ý cấu trúc cột: SQLite dùng PascalCase (`Id`, `Name`, `ProfilePath`, `JsonData`, `GroupId`, `CreatedAt`, `UpdatedAt`).
    - *Bẫy*: Truy vấn `SELECT group_id` sẽ lỗi `sqlite3.OperationalError: no such column: group_id`. Phải dùng `GroupId`.
  - Kiểm tra profile nhanh bằng Python:
    ```python
    import sqlite3
    conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db')
    c = conn.cursor()
    c.execute('SELECT Id, Name, GroupId FROM profiles WHERE Name LIKE ?', (f'%{keyword}%',))
    matches = c.fetchall()
    conn.close()
    ```
- **Lấy thông tin và chạy profile khi đã có Id**:
  - Kể cả khi `GroupId = 0`, gọi `GET /api/v3/profiles/{Id}` và `GET /api/v3/profiles/start/{Id}` vẫn hoạt động bình thường qua GPM Local API.

## 2. Xử lý xác minh Google khi Samsung S7 Offline & Bẫy Vòng Lặp Vô Tận (Batch Starvation)
- **Kiểm tra trạng thái S7 trước khi login & Fail-Fast**:
  - Chạy `adb devices` kiểm tra serial thiết bị (ví dụ `ce061606c3322c1603` của Máy 35).
  - **Bẫy timeout ATX khi S7 Offline**: Nếu thiết bị không có trong `adb devices`, lệnh `adb forward` sẽ fail và các request gọi tới ATX port (`http://127.0.0.1:17xxx/dump/hierarchy`) sẽ bị từ chối kết nối (WinError 10061), mỗi lần retry tốn 6s-18s. Nếu gọi lại qua từng bước của vòng lặp login (20 steps), một tài khoản sẽ ngốn > 600s gây timeout toàn bộ batch!
  - **Quy tắc fail-fast trong `get_s7_security_code`**:
    1. Hàm `get_s7_security_code` phải kiểm tra nhanh qua `adb devices` trước khi làm bất kỳ thao tác forward/ATX nào. Nếu serial không online, return `None` ngay lập tức (< 0.05s).
    2. Trong luồng `login_google_account`: nếu trang rơi vào `challenge/ootp` (đòi mã S7) mà S7 đang offline, hoặc sau 2 lần liên tiếp không lấy được S7 code, PHẢI break vòng lặp và ghi nhận trạng thái `BLOCKED_S7_OFFLINE`, không được lặp lại 20 lần làm treo các máy tiếp theo trong batch.
  - Nếu S7 `ONLINE`: script có thể tự động lấy mã bảo mật cục bộ (Security Code 10 chữ số) qua `com.google.android.gms/.app.settings.GoogleSettingsLink`.
  - Nếu S7 `OFFLINE`: script không thể lấy S7 Security Code. Bắt buộc phải ưu tiên nhánh Recovery Email nếu có option. Nếu Google bắt buộc S7 Security Code mà S7 offline, chuyển ngay sang tài khoản kế tiếp.
- **IMAP OTP Fetch từ Recovery Email (`thanhdatbui1995@gmail.com`)**:
  - Host: `imap.gmail.com` (SSL port 993)
  - User: `thanhdatbui1995@gmail.com`
  - App Password: `zpxn wtmn bkgc adlc` (chú ý strip khoảng trắng thành `zpxnwtmnbgcadlc`)
  - Logic lọc mail: Tìm thư đến từ Google trong vòng 180 giây gần nhất, bỏ qua các thư tiêu đề cảnh báo bảo mật ("Security alert" / "Cảnh báo bảo mật"), trích xuất mã 6 chữ số regex `(?<!\d)(\d{6})(?!\d)`.
- **Nguyên tắc bất biến bảo vệ Phone Farm**:
  - TUYỆT ĐỐI CẤM truy cập `https://myaccount.google.com/device-activity`.
  - TUYỆT ĐỐI CẤM đăng xuất (sign out) phiên làm việc của các thiết bị Samsung Galaxy S7.

  ## 3. Google GlifWebSignIn (v3) Password Submission Quirk & Bẫy Kẹt Màn Hình Mật Khẩu
  - **Hiện tượng**:
    - Khi nhập email thành công, URL chuyển sang `https://accounts.google.com/v3/signin/challenge/pwd?...`.
    - Script điền mật khẩu qua `pass_inp.first.fill(password)`, sau đó click `#passwordNext` hoặc gõ `Enter`, nhưng trang web không hề submit hoặc trigger navigation.
    - Vòng lặp kiểm tra tiếp tục chạy qua nhiều step và trang vẫn giữ nguyên URL `challenge/pwd` với text "nhập mật khẩu của bạn". Cuối cùng phiên hết hạn và tự động chuyển hướng về `https://www.google.com/account/about/?hl=vi` dẫn đến đánh giá sai là `FAILED`.
  - **Nguyên nhân cốt lõi**:
    - Giao diện Google Sign-in GlifWebSignIn v3 sử dụng Web Components / LitElement. Selector `#passwordNext` thực chất là một container bọc ngoài (`<div id="passwordNext">...</div>`). Click trúng container này hoặc click khi form validation chưa kích hoạt sẽ bị nuốt event (silent drop).
    - Ngoài ra, việc dùng `fill()` thuần mà không có focus/delay đôi khi không kích hoạt sự kiện `input`/`change` trên custom input field của Google.
  - **Giải pháp xử lý triệt để**:
    1. **Focus & Nhập mật khẩu có trigger event**:
       ```python
       pass_inp = page.locator('input[type="password"], input[name="Passwd"], input[name="password"]').first
       pass_inp.wait_for(state="visible", timeout=20000)
       pass_inp.click()
       pass_inp.fill(password)
       page.keyboard.press("Tab") # Kích hoạt blur/change validation
       time.sleep(1)
       ```
    2. **Nhắm trúng thẻ `<button>` thực thụ bên trong container hoặc dispatch Enter**:
       ```python
       next_btn = page.locator('#passwordNext button, button:has-text("Tiếp theo"), button:has-text("Next")').first
       if next_btn.count() > 0 and next_btn.is_visible():
           next_btn.click(force=True)
       else:
           pass_inp.focus()
           page.keyboard.press("Enter")
       ```
    3. **Thăm dò và retry submit ngay trong vòng lặp**:
       - Nếu sau 2-3 step URL vẫn còn ở `challenge/pwd` mà không có thông báo lỗi sai mật khẩu (`wrong password`), script phải chủ động re-focus vào ô password và gửi lại phím `Enter` hoặc click lại nút `Tiếp theo` với `force=True`, tránh để bị trôi hết 15 bước dẫn đến timeout về trang `about/?hl=vi`.
    4. **Bẫy thứ tự kiểm tra sai mật khẩu trong vòng lặp (Inline Validation Trap)**:
       - Khi nhập sai mật khẩu, Google GlifWebSignIn v3 KHÔNG điều hướng khỏi URL `challenge/pwd` mà hiển thị thông báo ngay tại chỗ:
         *"Mật khẩu không chính xác. Hãy thử lại hoặc nhấp vào 'Bạn quên mật khẩu?' để xem các lựa chọn khác."* (hoặc tiếng Anh: *"Wrong password"*).
       - **Bẫy**: Nếu trong vòng lặp đặt khối `if "challenge/pwd" in current_url: ... continue` TRƯỚC khối quét text lỗi (`mật khẩu không chính xác` / `wrong password`), script sẽ liên tục bấm Enter / Next mỗi step, bỏ qua hoàn toàn việc phát hiện sai pass. Hết 15-20 step, Google tự động hủy phiên và redirect về `https://www.google.com/account/about/?hl=vi`, khiến hệ thống ngộ nhận là lỗi mạng hoặc lỗi click!
       - **Quy tắc**: BẮT BUỘC kiểm tra `body_text` chứa `"mật khẩu không chính xác"` / `"wrong password"` / `"incorrect password"` TRƯỚC khi thực hiện bất kỳ hành động retry submit nào.
    5. **Kiểm tra trạng thái tài khoản trên Samsung S7 qua ADB**:
       - Khi gặp lỗi sai mật khẩu trên Web, trước khi đánh dấu DIE, kiểm tra ngay trên S7 qua lệnh:
         `adb -s <serial> shell dumpsys account | grep -E "Account {"`
       - Nếu tài khoản vẫn hiện `Account {name=..., type=com.google}`, tài khoản vẫn hoàn toàn sống và đăng nhập trên S7 thật. Khi đó có thể tận dụng S7 để khôi phục/đổi mật khẩu an toàn.

## 4. Xóa Sạch Dữ Liệu OpenAI / ChatGPT Offline Trong GPM Profile (Bảo Toàn Session Google)
- **Mục đích**: Khi cần đăng ký lại hoặc làm mới tài khoản ChatGPT trên profile GPM mà không muốn tạo lại profile hay đổi fingerprint (tránh làm mất trust score của Cloudflare/Turnstile).
- **Nguyên tắc an toàn**: Không xóa toàn bộ browser profile. Chỉ xóa chọn lọc đúng các bản ghi của `openai.com` và `chatgpt.com`. Giữ nguyên 100% cookies của Google, YouTube, mạng xã hội.
- **Thực thi offline qua SQLite (Bắt buộc đóng Chrome trước khi chạy)**:
  1. `Default/Network/Cookies`:
     ```sql
     DELETE FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%';
     VACUUM;
     ```
  2. `Default/Login Data`:
     ```sql
     DELETE FROM logins WHERE origin_url LIKE '%openai%' OR origin_url LIKE '%chatgpt%';
     VACUUM;
     ```
  3. Xóa các thư mục IndexedDB liên quan:
     Xóa thư mục `Default/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb` và các thư mục IndexedDB khác mang tên `*chatgpt*` / `*openai*`.
- **Canary Rule**: Luôn tạo file backup `.bak_chatgpt` và chạy thử nghiệm trên 1 profile trước, mở `myaccount.google.com` kiểm tra tài khoản Google còn sống nguyên vẹn (live) và `chatgpt.com` hiện giao diện trắng đăng ký/đăng nhập mới trước khi áp dụng batch.

## 5. Xử Lý 2FA TOTP (`challenge/totp`) Trong Luồng Login Google & Kỷ Luật Multi-Worker
- **Bẫy thiếu bộ xử lý 2FA khi tài khoản đã bật Authenticator**:
  - Với các tài khoản Google đã có sẵn 2FA Secret trong Master Excel / Clean V2 (ví dụ Máy 36 `caoanh11092003@gmail.com`), sau khi nhập đúng mật khẩu, Google không chuyển về `myaccount.google.com` mà chuyển hướng sang `https://accounts.google.com/v3/signin/challenge/totp`.
  - Nếu hàm `login_google_account` chỉ xử lý `challenge/ootp` (mã S7) hoặc recovery OTP mà thiếu nhánh `challenge/totp`, script sẽ lặp qua 15 bước vô ích và timeout.
- **Bộ xử lý chuẩn cho TOTP**:
  ```python
  if "challenge/totp" in current_url or page.locator('input[type="tel"], input#totpPin, input#idvPinId').count() > 0:
      if account.get("2fa_secret"):
          totp_code = generate_google_totp(account["2fa_secret"])
          logger.info(f"Submitting 2FA TOTP: {totp_code}...")
          code_inp = page.locator('input[type="tel"], input#totpPin, input#idvPinId').first
          code_inp.fill(totp_code)
          time.sleep(1)
          page.keyboard.press("Enter")
          time.sleep(5)
  ```
- **Kỷ luật Multi-Worker vs Tuần tự khi xác thực Gmail**:
  - **Bẫy Race Condition trên hòm thư khôi phục dùng chung**:
    - Khi nhiều tài khoản farm cùng sử dụng chung một email khôi phục (ví dụ `thanhdatbui1995@gmail.com`), việc chạy song song các worker (multi-worker) sẽ khiến Google gửi nhiều email chứa mã xác minh cùng lúc về hòm thư trong vòng 1-2 phút.
    - Script đọc IMAP (`fetch_recovery_email_otp`) sẽ rất dễ bắt nhầm mã OTP của tài khoản khác, dẫn đến nhập sai mã xác thực và kích hoạt lập tức Google Phone SMS Checkpoint (`challenge/iap`).
    - **Quy tắc bất biến**: Khi các tài khoản mục tiêu sử dụng chung 1 email khôi phục hoặc dùng chung thiết bị ADB S7, BẮT BUỘC phải thực thi TUẦN TỰ từng tài khoản (1 proxy = 1 acc/buổi).
    - Chỉ được phép mở đa luồng (3-4 workers, stagger 10s) khi các tài khoản có email khôi phục hoàn toàn độc lập và thiết bị S7 phân tách riêng.

## 6. Xử Lý Google Prompt (challenge/dp), PIN Matching & Playwright Navigation Race Condition
- **Bẫy Playwright Navigation Race Condition**:
  - Khi script click nút chọn tài khoản Google (Account Chooser) hoặc click nút Submit, trình duyệt chuyển hướng ngay lập tức.
  - Nếu vòng lặp thăm dò tiếp tục gọi trực tiếp `page.content()` hoặc `page.inner_text("body")`, Playwright sẽ văng ngoại lệ:
    `playwright._impl._errors.Error: Page.content: Unable to retrieve content because the page is navigating and changing the content.`
  - **Giải pháp**: Bọc các phương thức đọc DOM bằng helper an toàn và try-except bên trong vòng lặp:
    ```python
    def safe_content(page):
        try: return page.content().lower()
        except Exception: return ""

    def safe_body_text(page):
        try:
            if page.locator("body").count() > 0: return page.inner_text("body")
        except Exception: pass
        return ""
    ```
- **Xử lý Google Prompt (`challenge/dp`) trên Samsung Galaxy S7 (TouchWiz / Android 8)**:
  - **Bẫy Thông báo Nhóm (Grouped Notifications)**:
    - Trên Android 8/TouchWiz, nhiều thông báo từ `Dịch vụ Google Play` sẽ bị nhóm lại với header `Dịch vụ Google Play` và badge `Tổng N thông báo`.
    - Nếu script tìm và tap vào node `Dịch vụ Google Play`, nó chỉ chạm vào header làm bung/thu gọn nhóm thông báo mà KHÔNG mở hộp thoại phê duyệt.
    - *Giải pháp*: Ưu tiên quét tìm node con cụ thể mang nội dung thông báo xác nhận (`Cho phép một ứng dụng truy cập dữ liệu của bạn trên Google?`, `Bạn đang cố đăng nhập?`, `Phê duyệt đăng nhập...`), hoặc tap nút `Mở rộng` (`desc: 'Mở rộng'`) rồi tap vào node thông báo bên trong.
  - **Bẫy Khớp Số PIN (PIN Matching / Number Challenge)**:
    - Khi giao diện PC hiển thị yêu cầu chọn số PIN (2 chữ số, ví dụ `74`), màn hình S7 sẽ hiện 3 nút số để chọn, KHÔNG hề có nút `Có` / `Yes`.
    - *Bẫy logic*: Nếu code chỉ trả về `True` khi tìm thấy nút `Có` (`found_yes = True`), luồng sẽ bị kẹt và timeout dù đã tap đúng số PIN.
    - *Quy tắc*: Khi `target_pin` được cung cấp và tìm thấy node hiển thị đúng `target_pin` trên điện thoại, tap vào số đó và coi như phê duyệt thành công ngay lập tức.
  - **Quy trình chuẩn điều hướng 'Mã bảo mật' (10 chữ số) trên Samsung S7 TouchWiz / Android 7-8**:
    - **Lối vào tối ưu**: Khởi chạy activity `am start -n com.google.android.gms/.app.settings.GoogleSettingsLink`.
    - **Kiểm tra / Chọn tài khoản**:
      - Nếu email hiện tại chưa đúng tài khoản mục tiêu: tap vào avatar hoặc nút có content-desc chứa `"Tài khoản và các chế độ cài đặt"` / `"@gmail.com"` để mở Account Picker, chọn email mục tiêu.
    - **Vào màn hình Quản lý Tài khoản**:
      - Tap nút `"Tài khoản Google"` (hoặc `"Google Account"` / `"Quản lý Tài khoản Google"`).
    - **Vào mục Bảo mật**:
      - Cuộn và tap mục `"Bảo mật và đăng nhập"` (hoặc tab/mục `"Bảo mật"` / `"Security"`).
    - **Vào Mã bảo mật**:
      - Cuộn xuống tìm và tap `"Mã bảo mật"` (hoặc `"Security code"`, mô tả `"Nhận mã một lần để xác minh rằng đó là bạn"`).
    - **Bẫy lệch tài khoản tại màn hình Mã bảo mật & Bộ chọn Spinner**:
      - Trên màn hình hiển thị Mã 1 và Mã 2, tài khoản được chọn có thể không phải email vừa thao tác ở ngoài (thường hiển thị email mặc định đầu tiên của máy).
      - *Giải pháp*: Quét xem email đang hiển thị trên thanh tiêu đề có khớp `target_email` không. Nếu không, tap vào `android.widget.Spinner` ở tiêu đề `[216,72][960,240]` để bung danh sách tài khoản và tap chọn đúng email mục tiêu.
    - **Trích xuất mã 10 số**:
      - Chuỗi text mã bảo mật thường chứa ký tự Unicode ẩn định hướng (`\u202d`, `\u202c`) và khoảng trắng (ví dụ `\u202d6495 273 552`).
      - Phải làm sạch: `re.sub(r"\D", "", text)` và kiểm tra `re.match(r"^\d{10}$", cleaned)`. Cả Mã 1 và Mã 2 đều hợp lệ.

  - **Bẫy Vòng Lặp Thụ Động (Passive Loop Timeout Pitfall) trên challenge/dp**:
    - Khi trình duyệt rơi vào `challenge/dp`, nếu script chỉ tìm và click nút *"Thử cách khác"* (`Try another way`) mà không chủ động kích hoạt phê duyệt trên S7, trang web sẽ đứng yên ở `challenge/dp`.
    - Sau 15-20 bước thăm dò, phiên đăng nhập Google hết hạn và tự động chuyển hướng về `https://www.google.com/account/about/?hl=vi`, dẫn đến kết luận sai là đăng nhập thất bại dù S7 vẫn đang ONLINE và đã nhận được thông báo `SIGN_IN_PROMPTS`.
    - *Quy tắc bắt buộc*: Khi phát hiện `challenge/dp` và thiết bị S7 đang ONLINE, script PHẢI lập tức gọi hàm phê duyệt S7 tự động (đánh thức màn hình -> kéo thanh thông báo `cmd statusbar expand-notifications` -> tap thông báo Google Play Services / Sign-in prompt -> tap "Có" / chọn PIN), TUYỆT ĐỐI KHÔNG chỉ ngồi chờ hoặc chỉ thử click "Thử cách khác".

  - **Xử lý Google Prompt (`challenge/dp`) & Phê duyệt trên S7**:
    - **Kiểm tra dialog mở sẵn**: Ngay sau khi bật sáng màn hình (`keyevent 26` + `keyevent 82`), kiểm tra xem dialog phê duyệt hoặc số PIN đã hiển thị sẵn chưa trước khi kéo notification bar xuống.
    - **Bẫy Thông báo Nhóm**: Kéo status bar (`cmd statusbar expand-notifications`). Nếu thông báo Dịch vụ Google Play bị gộp, tìm thông báo con chứa `"Bạn đang cố đăng nhập"` hoặc chứa `target_email`, hoặc tap nút `"Mở rộng"` (`desc: 'Mở rộng'`).
    - **Quy tắc Phê duyệt dứt điểm**:
      - Nếu PC có hiển thị 2 chữ số PIN (`target_pin`): Màn hình S7 sẽ hiện các nút số để chọn (không có nút "Có"). Ngay khi tap đúng nút số khớp `target_pin`, BẮT BUỘC ghi nhận thành công (`return True`) ngay lập tức và gửi `keyevent 3` về Home.
      - Nếu không có PIN (chỉ hỏi "Có phải bạn đang đăng nhập không"): Tìm nút `"Có"` / `"Yes"` / `"Có, tôi là người thực hiện"` / `"Có, đúng là tôi"`, tap và ghi nhận thành công.

## 7. Tra Cứu Mật Khẩu Lịch Sử Chéo (Excel Cross-Source Audit) & Khôi Phục Qua S7 Live Session
- **Hiện tượng**: Tài khoản trong `master_gmail_manager.xlsx` hoặc `gmail_clean_v2.xlsx` bị Google báo lỗi *"Mật khẩu không chính xác"*.
- **Các nguồn tra cứu mật khẩu lịch sử cần rà soát trước khi kết luận DIE**:
  1. `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7` vs Sheet `Master_All`): Đôi khi cột mật khẩu giữa 2 sheet bị lệch (ví dụ Máy 38: `Master_All` lưu `Ibhqkdygvmef`, trong khi `Kibe_Farm_S7` lưu `N0spam@@`).
  2. `taikhoan_dat_v2_updated .xlsx` (Sheet `Tài Khoản`):
     - Cột `PASS` (Cột D): Chứa mật khẩu ngẫu nhiên ban đầu lúc tạo nick (ví dụ chuỗi `ab1kTXrBThE5i@yu`).
     - Cột `PASS MAIL` (Cột G): Chứa mật khẩu chuẩn hóa đổi sau này (ví dụ `Caoanh11092003@Ks`).
     - *Bẫy*: Nhiều tài khoản chưa đổi mật khẩu thành công trên Google nên mật khẩu thực sự hoạt động vẫn là chuỗi gốc ở cột `PASS`.
- **Khôi phục mật khẩu an toàn bằng phiên S7 đang Live**:
  - Khi mật khẩu ở cả 2 nguồn đều không khớp, kiểm tra phiên tài khoản trên thiết bị Android S7:
    `adb -s <serial> shell dumpsys account | grep -E "Account {"`
  - Nếu tài khoản vẫn còn phiên sống (`Account {name=..., type=com.google}`):
    - Trên trình duyệt GPM, bấm nút *"Bạn quên mật khẩu?"* (`Forgot Password`).
    - Google sẽ tự động đẩy Google Prompt về điện thoại S7: *"Có phải bạn đang khôi phục tài khoản của mình không?"*.
    - Trên S7: Tự động tap nút *"Có, đúng là tôi"* (Yes, it's me).
    - Trình duyệt sẽ hiển thị màn hình tạo mật khẩu mới (`accounts.google.com/v3/signin/recovery/changepassword`).
    - Nhập mật khẩu chuẩn hóa mới, cập nhật đồng bộ vào `master_gmail_manager.xlsx`, `gmail_clean_v2.xlsx` và `taikhoan_dat_v2_updated .xlsx`. Cách này giữ sống 100% tài khoản mà không sợ bị dính checkpoint hay mất nick.



