# Google OAuth Checkpoint Automation, Audio reCAPTCHA & IMAP Recovery OTP

Tài liệu kỹ thuật tổng hợp quy trình tự động hóa vượt rào cản xác minh Google OAuth (Antigravity / Gemini / Claude pool re-auth qua GPMLogin Chrome) trên hệ thống Taadaa Farm.

---

## 1. Chuỗi Quy Trình Vượt Checkpoint (Pipeline Architecture)
Khi watchdog tự động (`cron_chatgpt_web_pool_watchdog.py`) hồi sinh kết nối Google OAuth trên GPM Chrome:
1. **Account Chooser:** Chọn email đúng danh tính, có URL Guard chống loop.
2. **Password Input:** Tự động điền mật khẩu từ file Excel `gmail_clean_v2.xlsx`.
3. **reCAPTCHA Challenge Solver:** Tự động vượt bot-check qua Audio Challenge.
4. **Recovery Email OTP:** Kích hoạt gửi mã xác minh về email khôi phục và đọc qua IMAP SSL.
5. **Phone Checkpoint Detection (Fail-Safe):** Phát hiện chướng ngại vật SMS số điện thoại để ngắt an toàn.

---

## 2. Audio reCAPTCHA Solver (Speech-to-Text Bypass)
- **Cơ chế:** Google Enterprise/v2 reCAPTCHA cung cấp tùy chọn Audio cho người khiếm thị.
- **Thư viện & Công cụ:**
  - `pydub` + `speech_recognition` (Google Speech API).
  - FFmpeg binary có sẵn trên Windows: `C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe`.
- **Quy trình Playwright:**
  1. Tìm iframe `#recaptcha-anchor` -> Click checkbox.
  2. Nếu hiện challenge grid -> Tìm iframe `bframe` (hoặc `api2/bframe`).
  3. Click `#recaptcha-audio-button` -> Lấy URL audio từ `.rc-audiochallenge-tdownload-link` hoặc `#audio-source`.
  4. Download file `.mp3` về cache, dùng `pydub` convert sang `.wav`.
  5. Gọi `speech_recognition.Recognizer().recognize_google(audio_data)`.
  6. Điền chuỗi text nhận diện vào `#audio-response` -> Bấm nút Verify.

---

## 3. Đọc Mã OTP Email Khôi Phục Qua IMAP
- **Cấu hình môi trường:**
  - Host: `imap.gmail.com:993` (SSL).
  - User: `OTP_MAIL_USER` (`thanhdatbui1995@gmail.com`).
  - App Password: `OTP_MAIL_APP_PASSWORD`.
- **Kích hoạt gửi mã trên UI:**
  - Click vào dòng lựa chọn: `"Get a verification code at..."` hoặc `"Nhận mã xác minh tại..."`.
  - Fallback DOM: `el.closest('[role="link"], [role="button"], li, div[jsaction]')`.
- **Tối ưu tìm kiếm IMAP:**
  - Query nhanh: `imap.search(None, "FROM", "\"google.com\"")` (tránh search `ALL` quét 37,000+ emails gây timeout).
  - Lọc Header `BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)]` trước khi tải toàn bộ RFC822 body.
  - Bỏ qua email có Subject chứa `"cảnh báo"` hoặc `"security alert"`.
- **CỰC KỲ QUAN TRỌNG (Regex Number Clash Pitfall):**
  - Trong nội dung email Google gửi về hòm mail khôi phục:
    `"We received a request to access your Google Account thoan190945@gmail.com... Your code is: 984229"`
  - Nếu dùng regex quét 6 số `\d{6}` thông thường, regex sẽ bắt nhầm dãy số trong username (ví dụ: `190945` trong `thoan190945`) thay vì mã OTP thật `984229`!
  - **Bắt buộc:** Khử sạch mọi địa chỉ email trước khi chạy regex:
    ```python
    clean_body = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", " ", body)
    # Sau đó mới áp dụng regex bóc tách mã
    m = re.search(r"(?i)(?:verification code is|ma xac minh la|code is|is:)\D{0,40}(\d{6})(?!\d)", clean_body)
    ```

---

## 4. Các Pitfall & Quy Tắc Sống Còn

### Pitfall 1: Account Chooser Nuốt Màn Hình Challenge (Infinite Loop)
- Trên các trang challenge (`selectchallenge`, `challenge/iap`, `v2/idv`), Google luôn hiển thị huy hiệu email `@ user@gmail.com` ở đầu trang.
- Nếu bộ Account Chooser click `page.get_by_text(email)` mà không guard URL, script sẽ liên tục click vào huy hiệu này, reload lại trang challenge và không bao giờ chạm tới các nút options.
- **Quy tắc:** Chỉ click Account Chooser khi:
  `("accountchooser" in u_lower or "chooseaccount" in u_lower) and "selectchallenge" not in u_lower and "challenge" not in u_lower`

