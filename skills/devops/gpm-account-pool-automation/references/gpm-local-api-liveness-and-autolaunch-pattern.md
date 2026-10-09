# GPMLogin Local API Liveness & Auto-Launch / Graceful Skip Pattern

> 📌 **Bối cảnh thực tế (02/10/2026):**  
> Cron watchdog `gpm-gmail-nurture-watchdog` văng lỗi:  
> `Script exited with code 1 stdout: [ERROR] Lỗi kết nối GPM API: HTTPConnectionPool(host='127.0.0.1', port=19995): Max retries exceeded ... [WinError 10061]`  
> Do người dùng tắt app GPMLogin hoặc app chưa khởi động, script ném exception và `sys.exit(1)`, dẫn đến Hermes bắn cảnh báo thất bại mỗi chu kỳ.

---

## 1. Bản Chất Kỹ Thuật

1. **Vị trí GPMLogin.exe**:
   - Đường dẫn chuẩn: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\GPMLogin.exe`
   - Cổng API mặc định: `19995` (xác thực qua file `api_port.dat`).
2. **Bẫy Cron `no_agent: true`**:
   - Bất kỳ script nào kết thúc bằng `sys.exit(1)` hoặc ném unhandled exception đều khiến Hermes kích hoạt cơ chế báo động: `⚠️ Cron '<job_name>' failed: Script exited with code 1`.
   - Nếu người dùng chủ động tắt GPMLogin để tiết kiệm RAM/chơi game/dùng máy, việc watchdog bắn cảnh báo mỗi 5-60 phút là báo động rác (False Positive).

---

## 2. Chuẩn Thiết Kế Preflight Liveness & Auto-Launch

Mọi script watchdog / cron tương tác với GPM API v3 (`19995`) bắt buộc áp dụng mẫu Preflight Liveness sau:

```python
import os
import sys
import time
import requests
import subprocess
from pathlib import Path

GPM_API_BASE = "http://127.0.0.1:19995/api/v3"
GPM_EXE_PATH = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\GPMLogin.exe")

def is_gpm_api_live(timeout: float = 2.0) -> bool:
    """Kiểm tra nhanh GPM API port 19995 có phản hồi không."""
    try:
        res = requests.get(f"{GPM_API_BASE}/profiles?page=1&per_page=1", timeout=timeout)
        return res.status_code == 200
    except Exception:
        return False

def ensure_gpm_ready(auto_launch: bool = True, wait_seconds: int = 6) -> bool:
    """
    Đảm bảo GPM API sẵn sàng:
    1. Nếu đang live -> True ngay lập tức.
    2. Nếu offline và auto_launch=True -> Popen khởi động GPMLogin.exe và chờ API bind port.
    3. Nếu vẫn offline -> Log cảnh báo và trả về False.
    """
    if is_gpm_api_live():
        return True

    if auto_launch and GPM_EXE_PATH.exists():
        sys.stderr.write("[GPM_PREFLIGHT] GPM API offline, đang tự động khởi chạy GPMLogin.exe...\n")
        try:
            subprocess.Popen([str(GPM_EXE_PATH)])
            # Chờ app Electron tải xong và mở local HTTP server
            start_wait = time.time()
            while time.time() - start_wait < wait_seconds:
                time.sleep(1.5)
                if is_gpm_api_live():
                    sys.stderr.write("[GPM_PREFLIGHT] GPMLogin.exe đã online thành công!\n")
                    return True
        except Exception as e:
            sys.stderr.write(f"[GPM_PREFLIGHT] Lỗi khi launch GPMLogin.exe: {e}\n")

    return False
```

---

## 3. Quy Tắc Thoát Graceful Skip (Silent Watchdog)

Khi `ensure_gpm_ready()` trả về `False`:
- **ĐÂY LÀ LỖI NỀN TẢNG / MÔI TRƯỜNG TẠM NGHỈ (PLATFORM IDLE)**, KHÔNG PHẢI BUG SCRIPT.
- **CẤM** `sys.exit(1)` làm nổ alert cron.
- **BẮT BUỘC**:
  1. Ghi log cảnh báo ra file log và `sys.stderr`.
  2. Để `sys.stdout` hoàn toàn RỖNG.
  3. Kết thúc bằng `sys.exit(0)` (hoặc `return`) để Hermes im lặng chờ tick tiếp theo.

```python
def main():
    if not ensure_gpm_ready(auto_launch=True):
        # Ghi nhận vào log file/stderr để phục vụ audit thủ công
        logger.warning("GPM API không sẵn sàng (GPMLogin đang tắt). Tạm dừng đợt chạy an toàn.")
        # Silent watchdog: KHÔNG print gì ra stdout, exit 0
        sys.exit(0)

    # Tiếp tục logic lấy profiles và nuôi/login...
```
