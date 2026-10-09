# ADB Console Window Storms on Windows & Headless Subprocess Invariants

## Hiện Tượng (Symptoms)
- Màn hình người dùng bị chớp/nháy liên tục ("Clgt nó đang nháy nháy liên tục").
- Hàng loạt cửa sổ Command Prompt / Console viền đen xuất hiện rồi biến mất ngay lập tức trong tích tắc (title bar thường hiện `C:\Program Files (x86)\xiaowei\tools\adb.exe` hoặc `adb.exe`).
- Hiện tượng xảy ra dồn dập khi farm bắt đầu một đợt cronjob dọn dẹp, heal máy, hoặc quét batch thiết bị song song (như `clear-tiktok-cache`, `idle_screen_healer`).

---

## Cơ Chế Gây Lỗi (Root Cause Mechanics)

1. **Windows Subsystem & Console Allocation:**
   - `adb.exe` là một binary thuộc subsystem Console (`IMAGE_SUBSYSTEM_WINDOWS_CUI`).
   - Khi được gọi từ một tiến trình GUI / không có console (như `pythonw.exe`, Hermes Gateway background runner, hoặc Windows Service) qua Python `subprocess.run(...)` hay `subprocess.Popen(...)`, Windows nhận thấy tiến trình cha không có console attached. Do đó, hệ điều hành tự động cấp phát (allocate) một console window mới cho tiến trình con `adb.exe`.
   - Ngay khi lệnh hoàn thành (thường chỉ 50ms - 300ms), console window đó tự đóng lại.

2. **Cạm bẫy ngộ nhận về `pythonw.exe`:**
   - Nhiều lập trình viên lầm tưởng chạy script bằng `pythonw.exe` thì mọi lệnh con sinh ra sẽ tự động tàng hình.
   - **Thực tế:** `pythonw.exe` chỉ ẩn cửa sổ của chính trình thông dịch Python. Mọi child process dạng console subsystem (như `adb.exe`, `curl.exe`, `ffmpeg.exe`) được spawn bên trong vẫn sẽ bung cửa sổ riêng nếu không có cờ triệt tiêu.

3. **Console Window Storm trong Batch Concurrency:**
   - Khi một cronjob chạy với `MAX_WORKERS = 20` hoặc `30` quét qua 70-80 máy, mỗi máy gọi liên tiếp `dumpsys`, `am force-stop`, `input keyevent`, `settings put`...
   - Hệ thống phát sinh hàng trăm tiến trình `adb.exe` mỗi phút. Hàng trăm cửa sổ console bung lên - dập xuống liên hồi tạo thành "bão cửa sổ" (Console Window Storm), gây giật lag và làm người dùng khó chịu khi đang làm việc trên máy tính.

---

## Quy Trình Chẩn Đoán O(1) (Fast Triage Checklist)

Khi user báo "màn hình đang nháy liên tục" hoặc chụp ảnh thấy title bar `adb.exe`:

### Bước 1: Quét nhanh cây tiến trình liên quan
Chạy one-liner PowerShell để truy tìm cha-con:
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'adb|python' } | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-Table -AutoSize
```

### Bước 2: Lần ngược `ParentProcessId` để bắt thủ phạm
- Nếu `ParentProcessId` của `adb.exe` trỏ về `pythonw.exe` (ví dụ `clear-tiktok-cache.py`).
- Tiếp tục tìm `ParentProcessId` của `pythonw.exe` đó (ví dụ `cron_clear_tiktok_cache.py` hoặc `farm_idle_screen_and_app_healer.py` do Hermes Gateway điều phối).
- Kiểm tra mã nguồn của script nghi vấn xem có đang gọi `subprocess.run([ADB, ...])` trần trụi hay không.

---

## Giải Pháp & Quy Tắc Chuẩn Hóa (Standard Pattern)

### 1. Chuẩn hóa `_subprocess_window_kwargs`
Toàn bộ các lời gọi `subprocess` tới console binary trên Windows BẮT BUỘC phải kèm cờ `CREATE_NO_WINDOW`:

```python
import os
import subprocess
from typing import Any

def _subprocess_window_kwargs() -> dict[str, Any]:
    """Prevent console-window storms when console binaries are launched on Windows."""
    if os.name != "nt":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}
```

### 2. Áp dụng vào `subprocess.run` & `Popen`
```python
# Cách 1: Dùng helper kwargs
subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **_subprocess_window_kwargs())

# Cách 2: Inline trực tiếp nếu script đơn lẻ
kwargs = {}
if os.name == "nt":
    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kwargs)
```

### 3. Ưu tiên AdbClient chuẩn trong `automation_core.adb`
Thay vì tự viết hàm `adb(serial, args)` cục bộ bằng `subprocess.run`, hãy import `AdbClient` từ `automation_core.adb` — module này đã được bọc sẵn `_run_bounded` với `CREATE_NO_WINDOW` và timeout termination chuẩn Windows.
