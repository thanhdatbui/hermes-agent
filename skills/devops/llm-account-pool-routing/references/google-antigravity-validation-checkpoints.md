# Google Antigravity Checkpoints & VALIDATION_REQUIRED (403) Handling

## 1. Hiện tượng & Bản chất lỗi

Khi tài khoản Google AI Pro (Antigravity) đã hoàn tất luồng OAuth và cấp `access_token` hợp lệ, nhưng khi gửi request sinh nội dung (`streamGenerateContent` / `/v1/chat/completions`), upstream Google Cloud Code trả về `403 PERMISSION_DENIED`:

```json
{
  "error": {
    "code": 403,
    "message": "Verify your account to continue.",
    "status": "PERMISSION_DENIED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
        "reason": "VALIDATION_REQUIRED",
        "domain": "cloudcode-pa.googleapis.com",
        "metadata": {
          "validation_error_message": "Verify your account to continue.",
          "validation_url_link_text": "Verify your account",
          "validation_url": "https://accounts.google.com/signin/continue?sarp=1&scc=1&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini&plt=..."
        }
      }
    ]
  }
}
```

### Tại sao test connection trên OmniRoute vẫn xanh?
- Endpoint `POST /api/providers/[id]/test` chỉ gửi probe metadata nhẹ hoặc kiểm tra refresh token, thường trả về `valid: true, warning: probe 400 inconclusive`.
- Khi client thực sự gọi qua Combo, pre-dispatch filter hoặc upstream executor sẽ nhận `403` và phân loại thành `insufficient_quota` / `project_route_error` / `ALL_TARGETS_SKIPPED`.

---

## 2. Các tầng bảo mật chặn của Google & Quy trình xử lý

### Tầng 1: Cảnh báo bảo mật quan trọng (Critical Security Alert)
- **Triệu chứng:** Khi mở `https://myaccount.google.com/`, xuất hiện banner đỏ `Critical security alert: Suspicious attempt to sign in with your password`.
- **Cách xử lý tự động qua Playwright CDP:**
  1. Điều hướng tới `https://myaccount.google.com/notifications` hoặc link chi tiết sự kiện `https://myaccount.google.com/notifications/eid/<ID>?origin=3`.
  2. Bắt locator nút `"Yes, it was me"`:
     ```python
     btn = page.get_by_text('Yes, it was me')
     if await btn.is_visible():
         await btn.click()
     ```
  3. Sau khi bấm, Google sẽ gỡ cảnh báo và chuyển trạng thái về `Security Checkup: Safe`.

### Tầng 2: Upleveling Verification Checkpoint (Quét mã QR điện thoại)
- **Triệu chứng:** Khi mở `validation_url` trích xuất từ 403 response, Google chuyển hướng tới:
  `https://accounts.google.com/uplevelingstep/selection?...`
  với nội dung:
  > **Verify your info to continue**
  > Google needs to verify some info about your device or phone number before you can continue.
  > **Scan the QR code with your phone:** Open your Camera app, scan the code, and tap the link...
