# Chuyển dịch Bật 2FA: Bỏ On-Device Samsung S7 -> Bật trên GPM Profile & Cơ chế Preflight Lock Tránh Worker Timeout

## 1. Bản chất cốt lõi: Vì sao bỏ bật 2FA trên điện thoại S7?
- **Trên Samsung S7 qua ADB:** Khi vào mục Cài đặt Google -> "Xác minh 2 bước", app Gmail/Google Settings không chạy native mà mở một cửa sổ WebView mới toanh. Cửa sổ này không có cookie duyệt web trước đó, Google xếp vào High-risk Action và kích hoạt ngay **reCAPTCHA danh tính** hoặc báo lỗi *"Google không thể xác minh..."*. Trên Android ADB không thể tự động hóa giải captcha, dẫn đến kẹt và timeout 100%.
- **Trên GPM Profile (Playwright CDP):** 
  - GPM Chrome chạy đúng Proxy 4G của máy S7 đó.
  - Được Google nhận diện là trình duyệt Desktop chính quy.
  - Tích hợp sẵn bộ giải audio captcha (`solve_recaptcha_audio` qua `pydub` + `speech_recognition` + `ffmpeg-8.0`).
  - Google cho qua mượt mà, truy cập thẳng `myaccount.google.com/two-step-verification/authenticator` để bóc Base32 Secret Key và nhập TOTP kích hoạt 2FA thành công.

## 2. Quy trình chuẩn (Standard Workflow)
```
1. Reg Gmail trên S7 (ngâm >= 1-3 ngày trên farm, tạo trust).
2. Tạo Profile GPM (Map đúng Proxy 4G của máy S7 đó).
3. Đăng nhập Google trên GPM Chrome:
   - Điền email & pass.
   - Nếu gặp reCAPTCHA: Tự động giải bằng module audio captcha.
   - Nếu gặp Google Prompt (chọn số trên S7): Mở S7 qua DeviceContext, xác nhận số.
   - Bỏ qua màn hình thêm thông tin khôi phục.
4. Kích hoạt 2FA trên GPM:
   - Vào myaccount.google.com/two-step-verification/authenticator
   - Bấm "Thiết lập Authenticator" -> "Không thể quét mã" -> Lấy Base32 Secret Key (32 ký tự).
   - Dùng pyotp sinh mã TOTP True UTC -> Xác minh -> Hoàn tất!
5. Lưu Secret Key vào file quản trị (gmail_clean_v2.xlsx).
```

## 3. Khắc phục triệt để lỗi "Worker chờ lock bị timeout 600s"
- **Nguyên nhân:** Worker là đơn vị thực thi ngắn (<2 phút, ngốn token). Khi máy S7 đang bận ca nuôi TikTok 15-30 phút, nếu Worker đứng chờ cuốn chiếu (rolling-wait `sleep(30s)`) sẽ cạn trần 600s timeout và chết.
- **Kiến trúc 3 tầng giải quyết triệt để:**
  1. **Coordinator Preflight Check O(1):** Trước khi dispatch worker, Coordinator kiểm tra nhanh qua `TaskQueue.check_preflight_free(machine)`.
     - Nếu máy **RẢNH**: Dispatch worker thực thi ngay (<2 phút là xong).
     - Nếu máy **BẬN CRON**: TUYỆT ĐỐI KHÔNG dispatch worker. Đẩy task vào `TaskQueue` (persistent JSON queue) và báo cáo user.
  2. **SafeAdb & AdbGuard Layer (automation-core):**
     - Mọi lệnh ADB bắt buộc bọc qua `SafeAdb` với `DeviceContext(force_preempt=False)` (cấm tuyệt đối phá lock cron).
     - `adb_guard.py` monkey-patch `subprocess.run`, chặn đứng mọi lệnh ADB nếu chưa giữ lock thiết bị.
  3. **Watchdog ngoài band:** Quá trình chờ máy rảnh do tiến trình watchdog chạy ngầm ngoài band đảm nhiệm (không tốn token LLM, không bị giới hạn timeout 600s). Khi ca nuôi xong nhả lock, watchdog sẽ đón đầu thực thi task.
