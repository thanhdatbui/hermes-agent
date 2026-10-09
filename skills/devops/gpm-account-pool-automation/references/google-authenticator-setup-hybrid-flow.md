# Quy trình Bật 2FA Google Authenticator Hybrid (Playwright + S7 ADB Security Code)

## 1. Bối cảnh & Mục đích
- Tự động bật Google Authenticator (TOTP) cho toàn bộ Gmail trong farm Samsung S7.
- Repo quản lý độc lập: `D:\Taadaa\add-gmail-2fa`.
- Dữ liệu nguồn và đích:
  - Excel danh sách Gmail: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Cột 4: `2fa`, Cột 2: `tài khoản gmail`).
  - Excel Master: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`.
  - Proxy & Serial mapping: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
  - ADB chuẩn: `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`.

## 2. Các điểm cốt lõi kỹ thuật (Key Pitfalls & Workarounds)

### 2.1. Bỏ qua Shadow DOM bằng Direct URL
- Khi truy cập trang quản lý 2-Step Verification chính (`https://myaccount.google.com/signinoptions/two-step-verification`), Google render nhiều thành phần dạng Shadow DOM khiến Playwright khó selector chính xác nút bấm.
- **Giải pháp:** Điều hướng thẳng vào URL Authenticator:
  `https://myaccount.google.com/two-step-verification/authenticator`
- Bấm nút "Thiết lập" / "Set up" với `force=True`.

### 2.2. Trích xuất Secret Key Base32 (32 ký tự)
- Khi popup hiện QR code, không cần quét hình ảnh QR. Bấm nút:
  `div[role="dialog"] button:has-text("quét"), div[role="dialog"] button:has-text("scan"), div[role="dialog"] button:has-text("Can")` ("Không thể quét mã?" / "Can't scan?").
- Google sẽ hiển thị chuỗi Secret Key Base32 dạng 32 ký tự (thường chia thành các cụm 4 chữ số cách nhau bởi khoảng trắng).
- Regex trích xuất chuỗi:
  `r"([a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4})"` hoặc kiểm tra `len(cleaned) == 32 and cleaned.isalnum()`.
- Tạo mã xác nhận ngay lập tức qua `pyotp`:
  ```python
  import pyotp
  totp_code = pyotp.TOTP(secret_key).now()
  ```
- Nhập mã vào input trong dialog và bấm "Verify" / "Xong" để hoàn tất kích hoạt.

### 2.3. Giải quyết Challenge OTP / Mã bảo mật 10 số qua Samsung S7 ADB
- Nếu Google yêu cầu xác minh danh tính khi truy cập:
  1. Chọn "Thử cách khác" ("Try another way").
  2. Chọn mục "Nhận mã bảo mật" ("Get security code").
  3. Mở S7 qua ADB:
     - Đánh thức máy: `dumpsys power` -> `keyevent 26`, `keyevent 82`, vuốt mở khóa.
     - Khởi chạy Settings: `am start -a android.settings.SETTINGS`.
     - Tìm mục Google -> Chọn đúng email mục tiêu nếu đang chọn tài khoản khác.
     - Bấm "Tài khoản Google" -> Tab "Bảo mật" -> "Mã bảo mật".
     - Đọc UI hierarchy qua ATX Agent `tcp:7912` (forward sang `tcp:17000+machine_id`), lọc chuỗi 10 chữ số.
     - Điền 10 chữ số vào màn hình browser để vượt checkpoint.

### 2.4. Lưu trữ Secret Key vào Excel
- Ghi vào Cột 4 của `gmail_clean_v2.xlsx` cho dòng có email khớp.
- Ghi vào cột có header chứa `2fa` hoặc `secret` trong `master_gmail_manager.xlsx`.