- **Bản chất & Cảnh báo bẫy Copy-Paste Link:** 
  - Google yêu cầu luồng quét từ ứng dụng Camera thực tế (`Camera app intent / barcode scanner`).
  - **CẢNH BÁO QUAN TRỌNG 1 (Bẫy copy link):** Tuyệt đối **KHÔNG** copy link `https://accounts.google.com/devicephoneverification/begin?flow=browser...` rồi dán trực tiếp vào trình duyệt (Safari/Chrome trên iPad/Điện thoại) hoặc gửi qua ADB intent. Nếu dán trực tiếp, Google sẽ chặn ngay với thông báo:
    > *"We couldn't verify your info — Something went wrong and we couldn't verify your info. To complete verification, try going through the steps again."*
  - **CẢNH BÁO QUAN TRỌNG 2 (Bẫy gửi SMS shortcode 96831 trên iOS):**
    - Khi quét QR trên iPhone/iPad (Safari), Google kiểm tra SIM trên máy bằng cách tạo tin nhắn gửi tới đầu số ngắn **`96831`** (US Shortcode).
    - Các nhà mạng Việt Nam (Viettel, Mobi, Vina, Vietnamobile) **không hỗ trợ gửi SMS tới đầu số ngắn quốc tế 5 chữ số**, khiến iPhone báo đỏ *"Chưa gửi được"*.
  - **3 Cách Vượt Qua Upleveling Verification Thành Công 100%:**
    1. **Đăng nhập Google/Gmail app trên iPhone (Khuyên dùng):** Mở app **Gmail** hoặc app **Google** trên iPhone → Đăng nhập tài khoản Gmail cần xác minh. Sau khi tài khoản đã có trong app, mở Camera quét mã QR. Google sẽ chuyển luồng sang Google Prompt trong app (*"Có phải bạn đang đăng nhập không?"* → Bấm Có) mà **hoàn toàn không bắt gửi SMS**.
    2. **Quét bằng máy Android có Google Play Services:** Dùng bất kỳ máy Android cá nhân nào mở Camera quét mã QR. Google Play Services trên Android sẽ tự động chứng thực phần cứng ngầm (Play Integrity) trong 1 giây mà không cần gửi SMS.
    3. **Kích hoạt Passkey & 2-Step Verification trên GPM Profile:** Mở GPM Profile → Vào `myaccount.google.com/signinoptions/passkeys` và bật 2-Step Verification. Gắn Passkey/FIDO2 hardware credential giúp nâng trust tài khoản và tránh việc Google ép xác thực SMS shortcode.
- **Cách xử lý:**
  1. Trích xuất `validation_url` trực tiếp từ upstream API error response.
  2. Mở Profile GPM tương ứng qua Playwright CDP hoặc trực tiếp trên UI GPM.
  3. Điều hướng tới `validation_url` để hiển thị mã QR.
  4. Thông báo người dùng mở camera điện thoại quét mã QR xác nhận (hoặc gửi ảnh chụp màn hình QR `MEDIA:...png` để người dùng quét). Sau khi hoàn thành trên điện thoại, Google lập tức mở khóa API Cloud Code cho token.

### Tầng 3: Google Prompt / Device Challenge Trong Luồng OAuth (`challenge/dp`)
- **Triệu chứng:** Khi chạy OAuth Antigravity (`add_oauth_omniroute.py`) từ profile GPM qua proxy, sau khi chọn tài khoản, Google chuyển hướng tới:
  `https://accounts.google.com/v3/signin/challenge/dp?...`
  với nội dung:
  > **Xác minh danh tính của bạn**
  > **Kiểm tra Galaxy S7 (hoặc thiết bị gắn với tài khoản) của bạn**
  > Google đã gửi thông báo đến [Thiết bị] của bạn. Nhấn vào **Có** trên lời nhắc của Google, rồi nhấn vào **[Số]** trên điện thoại để xác minh danh tính của bạn.
- **Bản chất & Bẫy "Cách xác minh khác" (`challenge/selection`):**
  - Khác với login thông thường (có thể gửi mã về Recovery Email qua IMAP), khi Google đã chuyển vào `challenge/dp` số khớp, menu *"Cách xác minh khác"* thường **chỉ có 2 tùy chọn**:
    1. Nhấn vào Có trên điện thoại hoặc máy tính bảng.
    2. Sử dụng điện thoại hoặc máy tính bảng của bạn để nhận mã bảo mật offline (ngay cả khi không có mạng).
    *(Hoàn toàn KHÔNG có tùy chọn gửi OTP về Recovery Email!)*.
