# Quy trình Thiết lập Google Authenticator 2FA qua GPM & S7 Phone Farm

## 1. Mục tiêu
Thiết lập 2FA dạng TOTP (Google Authenticator) cho tài khoản Gmail nuôi trên GPM Profile, kết hợp vượt xác minh Security Code (Mã bảo mật 10 số) từ thiết bị Android Samsung S7 tương ứng.

## 2. Các thành phần & Dữ liệu tham chiếu
- **Tool / Repo**: `D:\Taadaa\add-gmail-2fa`
- **File tài khoản**: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Cột 1: Machine ID, Cột 2: Email, Cột 3: Password, Cột 4: 2FA Secret Key)
- **File ánh xạ proxy/serial**: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
- **GPM Local API**: `http://127.0.0.1:19995/api/v3/profiles`
- **Playwright CDP / Persistent Context**: Điều khiển browser GPM profile hoặc Chromium kèm proxy farm `http://192.168.110.2:{20000 + machine_id}`.

## 3. Khóa chống tranh chấp (DeviceContext Lock)
Trước khi thao tác thiết bị vật lý S7 để lấy mã hoặc chạy canary, bắt buộc acquire lease:
```python
import sys
sys.path.insert(0, r"D:\Taadaa\automation-core\src")
from automation_core.device_lock import DeviceContext, DeviceLockUnavailable

with DeviceContext(serial=device_serial, machine=str(machine_id), project="canary-gpm-2fa", force_preempt=False) as lease:
    # Thao tác ADB và CDP tại đây
```

## 4. Các bước tự động hóa chính
1. **Mở URL Authenticator**: `https://myaccount.google.com/two-step-verification/authenticator` (thêm `?hl=vi` để đảm bảo locale tiếng Việt nhất quán).
2. **Xử lý đăng nhập / Re-auth**:
   - Nhập email và password nếu trang yêu cầu.
   - Nếu Google yêu cầu **Mã bảo mật (Security Code 10 số)**: gọi helper ADB trên máy S7 (`get_s7_security_code` qua `com.google.android.gms/.app.settings.GoogleSettingsLink`), lấy mã 10 số và submit.
3. **Mở modal thêm Authenticator**:
   - Click nút "Thiết lập" (`Set up`).
   - Click liên kết "Không thể quét mã QR?" (`Can't scan it?`) để hiển thị chuỗi khóa bí mật dạng Base32 (32 ký tự).
4. **Trích xuất Secret Key & Tạo mã OTP**:
   - Regex tìm chuỗi Base32: `re.search(r'([A-Z2-7]{32})', ...)`.
   - Sinh TOTP 6 số tức thì qua thư viện `pyotp.TOTP(secret).now()`.
5. **Xác minh & Phê duyệt**:
   - Click "Tiếp theo", điền 6 số OTP vào ô xác minh và click "Xác minh".
   - Kiểm tra nếu xuất hiện dialog phụ: "Phê duyệt trình xác thực này?" (`Approve this authenticator?`), bấm click "Phê duyệt" để hoàn tất lưu.
6. **Lưu trữ Secret Key**:
   - Cập nhật Secret Key vào cột 4 của dòng tài khoản tương ứng trong `gmail_clean_v2.xlsx`.
   - Chụp ảnh màn hình evidence lưu tại `D:\Taadaa\runtime\kibe\`.
