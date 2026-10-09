# Quy Trình Bật 2FA Gmail: Bỏ On-Device S7 -> Chuyển Hoàn Toàn Sang GPM Profile

## 1. Bản chất vì sao bỏ Bật 2FA trên điện thoại Samsung S7
- Khi truy cập mục "Xác minh 2 bước" (2-Step Verification) trong app Gmail/Cài đặt Google trên điện thoại Android:
  - Google bắt buộc mở một cửa sổ **WebView bảo mật** mới để xác minh lại danh tính.
  - Cửa sổ này không có cookie web trước đó và nhận diện IP farm nên Google bật ngay **reCAPTCHA danh tính** hoặc báo lỗi *"Google không thể xác minh danh tính tài khoản này"*.
  - Trên điện thoại qua ADB, bot **không có extension hay công cụ giải captcha âm thanh tự động**, dẫn đến luồng on-device bị kẹt 100% và gây timeout cho worker/watchdog.

## 2. Quy trình chuẩn hóa trên GPM Profile
1. **Kiểm tra / Tạo Profile GPM:**
   - Map đúng Proxy 4G của máy S7 đó từ file `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
   - Gọi GPM API v3 (`http://127.0.0.1:19995/api/v3/profiles/create`):
     `{"profile_name": "<machine> - <email> - <port>", "raw_proxy": "<proxy>", "group_id": 1, "browser_type": "Chrome"}`.
2. **Đăng nhập Google trên GPM Chrome:**
   - Kết nối Playwright sync qua CDP (`remote_debugging_address`).
   - Vào `https://accounts.google.com/ServiceLogin?hl=vi`.
   - Điền Email -> Điền Password.
   - Nếu gặp reCAPTCHA: Sử dụng module `solve_recaptcha_audio` (tự động tải file âm thanh `.mp3` -> convert `.wav` bằng ffmpeg -> nhận diện bằng `speech_recognition` -> điền kết quả tự động trong 5 giây).
   - Nếu gặp màn hình thêm thông tin khôi phục (SĐT / Email khôi phục) -> Bấm "Huỷ" / "Để sau".
3. **Kích hoạt 2FA Google Authenticator:**
   - Điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator?hl=vi`.
   - Bấm "Thiết lập Authenticator" -> "Không thể quét mã".
   - Trích xuất chuỗi Base32 Secret Key (32 ký tự).
   - Dùng `pyotp.TOTP(secret_key).now()` sinh mã OTP True UTC 6 chữ số.
   - Điền mã OTP -> Bấm Xác minh -> Hoàn tất.
4. **Đồng bộ Dữ liệu & Nghiệm thu:**
   - Lưu Base32 Secret Key vào Cột D (`2FA`) của `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
   - Chụp ảnh toàn màn hình nghiệm thu (`MEDIA:<path_anh>`).
   - Đóng profile GPM an toàn qua API `/api/v3/profiles/close/<id>`.

## 3. Kiến trúc Chống Timeout: Tách "Chờ Đợi" ra khỏi Worker
- **Coordinator Preflight O(1):**
  - Dùng `TaskQueue.check_preflight_free(machine)` trước khi dispatch worker.
  - Máy rảnh -> Dispatch worker (<2 phút là xong).
  - Máy bận cron nuôi TikTok -> KHÔNG dispatch worker, đẩy vào `operator_task_queue.json`, để Watchdog ngoài band tự động đón đầu khi máy nhả lock.
- **Code Enforcement (`SafeAdb` & `adb_guard`):**
  - Mọi thao tác ADB bắt buộc qua `with safe_adb.acquire():` hoặc `DeviceContext(force_preempt=False)`. CẤM phá lock ca nuôi.
