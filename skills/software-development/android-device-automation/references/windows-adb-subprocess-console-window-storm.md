# Windows ADB Subprocess Console Window Storm & CreationFlags Invariant

## 1. Triệu chứng & Hiện trường
- Người dùng thấy hàng loạt cửa sổ Command Prompt (màu đen) nhảy chớp giật liên hồi trên màn hình desktop, tiêu đề cửa sổ mang tên đường dẫn file thực thi:
  `C:\Program Files (x86)\xiaowei\tools\adb.exe` (hoặc `adb.exe`, `python.exe`).
- Hiện tượng xuất hiện theo đợt khi có cronjob chạy nền kích hoạt (ví dụ: `cron_clear_tiktok_cache.py`, `farm_idle_screen_and_app_healer.py`, `farm_wifi_auto_healer.py`).
- Cửa sổ bật lên và biến mất trong tích tắc (<0.5s), nhưng do chạy đa luồng (`max_workers=20` đến `30`), hàng chục cửa sổ xuất hiện đồng thời theo tầng (cascade), gây chớp giật thị giác nghiêm trọng và giật lag desktop.

## 2. Nguyên nhân kỹ thuật (Root Cause)
1. **Subsystem Mismatch trên Windows**:
   - Khi tiến trình chạy nền là GUI subsystem (`pythonw.exe` từ Hermes Gateway, cron daemon hoặc task scheduler), tiến trình cha không có sẵn một console window gắn kèm.
   - Nếu script cha gọi `subprocess.run()` hoặc `subprocess.Popen()` để thực thi một file thực thi console subsystem (`adb.exe`, `python.exe`, `curl.exe`...) mà **KHÔNG truyền cờ `creationflags`**, hệ điều hành Windows mặc định sẽ tạo một console window mới cho mỗi subprocess.
2. **Khuếch đại do Batch & Đa luồng**:
   - Một lệnh ADB đơn lẻ chỉ chớp 1 lần có thể không kịp để ý. Nhưng khi batch job chạy 20-30 workers song song qua 70-80 máy, mỗi máy chạy chuỗi 5-10 lệnh (`input keyevent KEYCODE_WAKEUP`, `am force-stop`, `settings get/put`, `dumpsys window`), tốc độ mở/đóng cửa sổ đạt 30-50 cửa sổ/giây, tạo ra một cơn bão cửa sổ (console storm).

## 3. Invariant & Chuẩn hóa Code

### A. Chuẩn hóa trong `automation_core.adb`
Module `automation_core.adb` đã có hàm chuẩn:
```python
def _subprocess_window_kwargs() -> dict[str, Any]:
    """Prevent console-window storms when ADB is launched from pythonw.exe."""
    if os.name != "nt":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}
```
Mọi consumer dùng `AdbClient` của `automation_core` đều tự động được bảo vệ.

### B. Chuẩn hóa cho Standalone Script / Cron / Watchdog
BẤT KỲ script Python nào trực tiếp gọi `subprocess.run` hoặc `Popen` tới `adb` trên Windows BẮT BUỘC phải áp dụng một trong hai mẫu sau:

#### Mẫu 1: Helper Wrapper (Khuyến nghị cho file có nhiều lệnh gọi)
```python
import os
import subprocess

def subp_run(*args, **kwargs):
    if os.name == "nt" and "creationflags" not in kwargs:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(*args, **kwargs)
```
Thay thế toàn bộ `subprocess.run(...)` trong file bằng `subp_run(...)`.

#### Mẫu 2: Biến cờ dùng chung
```python
import os
import subprocess

WIN_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

# Truyền **WIN_KWARGS vào mọi subprocess.run / Popen
subprocess.run([ADB, "-s", serial, "shell", ...], capture_output=True, timeout=10, **WIN_KWARGS)
```

## 4. Quy tắc điều phối Worker (Coordinator Dispatch Lesson)
- Khi phát hiện lỗi thiếu `CREATE_NO_WINDOW` trên nhiều script khác nhau:
  - **CẤM gộp 4+ files vào 1 Worker subagent**: Worker sẽ bị cạn budget iterations hoặc dính timeout (600s).
  - **BẮT BUỘC phân rã 1–2 files / worker**: Cung cấp Patch Contract đóng với `old_string` -> `new_string` chính xác tuyệt đối và lệnh test `python -m py_compile <path>`.