- **Cách xử lý:**
  1. **Nhận diện tự động:** URL chứa `challenge/dp` và màn hình hiển thị 1 số đơn lẻ (ví dụ số `26`). Chụp ảnh màn hình debug hoặc dùng regex `(?:nhấn vào|chọn|tap|số|number)\s*(\d{1,2})` trích xuất số PIN.
  2. **Tương tác trên thiết bị Farm (Galaxy S7) & Bẫy 2 Bước Google Prompt:**
     - Dùng ADB kết nối vào thiết bị S7 tương ứng với tài khoản (tra qua `PROXYgandienthoai.xlsx` / `master_gmail_manager.xlsx`).
     - Bắt buộc bọc `acquire_device_lock(machine=..., serial=..., project="oauth-prompt", bypass_proxy_readiness=True, force_preempt=True)` để tạm dừng cron nuôi acc.
     - **Bẫy Đánh Thức Máy (Wakeup Trap):** TUYỆT ĐỐI KHÔNG gửi `keyevent 26` (KEYCODE_POWER) vì nếu màn hình đang mở (`mWakefulness=Awake`), `26` sẽ tắt ngấm màn hình chuyển sang `Dozing`, làm `dump/hierarchy` fail. BẮT BUỘC dùng `keyevent 224` (`KEYCODE_WAKEUP`) kết hợp `keyevent 82` (`UNLOCK`).
     - **Bẫy Quy Trình 2 Bước (Yes -> Matching PIN):** Khi có số PIN yêu cầu (ví dụ `26`), màn hình S7 đầu tiên hiển thị thông báo *"Bạn muốn cho phép một ứng dụng truy cập dữ liệu của bạn trên Google?"* với nút *"Vâng, đúng là tôi"* / *"Có"*. Script BẮT BUỘC bấm nút này trước, sau đó **KHÔNG ĐƯỢC return True hay gửi `keyevent 3` (HOME) ngay**. Phải tiếp tục chờ màn hình 2 xuất hiện (hiển thị 3 số PIN, ví dụ `26`, `87`, `68`), bấm đúng ô số `26`, sau đó mới gửi `keyevent 3` và hoàn tất duyệt.
     - **Ưu tiên Notification:** Khi mở thanh thông báo nhóm Google Play Services, ưu tiên tìm node chứa từ khóa hành động (`"cho phép một ứng dụng"`, `"truy cập dữ liệu"`, `"đang cố đăng nhập"`) trước khi fallback tìm `target_email` để tránh bấm nhầm các thông báo bảo mật khác có cùng email.

### Tầng 4: Google Offline Security Code Challenge (`challenge/ootp`) & Bẫy Selector TOTP
- **Triệu chứng:** Khi chạy OAuth, sau khi chọn tài khoản, Google chuyển hướng tới:
  `https://accounts.google.com/v3/signin/challenge/ootp?...`
  với nội dung:
  > **Xác minh danh tính của bạn**
  > **Lấy Galaxy S7 của bạn**
  > Mở ứng dụng Cài đặt -> Nhấn vào Google -> Quản lý Tài khoản Google của bạn -> Chọn tab Bảo mật -> Trong phần "Đăng nhập vào Google", hãy nhấn vào **Mã bảo mật** -> Chọn tài khoản nhận mã -> Nhập mã.
- **Bẫy Ghi Nhớ Thử Thách & Điều Hướng Ngược về Google Prompt:**
  - Nếu ở các phiên trước tài khoản đã từng chọn phương thức *"Mã bảo mật"*, Google sẽ ghi nhớ và mặc định điều hướng thẳng vào `challenge/ootp` thay vì hiện Google Prompt (`challenge/dp`).
  - **Khắc phục:** Tại màn hình `challenge/ootp`, automation nên kiểm tra và bấm nút *"Thử cách khác"* (`button:has-text("Thử cách khác"), button:has-text("Try another way")`) để đưa Google về màn hình `challenge/selection`.
  - **Ưu tiên trên `challenge/selection`:** Tuyệt đối KHÔNG hardcode chọn `data-challengetype="8"` ("Mã bảo mật"). Bắt buộc ưu tiên bắt `data-challengetype="6"` / `li:has-text("Chạm vào Có")` / `li:has-text("Lời nhắc")` để kích hoạt Google Prompt PIN 2 bước tự động trên S7. Chỉ fallback sang `data-challengetype="8"` khi không có tùy chọn Prompt.
