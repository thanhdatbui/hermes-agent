# GPM Gmail Login 2FA Gate & S7 ChatGPT Setup Workflow

## 1. Bản chất sự cố [LOGIN GPM ĐÊM ✗ 36] & Hard Phone Checkpoint
- **Hiện tượng**: Watchdog chạy tự động nạp Gmail lên GPM Profile bị fail 100% (ví dụ: `✓ 0 | ✗ 36`), đồng thời sinh ra các screenshot `oauth_<email>_hard_phone_checkpoint_<timestamp>.png`.
- **Nguyên nhân**:
  1. Profile GPM trên PC là môi trường Chromium mới toanh (Fingerprint PC, Canvas/WebGL khác, User-Agent Windows).
  2. Tài khoản Gmail tạo và ngâm trên Samsung Galaxy S7 nhưng **chưa được bật 2FA TOTP** (`2FA_Secret = None` trong `master_gmail_manager.xlsx`).
  3. Khi đăng nhập vào `accounts.google.com` trên PC, do tài khoản không có phương thức xác minh thay thế (không có TOTP), Google đánh giá rủi ro cao và kích hoạt màn hình chặn bắt buộc: *"Có điều bất thường về hoạt động của bạn / Xác minh số điện thoại để nhận mã SMS" (`challenge/iap`)*.
  4. Cơ chế an toàn (Fail-Safe) của farm ngắt ngay lập tức để tránh làm hỏng tài khoản Google, nhưng điều này làm lãng phí quota proxy (tối đa 2 acc/port/ngày).

## 2. Vì sao "Warm up profile" không giải quyết được?
- Lướt web, đọc báo hay xem video trước khi login chỉ tạo ra cookie khách (guest).
- Google nhận diện thiết bị đăng nhập qua auth state và hardware trust, không dựa vào cookie rác của trang bên thứ ba.
- Điểm mấu chốt là: **Tài khoản phải có 2FA TOTP (Google Authenticator) trước khi login vào bất kỳ trình duyệt PC nào**. Khi có TOTP, Google hỏi mã 6 số -> script dùng `pyotp` điền tự động pass 100% không bao giờ đòi SĐT.

## 3. Invariant: Phân định rõ 2 nhóm tài khoản khi nạp GPM & Xử lý 2FA

### A. Thực tế Farm: Nhiều Gmail chưa add 2FA vẫn login GPM thành công
- Trên thực tế farm, nhiều tài khoản Gmail LIVE cũ/đã ngâm tốt chưa bật 2FA TOTP vẫn đăng nhập lên GPM thành công qua luồng phối hợp S7 (khi Google hỏi challenge, script `run_oauth_s7_pipeline.py` tự động qua ADB tương tác với S7 để lấy mã bảo mật hoặc nhấn phê duyệt trên thiết bị).
- **CẤM TUYỆT ĐỐI hard-filter `if not two_fa: continue` một cách mù quáng** trong `post_evening_gpm_login_watchdog.py`: Việc chặn cứng này sẽ triệt tiêu khả năng login của toàn bộ các tài khoản Gmail LIVE đang chờ nạp lên GPM, đồng thời tạo ra nghịch lý bế tắc nếu sau đó lại đòi GPM có session để add 2FA.
- Candidate nạp GPM chỉ cần thỏa mãn: Gmail `LIVE`, chưa nạp OmniRoute, đã có profile GPM trong DB và máy rảnh/online ADB.

### ⚠️ Pitfall: Nghịch lý Con Gà - Quả Trứng (Tránh phá vỡ luồng 2FA)
- **Sai lầm cấu trúc nghiêm trọng**: Tự ý sửa script watchdog 2FA sáng (`post_morning_gmail_2fa_watchdog.py`) thành mở profile GPM PC để bấm add 2FA.
- **Tại sao sai?**
  1. Profile GPM trên PC mới tạo chưa hề có session đăng nhập Google.
  2. Watchdog 2FA mở GPM browser ra sẽ gặp redirect `google.com/account/about` (`NO_SESSION`), hoàn toàn không có session để add 2FA.
  3. Kết quả tạo ra vòng lặp bế tắc: GPM chưa login thì không add 2FA được, mà bên login GPM lại chặn không cho login nếu chưa có 2FA.
