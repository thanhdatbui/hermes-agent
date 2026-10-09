# ChatGPT Direct Registration on Samsung S7 (Android 8) — Lessons & Traps

Date: 2026-09-20
Status: ACTIVE

## 1. Samsung Pay Bottom-Edge Overlay Trap (`HintService`)
- **Triệu chứng**: Sau khi gõ email và bấm "Tiếp tục", thiết bị bị văng ra màn hình Home Launcher, hoặc click vào nút "Tiếp tục" bị nuốt mất sự kiện khiến script bị `EMAIL_SUBMIT_TIMEOUT` sau 80s+.
- **Nguyên nhân**: Dịch vụ `com.samsung.android.spay.pay.HintService` duy trì một View trong suốt nằm đè ở đáy màn hình (`bounds=[0, 1700][1080, 1920]`) để lắng nghe thao tác vuốt lên mở thẻ thanh toán. Khi tap vào nút submit ở cạnh dưới, HintService nuốt toàn bộ touch event và kéo ứng dụng về Home.
- **Giải pháp**: Trước khi chạy flow đăng ký web, bắt buộc vô hiệu hóa package:
  ```bash
  pm disable-user --user 0 com.samsung.android.spay
  ```

## 2. Bento Popup Account Switch & Safe Header Handling (`ensure_gmail_account_active`)
- **Active Header Tap Trap**: When `target_email` is already the primary active account in Gmail, it sits in `resource-id` containing `og_compact_header_secondary_text` (bounds `[324, 367][912, 426]`).
- Tapping this node directly opens Google Account Management ("Quản lý Tài khoản Google"), obscuring the Gmail conversation list and causing `FAILED_AT_OTP_FETCH` timeouts.
- **Rule**: If `target_email` is in `og_compact_header_secondary_text`, NEVER tap it! Dismiss popup safely via coordinate `(540, 1800)` or `(100, 1800)`. Only tap if `target_email` belongs to `og_secondary_account_information`.

## 3. Chrome Anti-Drift & Orientation Control
- **Anti-Drift Guard**: When switching back to Chrome from Gmail at Step 3, do not rely on generic `am start ...Main`. Verify that the current domain is `chatgpt.com` or `auth.openai.com`. If dropped onto `google.com` or another background tab, re-issue intent for `https://chatgpt.com/auth/login?screen_hint=signup`.
- **Portrait Lock (Orientation 0)**: Samsung S7 devices with `accelerometer_rotation=1` may switch to landscape (`1920x1080`), distorting web layouts and causing coordinate taps to miss. Lock orientation via settings before starting:
  ```python
  shell(device_id, "content", "insert", "--uri", "content://settings/system", "--bind", "name:s:accelerometer_rotation", "--bind", "value:i:0")
  shell(device_id, "content", "insert", "--uri", "content://settings/system", "--bind", "name:s:user_rotation", "--bind", "value:i:0")
  ```

## 4. Keyboard Dismissal & Direct Password Flow Coordinates
- **IME Overlay Trap**: After typing email or password, Samsung keyboard (`com.sec.android.inputmethod`) covers the bottom half of the screen (`bounds=[0,1047][1080,1920]`), obscuring the Continue button (`y=1504` or `y=1812`).
  - Send `shell input keyevent 111` (KEYCODE_ESCAPE) to dismiss the keyboard safely without accidental clicks or closing Chrome.
- **OpenAI Direct Password Flow**:
  - URL: `auth.openai.com/create-account/password`.
  - Password Input: Located at bounds `[111,1218][885,1290]` -> center `(540, 1254)`.
  - Continue Button: Pushed to the bottom by password requirements -> bounds `[48,1734][1032,1890]` -> center `(540, 1812)`.
  - Type password, send KEYCODE_ESCAPE, then tap `(540, 1812)`.