- **Bản chất & Cạm bẫy Selector trong Playwright:**
  - Input trên màn hình này có thuộc tính HTML `<input name="Pin" type="tel">`.
  - Bộ selector điền TOTP lỏng lẻo (`input[name="Pin"], input[type="tel"]`) sẽ match nhầm vào ô này, khiến script tự động sinh mã TOTP 6 số từ Authenticator Secret và submit liên tục. Google từ chối vì đây là ô nhận mã ngoại tuyến 10 số (`type="5"`), gây vòng lặp thử lại vô tận dẫn đến timeout sau 60s.
  - **Khắc phục selector:** Loại trừ URL chứa `challenge/ootp` hoặc kiểm tra nội dung trang có chữ *"Mã bảo mật"* / *"Security code"* trước khi điền TOTP; chỉ điền TOTP khi URL là `challenge/totp` hoặc trang chứa *"Google Authenticator"* / *"Ứng dụng xác thực"*.
- **Quy Trình Trích Xuất Mã Bảo Mật 10 Số Trên S7 & Bẫy Activity Stack:**
  - **Reset Stack trước khi mở Intent:** Khi gọi intent, sử dụng cờ `-S` (`am start -S -n com.google.android.gms/.app.settings.GoogleSettingsLink`) để buộc Android kill sạch process/task cũ trước khi start activity mới. Nếu không có `-S`, Android sẽ chỉ đưa task cũ lên foreground (`Warning: Activity not started, its current task has been brought to the front`), khiến UI tree bị kẹt ở sub-activity cũ.
  - **Cấu trúc UI GMS S7 thực tế (GMS Compose UI & Landscape 1920x1080):** Trên các máy S7 chạy màn hình ngang (1920x1080) và bản cập nhật GMS mới, màn hình chính Google Settings không có nút "Tài khoản Google" hay "Bảo mật". BẮT BUỘC tap vào Profile Card header (`[60,646][204,790]` hoặc email `[240,735][771,788]`) để mở bottom-sheet switcher -> sau đó tap nút *"Quản lý Tài khoản Google của bạn"* (`[300,444][1071,588]`). Nếu các tab bảo mật bị che khuất trong giao diện Compose, có thể tap biểu tượng Tìm kiếm (`[1800,132][1872,204]`) gõ `bao mat` để mở trực tiếp. Tuy nhiên, phương án tối ưu số 1 vẫn là bấm "Thử cách khác" trên trình duyệt để kích hoạt Google Prompt PIN 2 bước thay vì đọc mã offline.
- **Cạm bẫy "Cách xác minh khác" (`challenge/selection` thiếu Authenticator `type="6"`):**
  - Khi bấm "Cách xác minh khác" từ `challenge/ootp` hoặc `challenge/dp`, nếu tài khoản chưa được thiết lập Google Authenticator trên chính tài khoản Google (ví dụ mới chỉ bật 2FA trên TikTok hoặc dịch vụ khác), Google `challenge/selection` chỉ hiển thị:
    1. `type="39"`: Nhấn vào Có trên điện thoại hoặc máy tính bảng.
    2. `type="5"`: Sử dụng điện thoại hoặc máy tính bảng để nhận mã bảo mật offline.
    *(Hoàn toàn KHÔNG có tùy chọn Authenticator `type="6"` để giải mã bằng TOTP Secret!)*. Bắt buộc phải xác nhận qua Galaxy S7 hoặc vào `myaccount.google.com/signinoptions/two-step-verification` thêm Authenticator App vào tài khoản Google.

### Tầng 5: Checkpoint Trình duyệt không được hỗ trợ (`myaccount.google.com/not-supported`)
- **Triệu chứng:** Khi mở OAuth URL, profile bị chuyển hướng ngay sang:
  `https://myaccount.google.com/not-supported`
  với nội dung: *"Trình duyệt của bạn không còn được hỗ trợ. Vui lòng cập nhật lên trình duyệt mới hơn."*
