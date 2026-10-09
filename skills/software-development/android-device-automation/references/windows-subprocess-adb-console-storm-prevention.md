# Chống Lỗi Nháy Cửa Sổ Console adb.exe (Console Storm) Trên Windows

## 1. Hiện Tượng (Symptoms)
- Khi chạy các script Python nền, cron job, watchdog, hoặc auto-healer đa luồng trên Windows (như `cron_clear_tiktok_cache.py`, `farm_idle_screen_and_app_healer.py`, `farm_wifi_auto_healer.py`):
- Màn hình liên tục nhấp nháy hàng chục đến hàng trăm cửa sổ console / command prompt màu đen của tiến trình `adb.exe`.
- Cửa sổ console chớp tắt liên hồi ("console storm"), cướp focus nhập liệu của người dùng, gây giật lag UI Windows và cản trở thao tác trên máy tính farm.

---

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
- Mặc định trên hệ điều hành Windows, khi một tiến trình Python gọi `subprocess.run` hoặc `subprocess.Popen` để khởi chạy một binary thuộc phân hệ console subsystem (như `adb.exe`), Windows kernel sẽ cấp phát và hiển thị một cửa sổ console mới trừ khi tiến trình cha yêu cầu cấm hiển thị qua cờ process creation flag.
- Trong các watchdog hoặc batch runner chạy song song với `ThreadPoolExecutor(max_workers=20..30)`, số lượng tiến trình `adb.exe` được kích hoạt liên tục trong thời gian ngắn khiến hàng loạt cửa sổ console xuất hiện đồng loạt.

---

## 3. Giải Pháp Chuẩn (Canonical Solution)

Sử dụng cờ `subprocess.CREATE_NO_WINDOW` (có giá trị `0x08000000`) khi khởi chạy tiến trình trên Windows:

```python
import os
import subprocess
from typing import Any

# Khai báo kwargs an toàn đa nền tảng
kwargs: dict[str, Any] = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

# Truyền **kwargs vào toàn bộ các lệnh subprocess.run / Popen
proc = subprocess.run(
    [ADB, "-s", serial, "shell", "ip", "addr"],
    capture_output=True,
    text=True,
    timeout=10,
    **kwargs,
)
```

---

## 4. Cạm Bẫy Kiểu Dữ Liệu Type-Checking (Pyright / LSP Pitfall)

- **Vấn đề:** Nếu khai báo `kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW}` mà không chỉ định kiểu rõ ràng, bộ phân tích tĩnh (Pyright / Mypy) sẽ suy luận `kwargs` có kiểu `dict[str, int]`. Khi unpack `**kwargs` vào `subprocess.run()`, Pyright sẽ kiểm tra xem kiểu `int` có tương thích với toàn bộ các tham số khác của `subprocess.run` (như `executable: str | None`, `env: Mapping[str, str] | None`, `cwd: str | None`, `shell: bool`, v.v.) hay không, dẫn tới hàng loạt lỗi giả lập:
  - `No overloads for "run" match the provided arguments [reportCallIssue]`
  - `Argument of type "int" cannot be assigned to parameter "executable" [reportArgumentType]`
- **Cách khắc phục:** Khai báo kiểu tường minh với `dict[str, Any]`:
  ```python
  from typing import Any
  kwargs: dict[str, Any] = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
  ```
  Hoặc định nghĩa hằng số module-level:
  ```python
  WIN_KWARGS: dict[str, Any] = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
  ```

---

## 5. Danh Sách Script Đã Chuẩn Hóa
- `D:\Taadaa\automation-core\scripts\clear-tiktok-cache.py` (hàm `adb()`)
- `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_clear_tiktok_cache.py` (`get_connected_devices()`, `clear_device_cache()`)
- `C:\Users\Kibe\AppData\Local\hermes\scripts\farm_idle_screen_and_app_healer.py`
- `C:\Users\Kibe\AppData\Local\hermes\scripts\farm_wifi_auto_healer.py`
