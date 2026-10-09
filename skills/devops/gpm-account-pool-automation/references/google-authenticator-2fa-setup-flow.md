# Quy trình tự động bật 2FA Google Authenticator qua GPM Profile & Playwright CDP

## 1. Mục đích & Phạm vi
- Hướng dẫn và script tự động kích hoạt tính năng **Google Authenticator (2FA)** trên tài khoản Gmail đã đăng nhập sẵn trong GPM profile.
- Tự động vượt qua reCAPTCHA audio challenge (nếu Google yêu cầu xác minh danh tính).
- Lấy chuỗi mã bí mật Base32 (32 ký tự), sinh mã xác nhận TOTP True UTC, verify và lưu kết quả vào Excel quản lý.

## 2. Đường dẫn kịch bản & File dữ liệu
- Script chính: `D:\Taadaa\GPM auto\scripts\run_add_2fa_remaining.py`
- Master Excel: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7` & `Master_All`)
- Clean V2 Excel: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`
- Ảnh chụp chứng nhận: `D:\Taadaa\GPM auto\debug_screenshots\add_2fa\`

## 3. Các bước xử lý cốt lõi
1. **Khởi động GPM Profile qua API**:
   - Gọi `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
   - Trích xuất remote debugging port từ `data.remote_debugging_address`.
2. **Kết nối Playwright qua CDP**:
   - `browser = pw.chromium.connect_over_cdp(f"http://{cdp_addr}")`
3. **Điều hướng thẳng tới URL Authenticator**:
   - `https://myaccount.google.com/two-step-verification/authenticator`
4. **Xử lý Challenge**:
   - **reCAPTCHA Challenge**: Tự động nhận diện nút checkbox reCAPTCHA, chuyển sang audio challenge, tải âm thanh WAV và giải mã speech text qua `speech_recognition` (Google STT).
   - **Password Challenge**: Nếu URL chuyển hướng về `challenge/pwd` hoặc xuất hiện ô password, điền password tương ứng từ Excel database và submit.
5. **Kích hoạt Authenticator & Lấy Secret Key**:
   - Click nút `Thiết lập` / `Set up`.
   - Click `Không thể quét mã?` / `Can't scan it?`.
   - Trích xuất Base32 Secret Key 32 ký tự từ text của modal.
   - Click nút `Tiếp theo` / `Next`.
   - Sinh mã TOTP 6 số dựa trên Base32 secret và True UTC: `pyotp.TOTP(secret_key).now()`.
   - Điền 6 chữ số vào ô xác minh và click `Xác minh` / `Verify`.
6. **Đồng bộ hóa & Lưu bằng chứng**:
   - Chụp full-page screenshot lưu vào thư mục `debug_screenshots/add_2fa/`.
   - Cập nhật Secret Key vào cột `2FA` trong `gmail_clean_v2.xlsx` và cột `2fa_secret` trong `master_gmail_manager.xlsx`.
   - Dọn sạch tiến trình: Đóng browser context, stop profile qua API và kill tiến trình Chrome port tương ứng.