### Pitfall 2: Xung Đột Selector TOTP và Input Nhập OTP
- Cả Google Authenticator TOTP và Email OTP đều có thể dùng `<input type="tel">`.
- Nếu selector TOTP dùng `input[type="tel"]:visible`, script sẽ điền nhầm mã TOTP vào ô Email OTP hoặc ngược lại, dẫn đến lỗi `"Wrong code. Try again"`.
- **Quy tắc:** Tách biệt tuyệt đối:
  - TOTP: `#totpPin, input[name="totpPin"], input[id*="totpPin"]`.
  - Email OTP: `input[name="code"], #idvPin, input[id*="idvPin"]`.

### Pitfall 3: Phone Checkpoint (Đòi Số Điện Thoại) & Cơ Chế Fail-Safe
- Khi IP proxy bị đánh cờ hoặc tài khoản bị nghi ngờ hoạt động bất thường, Google sẽ nhảy sang màn hình:
  `"There is something unusual about your activity... Enter a phone number to get a text message with a verification code."`
- **Hành động bắt buộc:** Phát hiện Phone Checkpoint qua text analysis (`phone number`, `số điện thoại`, `enter a phone`) -> **DỪNG NGAY LẬP TỨC (Break/Abort)**.
- Tuyệt đối không để script loop điền nhầm OTP vào ô số điện thoại, tránh làm hỏng tài khoản.

---

## 5. Quy Chuẩn Vận Hành Farm: "DIE" vs "Disabled" & Tool Check-Live (`checkmail.live`)
- **Định nghĩa DIE trong Check-live Farm (User Operational Standard):**
  - Khi user hỏi "acc có die không", user TUYỆT ĐỐI KHÔNG hỏi lý thuyết về việc Google Server có vô hiệu hóa (disabled) hay chưa.
  - User hỏi **kết quả thực tế chạy qua công cụ kiểm tra live Gmail tích hợp (`checkmail.live`)**.
  - Khi một tài khoản bị Google đưa vào **Phone Checkpoint (`challenge/iap`)**, máy chủ Google tạm đình chỉ luồng xác thực bình thường -> `checkmail.live` gửi probe kiểm tra sẽ phân loại chuẩn xác tài khoản đó là **`[die]`**.
  - Vì vậy, trong vận hành Farm: **Phone Checkpoint = DIE trên tool check-live** (vì bot/automation không thể tự login sử dụng).
- **Quy chuẩn chạy kiểm tra qua `checkmail.live` (Tránh ngộ nhận & Timeout):**
  - **Tool canonical:** `D:/Taadaa/tools/check_gmail_live_fast.py` hoặc `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`.
  - **Bắt buộc dùng User Data Profile đã lưu session:** `D:\Taadaa\GPM auto\checkmail_proxy_data` (chứa API Key `b54a07fb...` và số dư > 8.000 credits). TUYỆT ĐỐI KHÔNG mở browser trắng không session vì trang bắt buộc đăng nhập mới cho check.
  - **Browser Executable:** Chỉ định rõ `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe` (hoặc Chrome hệ thống).
  - **Pitfall Fallback Timeout Proxy:** Trong `check_gmail_live_fast.py`, nếu proxy `mobi1:5101` bị lag/timeout 25s, khối `except Exception` mặc định trả về `{e: True}` (ngộ nhận LIVE sai lệch). Khi kiểm tra đối soát, nếu proxy farm 5101 bị nghẽn thì phải đảm bảo đường truyền thông suốt để nhận đúng kết quả `[Live]` / `[die]`.
  - **Bằng chứng đối soát thực tế 24/09/2026:**
    + `thoan190945@gmail.com` -> `[die]` (kẹt Phone Checkpoint)
    + `huehoa2302fi@gmail.com` -> `[die]` (kẹt Phone Checkpoint)
    + `lieumy1011199921@gmail.com` -> `[die]` (kẹt Phone Checkpoint)
    + `phamnhuphuong160120051601@gmail.com` -> `[Live]` (chỉ timeout click ChatGPT, tài khoản vẫn sống)
    + `thanhdatbui1995@gmail.com` -> `[Live]` (mail khôi phục chuẩn live)
- **Kỷ luật dữ liệu Farm:** **`CẤM xóa Gmail DIE`** (Mọi nick là tài sản). Chỉ đánh dấu trạng thái DIE, cô lập khỏi active pool OmniRoute hoặc chuyển sang sheet lưu trữ `Gmail_DIE_Archive`; tuyệt đối KHÔNG xóa vĩnh viễn khỏi Excel master vì tài khoản vẫn có thể cứu bằng SIM thật bất cứ lúc nào.

---

## 6. Phone Checkpoint & Cơ Chế Cooldown / Ngâm Thực Tế (Empirical Evidence)
- **Khác biệt cốt lõi:**
  - **Rate Limit IP:** Lỗi tạm thời do dải IP xoay (`"Bạn đã thử quá nhiều lần, hãy thử lại sau vài giờ"`), sau 24h - 48h ngâm IP sạch hệ thống sẽ tự nhả.
  - **Phone Checkpoint (`challenge/iap`):** Đây là **Cờ bảo mật cấp tài khoản (Account Security Flag)** được Google đánh dấu trực tiếp trên server sau khi quét đợt (security sweep) hoặc nghi ngờ đăng nhập bất thường.