- **Quy tắc bất biến**:
  - Bật 2FA (`post_morning_gmail_2fa_watchdog.py` / `add-gmail-2fa`) **PHẢI thực hiện trên S7 (Playwright qua proxy máy + ADB bốc mã bảo mật 10 số trên S7)** để ghi `2FA_Secret` vào Excel (`master_gmail_manager.xlsx`, `gmail_clean_v2.xlsx`).
  - TUYỆT ĐỐI KHÔNG chuyển luồng `post_morning_gmail_2fa_watchdog` sang mở profile GPM chưa login để add 2FA.
  - Trên GPM: Nếu tài khoản đã có 2FA TOTP, script tự động điền qua `pyotp`. Nếu chưa có 2FA TOTP, script phối hợp qua ADB thiết bị S7 để vượt challenge đăng nhập bình thường.

## 4. Bật 2FA tự động phối hợp S7 (`D:\Taadaa\add-gmail-2fa`)
Khi tài khoản chưa có 2FA trên S7, sử dụng pipeline tự động:
- **Repo**: `D:\Taadaa\add-gmail-2fa` (`runner.py`).
- **Quy trình**:
  1. Playwright mở Chromium qua đúng cổng Proxy Mobi của máy đó vào `myaccount.google.com/two-step-verification/authenticator`.
  2. Khi Google yêu cầu xác minh danh tính (Mã bảo mật 10 số): Script tự động gọi ADB vào máy Samsung S7 (`get_s7_security_code`), truy cập *Cài đặt -> Google -> Quản lý tài khoản -> Bảo mật -> Mã bảo mật*, trích xuất mã 10 số điền vào form.
  3. Bấm "Thiết lập Authenticator" -> "Không thể quét mã QR" -> Lấy **TOTP Secret Key**.
  4. Tự động lưu `2FA_Secret` vào file `master_gmail_manager.xlsx`.
- **Lệnh chạy**: `python D:\Taadaa\add-gmail-2fa\runner.py --machine <N>`

## 5. Quy tắc Reg / Login ChatGPT trên máy Samsung S7
- **Ưu thế**: Gmail đã add sẵn trong hệ điều hành Android của S7, IP 4G MobiProxy sạch, độ trust thiết bị thật cao.
- **Quy tắc bất biến**:
  - **BẮT BUỘC dùng "Direct Email OTP"**: Nhập địa chỉ email -> Nhận mã OTP 6 số về Gmail -> Nhập mã để login.
  - **CẤM TUYỆT ĐỐI bấm "Continue with Google" (Google SSO)** trên thiết bị di động: SSO trên mobile kích hoạt reCAPTCHA Challenge hoặc làm khóa phiên tài khoản.
  - **CẤM lệnh clear input `--meta 113` trên Android 8 & CẤM dùng `clear_field()` trên Chrome WebView**:
    * Binary `input` Android 8 không hỗ trợ cờ `--meta`, chỉ nhận keycode 29 và xóa 1 ký tự, dẫn đến nhân đôi chuỗi email (`hautuanphattechhautuanphattech...`).
    * CẤM gọi `clear_field()` từ `gmail_reg_v10` trên Chrome: Hàm này tìm thẻ `EditText` native Android, trên Chrome chỉ tìm thấy thanh địa chỉ URL bar (`com.android.chrome:id/url_bar: chatgpt.com/auth/...`). Nó sẽ ngộ nhận việc xóa chưa xong, lặp lại 3 attempts tốn 30s gọi `get_ui_xml` và làm cướp focus lên thanh URL gây timeout.
    * **Chuẩn hóa**: Dùng hàm chuyên dụng cho WebView `clear_webview_field(device_id, coord)` chỉ gửi chuỗi phím xóa 2 chiều thuần túy (MOVE_END + DEL 40 lần + MOVE_HOME + FORWARD_DEL 40 lần) không quét XML.
  - **CẤM tap toạ độ đáy `y >= 1700` (vd `540, 1800`) để đóng Bento popup**: Trên màn hình S7 (1080x1920), toạ độ này trúng nút Soạn thư nổi (FAB `compose_button`) của Gmail, làm kẹt trong màn soạn thư và swipe refresh không ra Inbox để đọc OTP. Luôn dùng `input keyevent 4` (KEYCODE_BACK) để đóng popup an toàn.
  - **Guard thoát màn Soạn thư & Tab Meet**: Đầu vòng lặp lấy OTP, nếu thấy `compose_area` / `Soạn thư` thì bấm Back để về Inbox; nếu thấy tab `Họp mặt` thì tap chuyển về tab `Thư`. Chi tiết xem `references/chatgpt-reg-s7-android8-input-clear-and-gmail-compose-pitfalls-20260922.md` trong skill `gmail-account-automation`.
