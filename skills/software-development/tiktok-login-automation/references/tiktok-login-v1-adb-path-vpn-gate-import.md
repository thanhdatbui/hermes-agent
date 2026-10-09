# Pitfall: Missing ADB_PATH Import in tiktok_login_v1.py Causes Silent Fallback to System 'adb'

## Triệu chứng & Vấn đề
Trong `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py` (khoảng dòng 604):
```python
require_android_vpn(
    AdbClient(
        adb_path=ADB_PATH if "ADB_PATH" in globals() else "adb",
        serial=device_id
    ),
    required=required
)
```
Nếu `ADB_PATH` không được import từ `social_reg_v1`, biểu thức `"ADB_PATH" in globals()` âm thầm trả về `False`. Kết quả là `AdbClient` rơi về `"adb"` thay vì sử dụng đúng đường dẫn xiaowei adb (`C:\Program Files (x86)\xiaowei\tools\adb.exe` được khai báo trong `social_reg_v1.py`).
Nếu môi trường terminal chưa export PATH hoặc trên Windows service không có `adb` trong system PATH, bước preflight VPN gate (`require_android_vpn`) sẽ ném exception chặn runner ngay từ đầu (`[device-lock] VPN GATE BLOCKED`).

## Cách khắc phục triệt để
Đảm bảo import rõ ràng `ADB_PATH` ở cả hai khối import trong `tiktok_login_v1.py`:

```python
try:
    from .device_lock import DeviceLockNeedsUserDecision, DeviceLockUnavailable, acquire_device_lock
    from .gmail_machine_audit import live_gmail_accounts
    from .social_reg_v1 import (
        ACCOUNTS,
        ADB_PATH,
        D_LONG,
        ...
    )
except ImportError:
    from device_lock import DeviceLockNeedsUserDecision, DeviceLockUnavailable, acquire_device_lock
    from gmail_machine_audit import live_gmail_accounts
    from social_reg_v1 import (
        ACCOUNTS,
        ADB_PATH,
        D_LONG,
        ...
    )
```

Kiểm tra cú pháp sau khi sửa:
```bash
python -m py_compile D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py
```

## Khuyến nghị khi chạy runner
Khi chạy script đăng nhập chính thức từ Git Bash / terminal trên Windows host:
```bash
export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH"
cd /d/Taadaa/Tiktok_Reg
python tiktok_login_v1.py <STT> --email <email> --ss
```
Lệnh này kích hoạt đầy đủ:
- VPN gate preflight với AdbClient trỏ đúng `adb.exe`.
- Tự động lấy OTP (Gmail app / Outlook app / Graph API) hoặc TOTP authenticator 2FA.
- Chụp ảnh bằng chứng từng bước (`--ss`). Nghiệm thu kết quả bắt buộc tại Account Switcher (Bottom sheet Chuyển đổi tài khoản).
