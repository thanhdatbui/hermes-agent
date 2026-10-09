# GPM API & S7 Google Prompt Coordination Workflow

## 1. ADB Environment Note (Taadaa Host)
- Trên host Windows này, lệnh `adb` không nằm trong biến môi trường PATH mặc định của bash/terminal.
- Đường dẫn thực thi ADB chuẩn:
  `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`
- Sử dụng trực tiếp trong script Python:
  ```python
  ADB_EXE = r"C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe"
  subprocess.run([ADB_EXE, "-s", serial, "shell", ...])
  ```

---

## 2. GPM Local API (v3 - Port 19995) + Playwright CDP
### Start Profile qua API
```python
import requests
from playwright.sync_api import sync_playwright

profile_id = "64769d3c-52fa-4e56-a287-703aef0b85b1"
res = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}").json()
if not res.get("success"):
    raise RuntimeError(f"GPM start failed: {res}")

remote_debugging_address = res["data"]["remote_debugging_address"]
# Ví dụ: 127.0.0.1:12345
```

### Kết nối CDP Playwright
```python
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(f"http://{remote_debugging_address}")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://accounts.google.com/ServiceLogin")
```

---

## 3. Quy trình Phối hợp Google Prompt / Mã bảo mật trên S7
Khi đăng nhập tài khoản Google trên GPM, Google có thể kích hoạt bảo mật yêu cầu xác minh qua điện thoại S7 đã gắn:

### Trường hợp 1: Google Prompt (Hiện số xác minh, ví dụ: 18)
1. **Trên trình duyệt GPM**:
   - Đọc số yêu cầu hiển thị trên trang (ví dụ: "Nhấn vào số 18 trên điện thoại").
2. **Trên điện thoại S7**:
   - Đánh thức và mở khóa màn hình:
     ```bash
     adb -s <serial> shell input keyevent 224
     adb -s <serial> shell input keyevent 82
     ```
   - Mở thanh thông báo nếu chưa hiện popup:
     ```bash
     adb -s <serial> shell cmd statusbar expand-notifications
     ```
   - Tap vào thông báo "Bạn đang cố đăng nhập?" (hoặc Google Play services prompt).
   - Chọn nút "Có, chính là tôi" (Yes, it's me).
   - Chọn đúng con số mà Google hiển thị trên trình duyệt GPM.

### Trường hợp 2: Thử cách khác -> Mã bảo mật 10 số (Security Code)
Nếu Google Prompt không gửi tới được thiết bị:
1. Trên trình duyệt GPM, bấm **"Thử cách khác" (Try another way)** -> Chọn **"Lấy mã bảo mật từ cài đặt Google"**.
2. Trên S7:
   - Mở Google Settings:
     ```bash
     adb -s <serial> shell am start -n com.google.android.gms/.app.settings.GoogleSettingsLink
     ```
   - Chọn đúng tài khoản Gmail cần xác minh.
   - Bấm **"Quản lý Tài khoản Google của bạn"** -> Chọn tab **"Bảo mật" (Security)**.
   - Bấm **"Mã bảo mật" (Security code)**.
   - Đọc mã 10 số (dạng `XXXXX XXXXX`) và điền vào ô xác minh trên trình duyệt GPM.

---

## 4. Kích hoạt 2FA Authenticator & Đồng bộ dữ liệu
1. Sau khi vào được phiên Google Account:
   - Điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator`.
   - Bấm **"Thiết lập ứng dụng xác thực"** (Set up authenticator).
   - Bấm **"Không thể quét mã?"** (Can't scan it?).
   - Lấy chuỗi **Secret Key 32 ký tự Base32**.
2. Sinh mã xác minh TOTP chuẩn UTC:
   ```python
   import pyotp
   totp = pyotp.TOTP(secret_key)
   otp_code = totp.now()
   ```
3. Nhập mã OTP vào trang Google -> Bấm **"Xác minh"** (Verify).
4. Lưu ảnh bằng chứng hoàn tất:
   ```python
   page.screenshot(path=r"D:\Taadaa\runtime\kibe\gpm_2fa_m09_success.png", full_page=True)
   ```
5. Đồng bộ Secret Key vào file quản lý tập trung:
   - `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Cột 4: 2FA secret).
6. Đóng trình duyệt và stop GPM profile:
   ```python
   requests.get(f"http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}")
   ```
