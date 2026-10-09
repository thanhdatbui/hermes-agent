# ADB Client Signature & Windows Path Pitfalls in Automation-Core

## 1. AdbClient Init Signature Trap
Trong `automation_core.adb`:
```python
class AdbClient:
    def __init__(
        self,
        adb_path: str = "adb",
        serial: str | None = None,
        default_timeout: float = 15,
        ...
    ):
```
- **Pitfall**: Tham số đầu tiên là `adb_path`, không phải `serial`.
  Nếu gọi:
  ```python
  client = AdbClient("ce0416041bdb271305")
  ```
  Python sẽ gán `self.adb_path = "ce0416041bdb271305"` và `self.serial = None`.
  Khi chạy lệnh `client.shell(...)` hoặc `client.run(...)`, tiến trình sẽ cố gắng thực thi file nhị phân tên là `"ce0416041bdb271305"` và ném ra:
  ```
  automation_core.adb.ADBError: adb executable not found: ce0416041bdb271305
  ```

- **Correct Pattern**:
  Luôn dùng named argument hoặc truyền đúng thứ tự:
  ```python
  # Khi adb đã có trong PATH:
  client = AdbClient(serial="ce0416041bdb271305")

  # Khi adb không có trong system PATH (ví dụ trên Windows qua GemPhoneFarm):
  ADB_BIN = r"C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe"
  client = AdbClient(adb_path=ADB_BIN, serial="ce0416041bdb271305")
  ```

## 2. Tìm nhanh ADB binary trên môi trường Windows Host
Khi môi trường bash/git-bash không có `adb` trong `$PATH`:
- Vị trí phổ biến của GemPhoneFarm:
  `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`
- Kiểm tra bằng python trước khi khởi tạo client:
  ```python
  import shutil
  adb_path = shutil.which("adb") or r"C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe"
  client = AdbClient(adb_path=adb_path, serial=serial)
  ```