- **Bằng chứng đối soát log thực tế gần 20 ngày (05/09 - 24/09):**
  - **KHÔNG CÓ TÀI KHOẢN NÀO TỰ HẾT HỎI KHI NGÂM.**
  - `thainhuong07052000rmv@gmail.com`: dính `challenge/iap` từ 06/09, ngâm suốt 14 ngày, đến 20/09 quét lại vẫn kẹt đòi số điện thoại.
  - `giathu0709200565@gmail.com`: dính `challenge/iap` từ 05/09, ngâm suốt 15 ngày, đến 20/09 vẫn kẹt đòi số điện thoại.
  - `dianavmoorepdqu9@gmail.com` (`COOLDOWN_PHONE`) & `darrellpperezvjnlo@gmail.com` (`COOLDOWN_IP`): ngâm hơn 15 ngày, đến 21/09 mở lại Google vẫn trơ trơ form đòi số điện thoại.
- **Cạm bẫy Hard-Lock khi thuê số ảo dùng 1 lần:**
  - Màn hình Google nêu rõ: *"Google sẽ lưu trữ số điện thoại này cho mục đích bảo mật"*.
  - Nếu nhập số điện thoại thuê ảo (chỉ tồn tại 10-15 phút), Google sẽ lưu số này làm Recovery Phone. Lần sau nếu bị quét lại và Google bắt xác minh lại đúng số cũ đã lưu -> Tài khoản sẽ bị **KHÓA CHẾT VĨNH VIỄN (Hard-Lock)** do không còn giữ SIM.
- **Giải pháp tối ưu cho Farm:**
  - Dùng **SIM vật lý thật của Farm** cắm máy để mở khóa (1 SIM thật có thể xác minh cho 4-5 Gmail, giữ quyền kiểm soát vĩnh viễn nếu Google hỏi lại).
  - Hoặc tạm thời cô lập, không để bot spam thử lại.

---

## 7. Bảng Giá & Dịch Vụ Thuê SIM OTP Việt Nam (+84) Cho Google (Cào Thực Tế 2026)
- **Invariant Địa Lý:** Khi tài khoản đăng nhập qua IP Proxy Farm Việt Nam, **CẤM TUYỆT ĐỐI** dùng đầu số ảo nước ngoài (US/UK/RU) để verify, tránh gây bất thường địa lý khiến Google từ chối số hoặc gắn cờ nặng hơn. Bắt buộc dùng **đầu số Việt Nam (+84)**.
- **Bảng giá thực tế (Cào trực tiếp tháng 09/2026):**
  - **FastOTP.net:** **`964đ / SMS`** (Rẻ nhất thị trường nội địa, timeout 600s, nạp Bank/MoMo).
  - **ViOTP.com:** **`~1.500đ – 2.200đ / SMS`** (Kho SIM vật lý nội địa dồi dào, có API RESTful).
  - **5sim.net (Lọc riêng mạng VN):** **`$0.175 – $0.19` (~4.400đ – 4.800đ)**.
    + Nhà mạng `virtual47` (tỷ lệ nổ code 57% - 77%).
    + Nhà mạng `virtual4` (stock 25.000 số).
    + Ưu điểm: Tự động hoàn tiền 100% nếu không nhận được SMS trong vòng 2 phút (gọi API cancel).
  - **Chothuesimcode.net:** **`$0.34 – $0.44` (~8.500đ – 11.000đ)** (Khá đắt).
  - **BinOTP.com:** ❌ Điều khoản ghi rõ không cung cấp SIM Việt Nam.

---

## 8. Cạm Bẫy Cloudflare Turnstile Khi Đăng Nhập ViOTP & Hướng Tiếp Cận API Token
- **Hiện tượng**: Khi tự động điều hướng tới `https://viotp.com/account/login`, trang bật widget bảo mật Cloudflare Turnstile (`Performing security verification`).
- **Bẫy Automation Click (`@e9` / CDP mouse click)**:
  - Khi click vào checkbox "Verify you are human", Cloudflare Turnstile phát hiện môi trường điều khiển DevTools / WebDriver / Chromium cờ bot.
  - Spinner xoay một nhịp ngắn rồi tự động reset checkbox về trạng thái rỗng (`[checked=false]`), không cấp token pass-through và giữ nguyên màn hình chặn.
- **Kỷ luật vận hành**:
  - TUYỆT ĐỐI KHÔNG cố gắng brute-force hay viết script loop click tự động qua Cloudflare Turnstile trên web ViOTP.
  - ViOTP hỗ trợ đầy đủ hệ thống REST API (`https://api.viotp.com/service/getv2?token=...`, `https://api.viotp.com/request/getv2?token=...&serviceId=...`).
  - Hướng tiếp cận chuẩn: Người vận hành đăng nhập thủ công 1 lần trên trình duyệt cá nhân để lấy mã **`API Token`** từ ViOTP Dashboard (hoặc cung cấp tài khoản/token), sau đó tích hợp trực tiếp qua HTTP REST API để order số và lấy OTP hoàn toàn không qua giao diện web.