## 5. Google SSO Bottom-Sheet Dismissal
- Khi Chrome tự động bật popup Credential Manager: *"Đã đăng nhập vào Google bằng [tài khoản cũ]"*:
  - Nhận diện chuỗi `"Đã đăng nhập vào Google bằng"` / `"Signed in to Google as"`.
  - Tìm nút "Hủy" / "Bỏ qua" hoặc fallback tap `(540, 1780)`.
  - Tap thêm điểm an toàn phía trên popup `(540, 300)` để dismiss triệt để bottom-sheet.

## 6. Form Xác Nhận Tuổi & Họ Tên (`auth.openai.com/about-you`)
- Sau khi nhập OTP chính xác, OpenAI chuyển tiếp sang màn hình `about-you` ("Hãy xác nhận tuổi của bạn").
- **Lỗi thiếu tên**: Nếu chỉ điền năm sinh mà bỏ trống họ tên, form báo lỗi *"Vui lòng nhập tên để tiếp tục"*.
- **Xử lý chuẩn**:
  - Focus ô `_r_i_-name` tại `(540, 645)`, điền tên (ví dụ `BuiTuyen`).
  - Focus ô năm sinh tại `(340, 835)`, điền năm sinh (ví dụ `1999` hoặc trích xuất từ DOB).
  - Gửi `keyevent 111` (KEYCODE_ESCAPE) hạ bàn phím ảo.
  - Tap nút "Tiếp tục" tại `(540, 1818)` (bounds `[48,1740][1032,1896]`).
  - Màn hình chuyển sang *"Bạn đã hoàn tất"* $\rightarrow$ Tap "Tiếp tục" tại `(540, 1000)` để vào thẳng giao diện chat chính thức.

## 7. Định Vị Avatar Gmail Bằng `selected_account_disc_gmail`
- Tọa độ cũ `(985, 138)` có thể chạm mép viền trên thanh tìm kiếm.
- **Tọa độ & Resource-ID chuẩn**: Ưu tiên tìm node `selected_account_disc_gmail` hoặc content-desc *"Tài khoản và các chế độ cài đặt"*, fallback tọa độ tâm `(990, 168)` để mở Google Bento account popup 100% tin cậy.

## 8. False Positive reCAPTCHA Trap trên Chrome Account Data Sync Popup (Máy 26 Incident)
- **Hiện tượng**: Script báo fail-fast `FAILED_AT_GOOGLE_RECAPTCHA (RECAPTCHA_TRIGGERED)` mặc dù OpenAI đã gửi mã xác minh thành công và màn hình web đã chuyển sang `auth.openai.com/email-verification` ("Kiểm tra hộp thư đến của bạn - Nhập mã xác minh...").
- **Nguyên nhân**: Chrome Android tự động đẩy popup hệ thống của Google Play Services: *"Xác minh danh tính của bạn - Tiếp tục sử dụng dữ liệu Chrome trong Tài khoản Google [Xác minh]"*. Bộ quét regex kiểm tra chuỗi `"Xác minh danh tính"` không phân biệt ngữ cảnh, dẫn đến việc nhầm tưởng đây là captcha chặn đăng ký và ngắt luồng sớm một cách oan uổng.
- **Quy tắc xử lý chuẩn**:
  - TUYỆT ĐỐI KHÔNG quét chuỗi `"Xác minh danh tính"` đơn lẻ khi màn hình đã có dấu hiệu của `email-verification` hoặc `Check your inbox`.
  - Chỉ kích hoạt `FAILED_AT_GOOGLE_RECAPTCHA` khi URL ở domain Google (`accounts.google.com`) HOẶC có các dấu hiệu bot puzzle cụ thể (`"Tôi không phải là người máy"`, `"I'm not a robot"`, `"g-recaptcha"`, `"rc-anchor"`).
  - Nếu gặp popup *"Tiếp tục sử dụng dữ liệu Chrome trong Tài khoản Google"*: Không bấm nút Xác minh, mà tap ra ngoài vùng popup (ví dụ `(540, 300)`) hoặc bấm Back/Hủy để popup biến mất và tiếp tục luồng OTP.