- **Nguyên nhân & Khắc phục:** Profile GPM mang User-Agent hoặc profile fingerprint quá cũ / Chromium Core lỗi thời. Cần chuẩn hóa profile lên GPMLogin Chromium Core 142 (`CHROME_EXE`) và cập nhật User-Agent tương thích phiên bản Chrome mới nhất trong `profile_data.db`.

### Tầng 6: Checkpoint Từ Chối Do Chưa Bật 2FA / Nhạy Cảm Thiết Bị (`accounts.google.com/v3/signin/rejected` với `rrk=77&rhlk=ve`)
- **Triệu chứng:** Khi chạy OAuth Antigravity từ GPM Profile, sau khi click chọn tài khoản trên Account Chooser, Google chuyển hướng trực tiếp sang:
  `https://accounts.google.com/v3/signin/rejected?hl=vi&continue=...&flowName=WebLiteSignIn&rrk=77&rhlk=ve`
  với thông báo:
  > **Chúng tôi muốn đảm bảo rằng bạn chính là người đang cố thực hiện hành động này.**
  > Để giúp chúng tôi xác minh danh tính của bạn:
  > - Thêm tính năng Xác minh 2 bước trong phần cài đặt rồi thử lại sau 7 ngày nữa
  > - Sử dụng thiết bị và trình duyệt mà bạn đã đăng nhập trước đây
  > - Sử dụng một mạng Wi-Fi quen thuộc, chẳng hạn như mạng tại nhà riêng hoặc cơ quan
- **Bản chất:**
  - Google gắn cờ hành động cấp quyền OAuth nhạy cảm (Google Cloud Platform) từ môi trường trình duyệt GPM profile khi tài khoản chưa kích hoạt tính năng Xác minh 2 bước (2-Step Verification) trên Google Account, hoặc session chưa đủ trust score để bypass.
  - Trên màn hình này, Google không cung cấp ô nhập mật khẩu hay gửi prompt mà chỉ có các liên kết:
    - `"Thêm tính năng Xác minh 2 bước"` trỏ đến `https://myaccount.google.com/signinoptions/two-step-verification/enroll-welcome?...`
    - `"Quay lại"` (`/AccountChooser?...`)
- **Bẫy trong automation (`run_oauth_s7_pipeline.py`):**
  - Vòng lặp `while time.time() - start_t < 180` trong `process_account` không có selector kiểm tra `signin/rejected`.
  - Khi gặp màn hình này, script không match bất kỳ selector nào (Account Chooser, Password, Prompt, TOTP, Consent), dẫn đến lặp im lặng (silent loop) và chết timeout 180s (`TIMEOUT không nhận được callback code!`).
- **Cách xử lý chuẩn:**
  1. **Fail-fast trong runner:** Bổ sung kiểm tra `if "signin/rejected" in cur_url or "rrk=77" in cur_url` trong `process_account`: log rõ lỗi `REJECTED_NEED_2FA` và fail-fast thay vì chờ 180s timeout.
  2. **Khắc phục tài khoản:** Mở `myaccount.google.com/signinoptions/two-step-verification` trên profile:
     - Nhập mật khẩu.
     - Xác thực qua email khôi phục hoặc thiết bị tin cậy.
     - Bật 2-Step Verification (kích hoạt Authenticator app với mã bí mật TOTP trong `master_gmail_manager.xlsx`).
     - Sau khi bật 2FA, chạy lại pipeline nạp OAuth Antigravity thì Google sẽ gửi Google Prompt (`challenge/dp`) hoặc TOTP thay vì chặn `signin/rejected`.

### Tầng 7: Checkpoint Đòi Số Điện Thoại Xác Minh ("Có điều bất thường...") vs Bẫy Bỏ Quên Nút "Thử cách khác" (2026-09-08)
- **Triệu chứng & Bằng chứng OCR:**
  Khi Re-Auth / OAuth lại tài khoản Google (ví dụ sau khi bị `invalid_grant` / `Token expired`), Google chuyển hướng sang màn hình:
  > **Xác minh danh tính của bạn**
  > Có điều bất thường về hoạt động của bạn. Để bảo mật tài khoản của bạn, Google muốn đảm bảo rằng người đăng nhập chính là bạn.
  > `[email]`
  > **Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh.**
  > `[Ô nhập Số điện thoại]`
  > `[Thử cách khác]` `[Tiếp]`
