# Hướng dẫn Bật 2FA trên GPM Profile thay thế hoàn toàn on-device Samsung S7

## 1. Tại sao chuyển dịch từ Samsung S7 sang GPM Profile?
- **Samsung S7 qua ADB:** Khi vào mục Cài đặt Google -> "Xác minh 2 bước", app Gmail/Google Settings mở một cửa sổ WebView bảo mật không lưu cookie duyệt web trước đó. Google lập tức bật **reCAPTCHA danh tính** hoặc báo lỗi *"Google không thể xác minh..."*. ADB trên điện thoại không thể giải captcha tự động, dẫn tới fail và timeout 100%.
- **GPM Profile (Chrome Desktop):**
  - Chạy qua đúng Proxy 4G của máy S7 đó.
  - Được Google nhận diện là trình duyệt Desktop chính quy.
  - Tích hợp module giải audio captcha tự động (`solve_recaptcha_audio` qua `pydub` + `speech_recognition` + `ffmpeg-8.0`).
  - Google cho vào thẳng hoặc chỉ qua reCAPTCHA audio 5s là tới trang Authenticator.
  - Bóc Base32 Secret Key (32 ký tự) và kích hoạt 2FA thành công 100%.

## 2. Quy trình chuẩn từng bước (Canonical Workflow)
1. **Khởi tạo Profile GPM:**
   - POST `http://127.0.0.1:19995/api/v3/profiles/create`
   - Gắn `raw_proxy` đúng proxy của máy S7 (lấy từ `PROXYgandienthoai.xlsx`).
2. **Đăng nhập Google:**
   - Mở profile qua GPM API, kết nối Playwright qua CDP.
   - Điền email & password.
   - Nếu có reCAPTCHA -> tự động giải bằng audio captcha solver.
   - Nếu có màn hình phục hồi (Thêm SĐT/email) -> bấm "Huỷ" / "Để sau".
   - Nếu có Google Prompt (chọn số trên S7) -> mở màn hình S7 qua `DeviceContext(force_preempt=False)`, xác nhận số.
3. **Kích hoạt Google Authenticator:**
   - Truy cập: `https://myaccount.google.com/two-step-verification/authenticator?hl=vi`
   - Bấm "Thiết lập Authenticator" -> "Không thể quét mã".
   - Bóc Secret Key Base32 (32 ký tự).
   - Dùng `pyotp.TOTP(secret_key).now()` sinh mã True UTC -> điền mã -> Bấm Xác minh.
4. **Đồng bộ Excel & Đóng Profile:**
   - Ghi Secret Key vào cột D (`2FA`) của `gmail_clean_v2.xlsx`.
   - Đóng browser và gọi API close profile.

## 3. Khắc phục lỗi Worker Timeout 600s khi máy bận
- Trước khi dispatch worker, Coordinator kiểm tra lock O(1) qua `TaskQueue.check_preflight_free(machine)`.
- Nếu máy bận cron nuôi TikTok -> Không dispatch worker, đẩy vào `TaskQueue` chờ cuốn chiếu.
- Sử dụng module `SafeAdb` và `adb_guard` trong `automation-core` để đảm bảo cấm tuyệt đối phá lock cron (`force_preempt=False`).
