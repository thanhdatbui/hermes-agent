# Quy Trình Bật 2FA Google & Luồng Phân Tầng Giữa S7 vs GPM

## 1. Bản Chất Phân Tầng Session Google: S7 Android vs GPM Chrome PC

### Vì sao không thể bật 2FA trực tiếp trên Samsung S7 qua ADB?
- Trên app Gmail / Cài đặt tài khoản của Android:
  - Mục **"Xác minh 2 bước" (2-Step Verification)** không chạy native mà mở một cửa sổ WebView mới.
  - Cửa sổ này đối với Google là một **phiên bảo mật nhạy cảm (high-risk security session)** không có sẵn cookie duyệt web.
  - Khi phát hiện mạng farm / proxy di động, Google **BẮT BUỘC** bật lớp bảo vệ:
    1. **reCAPTCHA danh tính** ("Xác nhận bạn không phải là rô-bốt").
    2. Bấm "Thử cách khác" sẽ báo ngay: *"Không thể đăng nhập cho bạn. Google không thể xác minh rằng tài khoản này là của bạn."*
  - Trên điện thoại qua ADB không có extension/audio solver để giải captcha, dẫn đến kẹt 100% không thể tự động hóa.

### Vì sao GPM Chrome PC lại bật 2FA thành công 100%?
- **Đã có Web Browser Session:** Profile GPM Chrome lưu giữ chuỗi cookie web chuẩn (`SID`, `SSID`, `HSID`, `__Secure-3PSID`...) cùng Fingerprint PC hoàn chỉnh.
- **Có Audio Captcha Solver:** Script `run_add_2fa_remaining.py` tích hợp module `solve_recaptcha_audio` (tải audio challenge, dùng speech recognition convert sang text) vượt qua reCAPTCHA của Google tự động.
- **Tự động trích xuất Base32 Secret Key & TOTP:** Đi thẳng vào URL `https://myaccount.google.com/two-step-verification/authenticator`, bóc 32 ký tự Secret Key, sinh mã TOTP True UTC và verify ngay tại chỗ.

---

## 2. Thứ Tự Điều Phối Chuẩn: Tạo ChatGPT vs Bật 2FA vs Login GPM

### Nghịch lý thường gặp:
- *"Chưa bật 2FA thì mang lên GPM hay bị đòi SMS verify / checkpoint."*
- *"Nhưng muốn bật 2FA trên S7 thì Google lại chặn ở WebView reCAPTCHA."*

### Giải pháp và trình tự chuẩn:
1. **Bước 1: Reg Gmail & Nuôi trên S7**
   - Gmail được tạo và hoạt động trên thiết bị thật (S7) qua proxy 4G chuẩn của máy.
   - Ngâm tối thiểu 3-7 ngày để tích lũy thiết bị và IP trust.

2. **Bước 2: Tạo Profile GPM gắn CHUẨN Proxy 4G của máy S7 đó**
   - Kiểm tra `PROXYgandienthoai.xlsx` để lấy đúng cổng proxy của máy (ví dụ Máy 05 dùng port 5105, Máy 09 dùng port 5111).
   - Tuyệt đối không dùng proxy khác IP / khác cụm kẻo Google kích hoạt checkpoint vị trí.

3. **Bước 3: Login Google lên GPM Chrome & Phối Hợp Google Prompt với S7**
   - Mở profile qua GPM API v3 (`port 19995`).
   - Dùng Playwright điền email, mật khẩu.
   - **Hiện tượng Google Prompt (Xác minh thiết bị Galaxy S7):**
     - Do tài khoản đã ngâm trên S7 và GPM chạy đúng proxy 4G của máy đó, Google **KHÔNG đòi SMS số điện thoại** mà gửi **thông báo số (Google Prompt)** về máy S7 ("Nhấn vào Có rồi chọn số XX").
     - **Cơ chế phối hợp với S7 qua ADB:**
       + Bật sáng màn hình S7 (`input keyevent 224`), mở khóa (`input keyevent 82`).
       + Bắt thông báo Google Prompt nổi lên trên S7 -> Tap "Có, chính là tôi" -> Chọn đúng số tương ứng trên màn hình GPM.
       + **HOẶC dùng phương án Security Code (Mã bảo mật 10 số):** Trên GPM bấm "Thử cách khác" (Try another way) -> chọn "Lấy mã bảo mật từ thiết bị Android" -> Dùng ADB vào Settings -> Google -> Quản lý tài khoản -> Bảo mật -> Mã bảo mật trên S7 lấy 10 số điền vào GPM (chuẩn theo `s7_helper_clean.py`).
     - Sau khi vượt qua bước này, tài khoản đăng nhập thành công vào Google Account trên GPM!

4. **Bước 4: Bật 2FA Google Authenticator trên GPM ngay lập tức**
   - Chạy `setup_authenticator_for_profile` trong `D:/Taadaa/GPM auto/scripts/run_add_2fa_remaining.py`.
   - Trích xuất Secret Key, lưu đồng bộ vào:
     - `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` (cột D / 2FA).
     - `D:/OneDrive/TaadaaData/kibe/master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7` & `Master_All`).

5. **Bước 5: Đăng ký / Liên kết ChatGPT**
   - Khi tài khoản đã có 2FA và có session GPM:
     - Đăng ký ChatGPT trên Web GPM hoặc trên S7 đều an toàn.
     - Dù Google có hỏi lại OTP, hệ thống chỉ cần đọc Secret Key từ Excel để sinh mã TOTP là vượt qua trong 2 giây, không bao giờ bị đòi SMS số điện thoại.