- **Bẫy trong automation (`run_oauth_s7_pipeline.py`):**
  - Trong kịch bản ban đầu, nút *"Thử cách khác"* (`button:has-text("Thử cách khác"), button:has-text("Try another way")`) chỉ được click khi `is_dp` (`challenge/dp` hoặc trang chứa text prompt "nhấn vào Có", "kiểm tra Galaxy").
  - Khi Google rơi vào màn hình đòi số điện thoại trên, script hoàn toàn không có handler xử lý, bỏ quên nút *"Thử cách khác"*, dẫn đến lặp rỗng suốt 180s và chết timeout (`Timeout không nhận được callback code!`).
- **Cách xử lý chuẩn 100%:**
  1. **Nhận diện tự động:** Bắt URL `challenge/iap` hoặc nội dung body chứa: `"nhập số điện thoại"`, `"tin nhắn văn bản cùng mã xác minh"`, `"số điện thoại để nhận"`.
  2. **Click "Thử cách khác":** Tìm ngay selector:
     `button:has-text("Thử cách khác"), button:has-text("Try another way"), div[role="button"]:has-text("Thử cách khác"), a:has-text("Thử cách khác")`
     Click nút này để đưa Google về màn hình `challenge/selection`.
  3. **Chuyển luồng sang Prompt S7 / Mã 10 số:** Tại màn hình `challenge/selection`, script tự động chọn phương thức Google Prompt (bấm Có trên Samsung S7) hoặc Mã bảo mật 10 số offline (`challenge/ootp`) vốn đã có sẵn trên phần cứng S7 của farm.
  4. **Fail-fast nếu là Hard SMS:** Nếu màn hình đòi số điện thoại không có nút *"Thử cách khác"*, chụp ảnh debug và return ngay trạng thái `SMS_CHECKPOINT` thay vì để lặp timeout 180s làm nghẽn tiến trình runner.

### Tầng 8: Checkpoint Chọn Phương Thức Đăng Nhập (`challenge/selection`) — Bẫy "Không thể kết nối với thiết bị" & Ưu Tiên TOTP Authenticator (2026-09-08)
- **Triệu chứng & Bằng chứng OCR (WinRT OCR):**
  Khi tài khoản rơi vào màn hình `accounts.google.com/signin/challenge/selection` ("Chọn cách bạn muốn đăng nhập"):
  > **Chọn cách bạn muốn đăng nhập:**
  > `[Nhấn vào Có trên điện thoại hoặc máy tính bảng]`
  > *Không thể kết nối với thiết bị ngay bây giờ*
  > `[Nhận mã xác minh từ ứng dụng Google Authenticator]`
  > `[Thử cách khác]`
- **Bẫy trong automation (`run_oauth_s7_pipeline.py`):**
  - Selector mặc định ưu tiên tìm Google Prompt (`div[data-challengetype="6"], li:has-text("Nhấn vào Có")`).
  - Phần tử `li:has-text("Nhấn vào Có")` vẫn hiện diện trên DOM và `is_visible() == True`, nhưng do Google ghi chú *"Không thể kết nối với thiết bị ngay bây giờ"*, nút này bị vô hiệu hóa hoặc không kích hoạt được push prompt tới S7.
  - Playwright click liên tục vào `prompt_opt` mỗi 3s mà không làm thay đổi URL trang, dẫn đến kẹt lặp 40+ lần cho đến khi timeout 180s (`TIMEOUT không nhận được callback code!`).
  - Trong khi đó, tùy chọn thứ hai *"Nhận mã xác minh từ ứng dụng Google Authenticator"* hiển thị ngay bên dưới và tài khoản trong config đã có sẵn `totp_secret`.