## 9. Bẫy App Gmail Lạc Vào Tab "Họp Mặt" (Google Meet) Khi Mở Hòm Thư Lấy OTP (Máy 62 Incident)
- **Hiện tượng**: Khi mở App Gmail để lấy OTP từ OpenAI (`com.google.android.gm/.ConversationListActivityGmail`), script polling liên tục và vuốt làm mới nhưng không bao giờ thấy thư mới, dẫn đến timeout `FAILED_AT_OTP_FETCH (182s)`.
- **Nguyên nhân**: App Gmail trên Samsung S7 có thanh điều hướng dưới đáy (`bottom_navigation`) gồm 2 tab: **"Thư" (Mail)** và **"Họp mặt" (Meet)**. Nếu phiên trước đó vô tình mở Meet, ứng dụng sẽ ghi nhớ và mở thẳng vào màn hình Meet (*"Cuộc họp mới" / "Tham gia cuộc họp"*). Màn hình này hoàn toàn không chứa danh sách thư đến.
- **Quy tắc xử lý chuẩn**:
  - Khi mở Gmail ở Step 2, kiểm tra XML xem có chứa chuỗi `"Cuộc họp mới"` / `"Tham gia cuộc họp"` / `"New meeting"` không.
  - Nếu phát hiện đang ở tab Meet, tìm node chứa text `"Thư"` / `"Mail"` trên `bottom_navigation` hoặc tap trực tiếp tọa độ tab Thư ở góc dưới bên trái `(270, 1850)` để chuyển ngay về hòm thư đến trước khi vuốt kéo làm mới.

## 10. Keyevent 66 (ENTER) & Retry Submit Form Email trên Chrome WebView (Máy 14 & 70 Incident)
- **Hiện tượng**: Sau khi gõ email vào form `chatgpt.com/auth/login?screen_hint=signup`, script tap nút "Tiếp tục" (`540, 1485`) nhưng giao diện web không phản hồi hoặc touch event bị nuốt do WebView proxy 4G lag, dẫn đến timeout `FAILED_AT_EMAIL_SUBMIT (175s-185s)`.
- **Nguyên nhân**: Trên Android Chrome WebView, nút HTML submit đôi khi chưa gắn xong event listener khi tap một lần duy nhất. Nếu script đánh dấu `email_submitted = True` ngay sau lần tap đầu tiên rồi ngồi chờ thụ động 25 vòng lặp, form sẽ bị treo bất động.
- **Quy tắc xử lý chuẩn**:
  - Gửi thêm lệnh `shell(device_id, "input", "keyevent", "66")` (KEYCODE_ENTER) ngay sau khi tap nút "Tiếp tục" để ép form HTML kích hoạt submit trực tiếp từ input field.
  - Nếu sau 2 vòng lặp kiểm tra XML vẫn còn thấy ô nhập email (`Email address`) và chưa chuyển sang màn hình OTP/Password, cho phép retry tap lại nút "Tiếp tục" hoặc nhấn ENTER thay vì chờ timeout.

## 11. Phòng Vệ Redirect Ngoài Ý Muốn Sang Google SSO `accounts.google.com` (Máy 29 Incident)
- **Hiện tượng**: Khi vào link đăng ký ChatGPT, Chrome tự động kích hoạt Credential Manager hoặc chạm nhầm vào nút "Tiếp tục với Google", đẩy trình duyệt sang `accounts.google.com/v3/signin/identifier` làm hỏng hoàn toàn luồng đăng ký bằng Direct Email OTP.
- **Quy tắc xử lý chuẩn**:
  - Trong vòng lặp Step 1, kiểm tra XML nếu xuất hiện URL hoặc nội dung của `accounts.google.com` hoặc `signin/identifier`:
    + Lập tức ghi nhận log cảnh báo redirect ngoài ý muốn.
    + Kích hoạt intent điều hướng lại URL đăng ký ChatGPT: `am start -a android.intent.action.VIEW -d "https://chatgpt.com/auth/login?screen_hint=signup" com.android.chrome`.
    + Chờ 2.0s, reset cờ `email_typed = False`, `email_submitted = False` để thực hiện lại luồng nhập email sạch.

