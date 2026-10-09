# AdbClient Constructor Positional vs Keyword Argument Pitfall

## Triệu chứng
Khi khởi tạo `AdbClient` để dump UI hoặc gửi lệnh ADB tới thiết bị:
```python
from automation_core.adb import AdbClient

adb = AdbClient(device_serial)
```
Gây ra lỗi:
```
ADBError: adb executable not found: ce031603b3158b0b02
```
Kèm theo đó là các hàm downstream như `capture_atx_session_ui(adb)` trả về `None` với `failure_signature='ATX_CAPABILITY_PROBE_FAILED'`.

## Nguyên nhân
Chữ ký của hàm khởi tạo `AdbClient.__init__`:
```python
def __init__(
    self,
    adb_path: str = 'adb',
    serial: str | None = None,
    default_timeout: float = 15,
    ...
)
```
Tham số đầu tiên theo thứ tự vị trí (positional argument) là `adb_path`, KHÔNG PHẢI `serial`.
Khi truyền `AdbClient(device_serial)`, chuỗi serial bị gán nhầm thành đường dẫn binary `adb`.

## Cách khắc phục chuẩn
Luôn luôn truyền serial bằng keyword argument rõ ràng:
```python
# ĐÚNG:
adb = AdbClient(serial=device_serial)

# HOẶC khi tuỳ chỉnh adb binary:
adb = AdbClient(adb_path="adb", serial=device_serial)
```
Quy tắc này áp dụng cho mọi consumer script của `automation-core` (Tiktok-video, tiktok-log-in, tiktok-follow, tiktok-luot nuoi acc, v.v.).
