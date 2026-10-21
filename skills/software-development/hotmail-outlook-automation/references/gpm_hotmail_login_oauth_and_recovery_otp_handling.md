# Xử Lý Đăng Nhập Hotmail Trên GPMLogin: OAuth Silent Redirect, False Positive Auth, và OTP Mail Khôi Phục

## 1. Cạm Bẫy OAuth Silent Sign-in (`complete-client-signin-oauth-silent`)
- **Hiện tượng**: Sau khi submit email và password trên `login.live.com`, Microsoft chuyển hướng trình duyệt qua URL trung gian:
  `https://account.microsoft.com/auth/complete-client-signin-oauth-silent?state=...`
- **PITFALL NGHIÊM TRỌNG**: TUYỆT ĐỐI CẤM gọi `page.goto("https://account.microsoft.com")` hoặc ép reload khi thấy URL này. Việc can thiệp thủ công sẽ làm đứt chuỗi trao đổi token ngầm (silent OAuth redirect) và đẩy trình duyệt rơi vào trang Landing quảng bá dành cho khách vãng lai (Unauthenticated Promo Page):
  - Tiêu đề: `Microsoft account | Đăng nhập hoặc tạo tài khoản của bạn ngay hôm nay – Microsoft`
  - Nội dung chính: *"Hoàn toàn miễn phí với tài khoản Microsoft - Đăng nhập để quản lý tài khoản của bạn"*.
- **Cách xử lý chuẩn**: Chờ tự nhiên (polling loop 1s, tối đa 15-20s) không can thiệp cho đến khi URL tự chuyển tiếp về `https://account.microsoft.com/?lang=...` với tiêu đề `Microsoft account | Trang chủ`.

## 2. Nhận Diện Đăng Nhập Chuẩn Xác (Chống False Positive)
- **Cạm bẫy Selector Universal Header (UHF)**:
  Trên trang Promo vãng lai chưa đăng nhập, Microsoft vẫn render Universal Header có chứa:
  - Nút avatar tròn chứa chữ `ME`
  - Nút `@Phản hồi` / `@Feedback`
  - Text `Tài khoản Microsoft`
  Nếu selector kiểm tra đăng nhập chỉ dựa vào các phần tử này hoặc `page.url.startswith("account.microsoft.com")`, script sẽ báo `SUCCESS` nhầm (False Positive) dù thực tế chưa hề đăng nhập!
- **Quy tắc phân loại Auth**:
  1. **LOẠI TRỪ (Unauthenticated)**: Nếu body chứa:
     - `"hoàn toàn miễn phí với tài khoản microsoft"`
     - `"đăng nhập để quản lý tài khoản của bạn"`
     - `"sign in to manage your account"`
     -> Đánh dấu CHƯA đăng nhập (`logged_in = False`).
  2. **CHẤP NHẬN (Authenticated)**: Khi phát hiện các thẻ quản trị thực tế của người dùng:
     - `"thay đổi mật khẩu"` / `"change password"`
     - `"bảo mật"` / `"security"`
     - Tiêu đề trang chứa `"trang chủ"` hoặc `"home"`.

## 3. Thử Thách Xác Minh Danh Tính Qua Mail Khôi Phục (`@fviainboxes.com`)
- Khi đăng nhập trên proxy/IP mới, Microsoft có thể yêu cầu:
  - Tiếng Việt: *"Sắp hoàn thành - Gửi mã đến ...@fviainboxes.com"*, *"Xác minh email của bạn"*.
  - Tiếng Anh: *"Almost there - Send a code to..."*, *"Verify your email"*.
- **Quy trình xử lý tự động**:
  1. KHÔNG đưa *"xác minh email"* vào `hard_block_keywords`.
  2. Tra cứu `recovery_email` tương ứng từ file dữ liệu (`gmail_clean_v2.xlsx`).
  3. Điền email khôi phục đầy đủ vào ô xác minh danh tính và click nút gửi mã.
  4. Gọi `fetch_recovery_email_otp(rec_email)` từ `mail_domain_otp_helper.py` để polling mã OTP từ API `fviainboxes.com`.
  5. Điền mã OTP vào form (hỗ trợ cả UI 6 ô `#codeEntry-0`..`#codeEntry-5` và ô OTC `#iOttText`) rồi submit.

## 4. Xử Lý Cookie Consent Banner
- Microsoft thường xuyên bật popup Cookie Consent che khuất màn hình (`Chấp nhận`, `Accept`, `Đồng ý`, `Từ chối`, `#acceptButton`).
- Cần có hàm bắt và đóng banner cookie ở cả 2 thời điểm:
  - Trong vòng lặp chờ chuyển tiếp URL sau submit.
  - Ngay sau khi vào trang đích trước khi chụp ảnh màn hình và kiểm tra auth.
