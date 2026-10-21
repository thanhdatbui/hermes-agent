# Headless Python Watchdog Silent Import Crash Trap & Defensive Process Probing

## 1. Hiện tượng & Vấn đề thực tế

Trên hệ điều hành Windows, các dịch vụ chạy ngầm (Downloader, Renderer, Crawler, Watchdog) thường được thiết lập chạy tự động sau khi khởi động máy (Windows Task Scheduler hoặc Startup folder `shell:startup`) thông qua launcher VBScript ẩn:
```vbscript
Option Explicit
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """D:\Path\To\venv\Scripts\pythonw.exe"" ""C:\Users\Admin\watchdog.py""", 0, False
Set WshShell = Nothing
```

### Cái bẫy "Chết ngầm" (Silent Crash Trap):
1. **Thiếu thư viện trong venv mới:** Khi chuyển đổi đường dẫn Python từ Python hệ thống (system Python) sang một virtual environment (`venv`) mà quên kiểm tra xem `venv` đó đã cài đủ các thư viện của script hay chưa (ví dụ: `psutil`, `openpyxl`).
2. **`pythonw.exe` không cấp phát console buffer:** `pythonw.exe` là GUI subsystem executable, không có cửa sổ console và `sys.stdout` / `sys.stderr` mặc định là `None`.
3. **ModuleNotFoundError không để lại dấu vết:** Khi script chạy đến dòng `import psutil`, Python văng `ModuleNotFoundError: No module named 'psutil'` và kết thúc tiến trình ngay lập tức (<0.05s) với exit code 1.
4. **Task Scheduler báo giả tạo thành công:** `wscript.exe` gọi `WshShell.Run ..., 0, False` (không đợi tiến trình kết thúc) nên `wscript.exe` trả về exit code 0. Task Scheduler ghi nhận `LastTaskResult: 0` (Thành công).
5. **Hậu quả:** Sau ca reboot định kỳ (05:20, 11:20, 17:20), toàn bộ các tiến trình nền bị dừng vĩnh viễn mà không có 1 byte log lỗi nào được ghi ra đĩa, khiến các watchdog cấp cao hơn (reporting watchdog) báo "⚪ Đang dừng".

---

## 2. Nguyên tắc phòng thủ Watchdog (Zero-Hard-Dependency Pattern)

Một script Watchdog / Process Supervisor có nhiệm vụ sống bền bỉ 24/7 để giám sát và phục hồi tiến trình khác thì **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP CHẾT vì thiếu thư viện bên thứ ba**.

### Quy chuẩn code Watchdog phòng thủ đa tầng:

```python
import os
import sys
import subprocess

# 1. Bọc import phòng thủ: không bao giờ để lỗi import làm sập Watchdog
try:
    import psutil
except ImportError:
    psutil = None

def is_process_running(target_signatures: list[str]) -> bool:
    """Kiểm tra tiến trình đang chạy với cơ chế Fallback 2 tầng."""
    # Tầng 1: Sử dụng psutil nếu có (nhanh, chính xác)
    if psutil is not None:
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = " ".join(p.info.get('cmdline') or [])
                if any(sig.lower() in cmd.lower() for sig in target_signatures):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    # Tầng 2: Fallback sang Windows OS built-in (wmic / tasklist) không phụ thuộc thư viện
    try:
        out = subprocess.check_output(
            'wmic process where "name=\'python.exe\' or name=\'pythonw.exe\'" get commandline',
            shell=True,
            text=True,
            errors="replace",
            timeout=5
        )
        out_lower = out.lower()
        if any(sig.lower() in out_lower for sig in target_signatures):
            return True
    except Exception:
        pass

    return False
```

---

## 3. Checklist kiểm tra trước khi chuyển đổi môi trường Python

Khi chuyển đổi đường dẫn `python_exe` trong bất kỳ launcher nào (`.vbs`, `.ps1`, `.bat`, Task Scheduler):
1. **Kiểm tra môi trường đích trước khi đổi:**
   ```powershell
   & "D:\Path\To\venv\Scripts\python.exe" -c "import <tat_ca_cac_thu_vien_script_can>; print('OK')"
   ```
2. **Nếu thiếu module nhị phân:**
   - Cài đặt bù qua `pip install <module>`.
   - Hoặc chép trực tiếp package tương thích kiến trúc/phiên bản Python (`3.11.x 64-bit`) từ `site-packages` của môi trường đang có vào `venv/Lib/site-packages/`.
3. **Chạy thử trực tiếp script qua console python.exe trước khi chuyển sang pythonw.exe:**
   ```powershell
   & "D:\Path\To\venv\Scripts\python.exe" "C:\Users\Admin\watchdog.py"
   ```
   Xác nhận `LASTEXITCODE -eq 0` và không có bất kỳ traceback hay `ModuleNotFoundError` nào trên stderr.
