# Phòng Chống Bão Cửa Sổ Console (Console Window Storm) Trên Windows Khi Chạy Script Nền / ADB

Tài liệu quy định và hướng dẫn kỹ thuật phòng ngừa triệt để lỗi "bão cửa sổ nhấp nháy" (Console Window Storm) khi chạy automation và watchdog trên Windows.

---

## 1. Hiện Tượng Thực Tế (Symptoms)

- Màn hình desktop của user xuất hiện hiện tượng **nhấp nháy / chớp tắt liên hồi** các cửa sổ đen nhỏ bật lên rồi tắt ngay trong tích tắc (vài chục đến hàng trăm ms).
- Người dùng hoang mang ("Clgt nó đang nháy nháy liên tục", nghi ngờ virus hoặc màn hình hỏng).
- Hiện tượng bùng phát khi các cronjob/watchdog chạy nền kích hoạt (ví dụ: dọn dẹp cache ban đêm `clear-tiktok-cache`, watchdog toggle Wi-Fi `farm_wifi_auto_healer`, kiểm tra trạng thái màn hình máy idle `farm_idle_screen_and_app_healer`).

---

## 2. Cơ Chế Gây Lỗi Kỹ Thuật (Root Cause Mechanics)

1. **Win32 CreateProcess Console Allocation:**
   - Các tiến trình nền (background service, Hermes Gateway daemon, hoặc script chạy bằng `pythonw.exe`) hoạt động trong trạng thái **GUI subsystem / detached process** (không có Console đính kèm).
   - Khi một tiến trình GUI/detached gọi `subprocess.run()` hoặc `subprocess.Popen()` để thực thi một file thực thi dạng **Console Subsystem** (như `adb.exe`, `python.exe`, `git.exe`):
   - Mặc định, Windows API `CreateProcessW` sẽ **tự động cấp phát một cửa sổ Console mới** cho tiến trình con đó.
   - Khi lệnh con hoàn thành (ví dụ `adb shell input keyevent ...` chỉ mất vài chục ms), cửa sổ Console này lập tức đóng lại.

2. **Cộng hưởng đa luồng (Multi-threading Concurrency Storm):**
   - Khi script chạy song song `ThreadPoolExecutor(max_workers=20..30)` quét qua 70–80 thiết bị S7 đồng thời, hàng chục cửa sổ `adb.exe` liên tục được Windows tạo ra và hủy đi trên màn hình trong cùng một giây.
   - Điều này tạo nên hiện tượng chớp giật thị giác dữ dội (Console Storm), làm gián đoạn trải nghiệm của người dùng trên PC.

---

## 3. Giải Pháp Bắt Buộc (Mandatory Invariant Solution)

### A. Đối với `subprocess.run` trong các script chạy nền:
Luôn truyền cờ `creationflags=subprocess.CREATE_NO_WINDOW` (hằng số `0x08000000` của Win32 API).

**Cách 1: Khai báo helper wrapper (Khuyên dùng cho toàn bộ file)**
```python
import os
import subprocess

def subp_run(*args, **kwargs):
    """Wrapper subprocess.run tự động ẩn console window trên Windows."""
    if os.name == "nt" and "creationflags" not in kwargs:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(*args, **kwargs)
```
Thay thế toàn bộ `subprocess.run(...)` trong file thành `subp_run(...)`.

**Cách 2: Khai báo kwargs chuẩn**
```python
WIN_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

# Truyền vào subprocess:
res = subprocess.run([ADB, "-s", serial, "shell", "dumpsys", "window"], capture_output=True, text=True, timeout=5, **WIN_KWARGS)
```

### B. Đối với `subprocess.Popen` (spawn tiến trình con độc lập):
```python
kwargs = {
    "stdin": subprocess.DEVNULL,
    "stdout": subprocess.DEVNULL,
    "stderr": subprocess.DEVNULL,
}
if sys.platform == "win32":
    # 0x08000200 = CREATE_NEW_PROCESS_GROUP (0x200) | CREATE_NO_WINDOW (0x08000000)
    kwargs["creationflags"] = 0x08000200
else:
    kwargs["start_new_session"] = True

proc = subprocess.Popen(argv, **kwargs)
```

---

## 4. Danh Sách Các File Trọng Yếu Đã Chuẩn Hóa

- `D:/Taadaa/automation-core/src/automation_core/adb.py` (`_subprocess_window_kwargs()`)
- `D:/Taadaa/automation-core/scripts/clear-tiktok-cache.py` (`adb()` helper)
- `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_clear_tiktok_cache.py` (`WIN_KWARGS` trên toàn bộ ADB calls)
- `C:/Users/Kibe/AppData/Local/hermes/scripts/farm_idle_screen_and_app_healer.py` (`subp_run()`)
- `C:/Users/Kibe/AppData/Local/hermes/scripts/farm_wifi_auto_healer.py` (`subp_run()`)
- `C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py` (`creationflags = 0x08000200`)

---

## 5. Invariant Checklist Khi Viết Script Mới

- [ ] CẤM gọi `subprocess.run([ADB_EXE, ...])` trần mà không có cờ `creationflags=subprocess.CREATE_NO_WINDOW` trên Windows.
- [ ] Không giả định rằng script chạy bằng `pythonw.exe` thì các tiến trình con do nó sinh ra sẽ tự động không có cửa sổ. Tiến trình con Console **BẮT BUỘC** phải có cờ `CREATE_NO_WINDOW`.
- [ ] Khi debug đa luồng trên farm, luôn kiểm tra xem màn hình desktop có bị nháy hay không trước khi đưa script vào cronjob định kỳ.
