# Case 189: OpenBLAS Memory Allocation Failure Trên Host 56 Cores & Phòng Vệ 3 Lớp Cho Watchdog (24/09/2026)

## Hiện Tượng & Triệu Chứng
Vào lúc 06:36:50 sáng ngày 24/09/2026, cron job `tiktok-feed-session-watchdog` (Job ID: `1d62cb3562e0`) bị crash và trả về cảnh báo Telegram:
```text
⚠️ Cron 'tiktok-feed-session-watchdog' failed: Script exited with code 1
stderr:
OpenBLAS error: Memory allocation still failed after 10 retries, giving up.
OpenBLAS error: Memory allocation still failed after 10 retries, giving up.
...
```
Hoàn toàn không có Python traceback. Tiến trình Python bị dừng đột ngột với exit code 1.

## Nguyên Nhân Gốc Rễ (Root Cause)
1. **Cấu hình máy chủ**: Host chạy Windows 10 với Dual Intel Xeon CPU gồm **56 logical processors** (`cpu_count = 56`).
2. **Kích hoạt ngầm**: `feed_session_watchdog.py` không import trực tiếp `numpy`, nhưng import `openpyxl` để đọc file mapping an toàn `taikhoan_run_safe.xlsx`. Khi môi trường venv có cài `numpy` (hoặc `openpyxl` quét optional dependencies), DLL C-extension OpenBLAS (`libscipy_openblas64_-...dll`) tự động được nạp vào memory.
3. **Mặc định luồng**: Khi biến môi trường `OPENBLAS_NUM_THREADS` chưa được khai báo, OpenBLAS tự động khởi tạo thread pool với số luồng tương ứng `cpu_count` (56 luồng).
4. **Phân mảnh bộ nhớ / Tải farm**: OpenBLAS dùng `VirtualAlloc` để cấp phát bộ nhớ ảo liên tục cho mỗi luồng. Vào các khung giờ cao điểm khi 80 máy chạy feed session cùng hàng chục cronjobs và process ngầm, commit charge cao khiến `VirtualAlloc` thất bại. Sau 10 lần retry nội bộ, OpenBLAS in thông báo ra stderr và gọi thẳng `exit(1)` ở tầng C, bypass toàn bộ `try/except` của Python.

## Giải Pháp Phòng Vệ 3 Lớp (3-Tier Defense)

### 1. Lớp 1 (Script Level)
Khai báo giới hạn luồng OpenBLAS, MKL, OMP, NUMEXPR ngay dòng đầu tiên của `feed_session_watchdog.py`, trước bất kỳ lệnh `import` nào khác:
```python
import os
# Prevent OpenBLAS/MKL memory allocation failure on high-core hosts (56 cores)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import subprocess
...
```
*Lưu ý quan trọng*: Bắt buộc phải đặt trước khi import `openpyxl`, `pandas` hoặc `numpy`. Nếu đặt sau import, DLL đã nạp và thread pool đã được cấp phát nên việc set biến môi trường sẽ vô tác dụng.

### 2. Lớp 2 (Cron Scheduler Level)
Trong Hermes scheduler (`D:/Taadaa/Hermes/cron/scheduler.py`), hàm `_run_job_script`:
Tự động tiêm các biến môi trường giới hạn luồng vào `cron_env` của subprocess:
```python
popen_kwargs = {"creationflags": windows_hide_flags()} if sys.platform == "win32" else {}
cron_env = _sanitize_subprocess_env(os.environ.copy())
# Default thread caps to prevent OpenBLAS/MKL memory allocation failures on high-core hosts
cron_env.setdefault("OPENBLAS_NUM_THREADS", "1")
cron_env.setdefault("MKL_NUM_THREADS", "1")
cron_env.setdefault("OMP_NUM_THREADS", "1")
cron_env.setdefault("NUMEXPR_NUM_THREADS", "1")
result = subprocess.run(
    argv,
    capture_output=True,
    text=True,
    timeout=script_timeout,
    cwd=str(path.parent),
    env=cron_env,
    **popen_kwargs,
)
```
Điều này đảm bảo toàn bộ 33 cronjob trên host (kể cả các watchdog khác) đều được bảo vệ tự động mà không cần vá từng file riêng lẻ.

### 3. Lớp 3 (Host OS User Level)
Thiết lập biến môi trường cấp User vĩnh viễn trên Windows qua PowerShell:
```powershell
[System.Environment]::SetEnvironmentVariable('OPENBLAS_NUM_THREADS', '1', 'User')
```
Mọi terminal, Task Scheduler hoặc process con sinh ra từ tài khoản User đều thừa hưởng `OPENBLAS_NUM_THREADS=1`.

## Quy Trình Đồng Bộ & Kiểm Chứng
1. Sửa file runtime: `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
2. Đồng bộ sang Git deploy: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
3. Đồng bộ sang OneDrive shared sync: `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/feed_session_watchdog.py`
4. Kiểm tra cú pháp:
   ```bash
   python -m py_compile C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py
   python -m py_compile D:/Taadaa/Hermes/cron/scheduler.py
   ```
5. Kiểm tra thực thi:
   ```bash
   python -c "import os; from feed_session_watchdog import is_pid_alive; print('OPENBLAS_NUM_THREADS:', os.environ.get('OPENBLAS_NUM_THREADS'))"
   ```