- **Cách xử lý chuẩn 100%:**
  1. **Ưu tiên TOTP nếu có `totp_secret`:** Khi URL chứa `selection`, nếu cấu hình tài khoản có `totp_secret`, BẮT BUỘC ưu tiên kiểm tra và click tùy chọn Authenticator trước:
     ```python
     if "selection" in cur_url:
         if totp_secret:
             totp_opt = page.locator('div[data-challengetype="12"], div[data-challengetype="5"], li:has-text("Authenticator"), li:has-text("xác thực"), div[role="link"]:has-text("Authenticator")').first
             if totp_opt.count() > 0 and totp_opt.is_visible():
                 logger.info(f"[M{mid:02d}] Chọn phương thức 'Google Authenticator / Ứng dụng xác thực'...")
                 totp_opt.click()
                 time.sleep(3)
                 continue
     ```
     Sau khi click, Google sẽ chuyển sang màn hình `challenge/totp`, nơi script tự động sinh mã 6 số qua `pyotp.TOTP(totp_secret).now()` và điền vào `input#totpPin` trong 1-2 giây.
  2. **Bảo vệ `prompt_opt` chống click vô ích:** Kiểm tra text của `prompt_opt`, nếu chứa `"không thể kết nối"`, `"cannot reach"`, `"can't reach"` hoặc `aria-disabled="true"` thì bỏ qua `prompt_opt` để fallback sang tùy chọn mã bảo mật hoặc TOTP.
  3. **Chẩn đoán nhanh bằng WinRT OCR:** Khi runner timeout và chụp screenshot debug vào `D:\Taadaa\GPM auto\debug_screenshots\...`, chạy ngay script OCR WinRT không cần thư viện bên ngoài để đọc nội dung UI thực tế:
     ```bash
     python "C:\Users\Kibe\AppData\Local\hermes\skills\productivity\windows-native-ocr\scripts\winrt_ocr.py" "D:\Taadaa\GPM auto\debug_screenshots\oauth_<email>_timeout_<timestamp>.png"
     ```

---

## 3. Phân biệt 403 VALIDATION_REQUIRED vs 403 SUBSCRIPTION_REQUIRED (#3501)

