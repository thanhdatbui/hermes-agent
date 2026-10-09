# Google Authenticator 2FA Setup via GPM CDP & S7 Phone

## Quy trình canary / production bật 2FA Authenticator cho Gmail trên GPM

### 1. Chuẩn bị & Safety Preflight
- **Device Lock**: Bắt buộc giữ lock thiết bị Android S7 tương ứng trước khi thao tác:
  ```python
  from automation_core.device_lock import DeviceContext
  with DeviceContext(serial=serial, machine=machine, project="gpm-2fa-setup", force_preempt=False):
      ...
  ```
- **ADB Client Pitfall**:
  - `automation_core.adb.AdbClient` nhận tham số đầu tiên là `adb_path: str = 'adb'`, thứ hai mới là `serial: str | None = None`.
  - **LỖI THƯỜNG GẶP**: Gọi `AdbClient("ce0416041bdb271305")` sẽ khiến `adb_path` bị gán nhầm thành chuỗi serial -> lỗi `adb executable not found: ce0416...`.
  - **CÁCH GỌI ĐÚNG**: Dùng keyword argument: `AdbClient(serial="ce0416041bdb271305")` hoặc chỉ định path nếu adb chưa trong PATH: `AdbClient(adb_path=r"C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe", serial=serial)`.

### 2. GPM Profile & Playwright CDP Flow
1. Khởi động profile qua Local API v3: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
2. Lấy `remote_debugging_address` và kết nối bằng `playwright.chromium.connect_over_cdp(f"http://{addr}")`.
3. Đăng nhập Google Account (`https://accounts.google.com/ServiceLogin?hl=vi`):
   - Điền email & password.
   - Nếu có Google Prompt / OOTP gửi về máy S7: Gửi keyevent bật màn hình S7 (`224`, `82`) và xác nhận.
   - Bỏ qua popup thêm số điện thoại / recovery mail nếu có.
4. Điều hướng tới cài đặt Authenticator:
   - URL: `https://myaccount.google.com/two-step-verification/authenticator?hl=vi`
   - Bấm "Thiết lập ứng dụng xác thực" / "Set up authenticator".
   - Chọn "Không thể quét mã" ("Can’t scan it") để hiển thị Base32 Secret Key dạng text.
5. Trích xuất Secret Key & Tạo mã OTP:
   - Regex tìm chuỗi Base32: `([A-Z2-7]{4}(?:\s+[A-Z2-7]{4}){7})`.
   - Chuẩn hóa: `secret_key = raw_key.replace(" ", "").upper()`.
   - Sinh OTP bằng `pyotp.TOTP(secret_key).now()`.
   - Nhập OTP vào ô xác minh trên trang web và bấm Verify.
6. Cập nhật Excel & Bằng chứng:
   - Chụp screenshot bằng chứng full-page.
   - Lưu `secret_key` vào cột 2FA (Cột 4 / D) trong `gmail_clean_v2.xlsx`.
7. Đóng CDP và gọi `GET http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}`.
