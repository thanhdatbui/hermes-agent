# OpenBLAS Thread Cap & High-Core VirtualAlloc Failure Protection (2026-09-24)

## 1. Hiện tượng & Cơ chế Lỗi (Root Cause)

### Hiện tượng
Cronjob (như `tiktok-feed-session-watchdog` hoặc các cron script no_agent khác) bị sập đột ngột với exit code 1:
```text
OpenBLAS error: Memory allocation still failed after 10 retries, giving up.
```
Tiến trình Python bị terminate ngay lập tức ở tầng C-code mà KHÔNG in ra bất kỳ Python traceback nào.

### Nguyên nhân
- Máy chủ chạy CPU nhiều nhân (Dual Xeon, 56 logical processors, `os.cpu_count() == 56`).
- Script Python gián tiếp nạp C-extension OpenBLAS (`libscipy_openblas64*.dll`) qua các thư viện phổ biến:
  - `openpyxl` (tự động thăm dò numpy để hỗ trợ array formatting).
  - `numpy`, `scipy`, `pandas`, `opencv-python` (`cv2`), `torch`.
- Khi biến môi trường `OPENBLAS_NUM_THREADS` không được chỉ định:
  - OpenBLAS mặc định tạo và cấp phát buffer bộ nhớ ảo liên tục cho toàn bộ **56 threads**.
  - Khi hệ thống đang chạy tải cao (80 máy farm lướt feed + nhiều tiến trình đồng thời), bộ nhớ ảo/commit charge bị phân mảnh, lệnh `VirtualAlloc` của OpenBLAS thất bại sau 10 lần retry.
  - OpenBLAS gọi trực tiếp `exit(1)` trong mã nguồn C, làm crash tiến trình.

---

## 2. Kiến trúc Phòng vệ 3 Lớp Bắt buộc (3-Layer Defense)

### Lớp 1: Script Header Injection (Đầu mỗi script runtime & deploy)
Phải đặt biến môi trường giới hạn thread ngay dòng đầu tiên của script Python, **TRƯỚC MỌI LỆNH IMPORT THƯ VIỆN BÊN NGOÀI**:
```python
import os
# Prevent OpenBLAS/MKL memory allocation failure on high-core hosts (56 cores)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import subprocess
import openpyxl
...
```

### Lớp 2: Hermes Cron Scheduler Subprocess Guard
Trong `cron/scheduler.py` (hàm `_run_job_script`):
Mọi script chạy dưới chế độ `no_agent: true` đều phải được tiêm sẵn các biến môi trường giới hạn thread vào `cron_env` trước khi gọi `subprocess.run`:
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

### Lớp 3: Windows User Environment Variable
Cấu hình biến môi trường cố định ở tầng Windows User để mọi tiến trình Python mới sinh ra trên host đều kế thừa:
```powershell
powershell -Command "[System.Environment]::SetEnvironmentVariable('OPENBLAS_NUM_THREADS', '1', 'User')"
```
Kiểm tra lại:
```powershell
powershell -Command "[System.Environment]::GetEnvironmentVariable('OPENBLAS_NUM_THREADS', 'User')"
# Kết quả phải trả về 1
```