| Lỗi | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `403 VALIDATION_REQUIRED` | Google chặn bảo mật thiết bị (chưa vượt qua QR checkpoint) | Quét QR bằng Camera + app Google / Android / Passkey như mục 2. |
| `403 SUBSCRIPTION_REQUIRED` (#3501) | Project ID hoặc Tier context không khớp với gói bản quyền | Gọi endpoint `/v1internal:loadCodeAssist` và `/v1internal:onboardUser` với đúng `tier_id` (`standard-tier` hoặc `g1-pro-tier`) để đồng bộ lại project mapping. |

---

## 4. Kỹ thuật Debug trực tiếp Decrypted Token trong OmniRoute

Database SQLite `C:\Users\Kibe\.omniroute\storage.sqlite` mã hóa các trường nhạy cảm (`access_token`, `refresh_token`) bằng `AES-256-GCM` dạng `enc:v1:<iv>:<ciphertext>:<tag>`.

Để test trực tiếp với Google API mà không bị ảnh hưởng bởi lớp router/proxy:
1. Lấy `STORAGE_ENCRYPTION_KEY` từ môi trường tiến trình OmniRoute đang chạy qua `psutil`.
2. Chạy script Node.js với `--import tsx/esm`:
   ```javascript
   import { decrypt } from './src/lib/db/encryption.ts';
   import { getDbInstance } from './src/lib/db/core.ts';

   const db = getDbInstance();
   const row = db.prepare('SELECT access_token, project_id FROM provider_connections WHERE id = ?').get(connId);
   const token = decrypt(row.access_token);

   const res = await fetch('https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'Authorization': 'Bearer ' + token,
       'Accept': 'text/event-stream'
     },
     body: JSON.stringify({
       project: row.project_id,
       requestId: 'debug-probe',
       model: 'gemini-3.7-flash-high',
       userAgent: 'Antigravity-Agent/1.0',
       requestType: 'agent',
       request: { contents: [{ role: 'user', parts: [{ text: 'Ping' }] }] }
     })
   });

   console.log('Status:', res.status);
   console.log('Body:', await res.text());
   ```

---

## 5. Pipeline Tự động hóa OAuth S7 Khép Kín (`run_oauth_s7_pipeline.py`)

Để gom toàn bộ quy trình vượt checkpoint (Prompt/Mã bảo mật) + OAuth exchange + gán proxy + sync model thành 1 lệnh duy nhất, sử dụng tool:
`D:\Taadaa\AI-Tools\tools\omniroute\run_oauth_s7_pipeline.py`

### Cách sử dụng:
```bash
python "D:/Taadaa/AI-Tools/tools/omniroute/run_oauth_s7_pipeline.py" <machine_id>
# Ví dụ nạp Máy 58:
python "D:/Taadaa/AI-Tools/tools/omniroute/run_oauth_s7_pipeline.py" 58
```

### Quy trình tự động thực thi:
1. **Khởi chạy Context Browser:** Mở persistent context GPM profile bằng Core 142 qua Singbox proxy tương ứng (`20000 + (port - 5100)`).
2. **Account Chooser:** Chọn tài khoản theo email chính xác mà không bị trap bởi avatar chip ở header consent.
3. **Duyệt Google Prompt (`challenge/dp`):**
   - Acquire device lock trên serial của S7.
   - Bật màn hình bằng `keyevent 224` (WAKEUP) + `keyevent 82` (UNLOCK).
   - Mở notification nhóm Google Play, tìm và tap thông báo duyệt truy cập.
   - Bấm "Có" / "Cho phép" / "Vâng, đúng là tôi".
   - Bắt đối chiếu target PIN hiển thị trên trình duyệt PC, tìm node chứa PIN trên S7 và tap chọn.
   - Trả device về Home (`keyevent 3`) và giải phóng lock.
4. **Trích xuất Mã Bảo Mật 10 số (`challenge/ootp`):** Nếu Google yêu cầu mã offline, script mở `GoogleSettingsLink`, điều hướng tới Bảo mật -> Mã bảo mật, đọc mã 10 số và điền vào ô Pin trên trình duyệt.
5. **Exchange Code & Bind Proxy:**
   - Lấy authorization code từ redirect URL `/callback`.
   - Gửi exchange lên `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange`.
   - Tra cứu proxy theo port (ví dụ 5124) và gán 1:1 qua `PUT /api/settings/proxies/assignments`.
   - Gọi `POST /api/providers/{conn_id}/sync-models`.
6. **Xác thực Live:** Gửi request kiểm thử qua `POST http://localhost:20129/v1/chat/completions` với header `x-omniroute-connection-id: <conn_id>` để chứng thực tài khoản hoạt động trước khi hoàn tất.

### Lưu ý sống còn về Password/TOTP & Timeout Debug:
- Khi chạy `run_oauth_s7_pipeline.py`, nếu tài khoản chưa lưu session hoàn toàn và Google yêu cầu nhập mật khẩu (`challenge/pwd` / `input[type="password"]`), script ban đầu không có handler nhập mật khẩu sẽ bị kẹt im lặng trong vòng lặp chờ `captured_code` dẫn đến **FAILED (TIMEOUT)** sau 180s.
- Bắt buộc:
  1. Tích hợp đọc mật khẩu và mã TOTP từ `master_gmail_manager.xlsx` / `gmail_clean_v2.xlsx`.
  2. Bắt các input `input[type="password"]`, `input[name="Passwd"]` và bấm `#passwordNext`.
  3. Bắt các input `input#totpPin` (với điều kiện URL không phải `ootp`) và sinh mã TOTP qua `pyotp`.
  4. Luôn ghi log URL hiện tại nếu rơi vào vòng lặp chưa khớp selector và chụp ảnh `debug_screenshots/oauth_<email>_timeout.png` trước khi return TIMEOUT.

