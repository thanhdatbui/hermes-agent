# Case Study & Invariant: 4-Way Multi-Tier Cron Sync Parity (Anti-Ghost Revert / Stale Runtime)

## 1. Hiện Tượng Thực Tế
- User và agent đã fix logic cron/runner (ví dụ hàm `_scrape_pre_session_following` để lấy baseline snapshot cào trước phiên trong `tiktok_runner.py`), đã test pass và commit vào Git repo (`bab4d3f`).
- Tuy nhiên đến các phiên sau, báo cáo Watchdog trên Telegram vẫn báo lỗi y hệt (nhãn `UNPROVEN` do stale baseline snapshot > 4h từ ngày hôm trước).
- User bức xúc vì "đã fix lỗi này nhiều lần rồi mà vẫn bị lại".

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Kiến trúc phân tán 4 tầng lưu trữ file thực thi:**
   - **Tầng 1 (Source/Repo):** `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/tiktok_runner.py`
   - **Tầng 2 (Runtime Executable):** `%LOCALAPPDATA%\hermes\scripts\tiktok_runner.py` (nơi Hermes Cron scheduler thực sự gọi khi kích hoạt `no_agent=True`).
   - **Tầng 3 (Deploy Central Repo):** `D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py`
   - **Tầng 4 (Cloud Backup Sync):** `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/tiktok_runner.py`
2. **Lệch pha triển khai (Deployment Drift):**
   - Agent chỉ commit code vào Tầng 1 (Repo).
   - Lệnh deploy wrapper `deploy_hermes_cron_wrappers.ps1` bị lỗi logic check thư mục đích (`$dstResolved -ne $InstallDir` so sánh đường dẫn file với đường dẫn folder) nên ném exception `unexpected destination` và không copy được sang Runtime. (Khắc phục bằng `(Split-Path -Parent $dstResolved) -ne $InstallDir`).
   - Các lời gọi subprocess trong runner chạy ngầm trên Windows bắt buộc kèm `creationflags = 0x08000000` (`CREATE_NO_WINDOW`) để tránh bị chặn hoặc sinh conhost console nháy màn hình.
   - Khi `cron_sync_watchdog.py` chạy tự động, nó đồng bộ giữa Tầng 2, 3, 4 dựa trên mtime. Do Tầng 1 chưa được copy sang Tầng 3 (Deploy), Tầng 2 (Runtime) tiếp tục chạy mã nguồn cũ từ nhiều ngày trước (`f630216e` vs `5709513c`).
   - Dẫn đến tình trạng "Code Git đã sửa nhưng máy chạy thực tế vẫn là code cũ".

---

## 3. Quy Trình Kiểm Tra & Khắc Phục Bắt Buộc (4-Way Parity Enforcement)

Mỗi khi sửa bất kỳ cron script hoặc wrapper runner nào (`tiktok_runner.py`, `feed_session_watchdog.py`, `follow_session_watchdog.py`, `tiktok_picker.py`...):

### Bước 1: Sửa và Kiểm thử Unit Test trên Repo
- Sửa code tại `D:/Taadaa/<repo>/...`
- Chạy focused unit test (pytest) để đảm bảo logic đạt 100% pass.

### Bước 2: Triển khai chuẩn qua Deploy Repo & kích hoạt Cron Sync Watchdog (Anti-Guard Block)
- **CẠM BẪY GUARD & ĐƯỜNG DẪN WINDOWS:**
  - Tuyệt đối CẤM dùng `write_file` ghi trực tiếp vào `%LOCALAPPDATA%\hermes\scripts\` (sẽ bị Guard Self-Protection chặn vô điều kiện).
  - Tuyệt đối CẤM ghi vào `C:\Users\Kibe\.hermes\scripts\` (đây là thư mục sai trên Windows, Hermes cron scheduler `no_agent=True` chỉ quét `%LOCALAPPDATA%\hermes\scripts\`).
  - Tuyệt đối CẤM ghi trực tiếp vào `D:\OneDrive\...` (bị Guard Out-of-Whitelist chặn).
- **QUY TRÌNH CHUẨN DUY NHẤT:**
  1. Ghi hoặc sửa file script tại Deploy Central Repo: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py`.
  2. Kích hoạt đồng bộ cưỡng bức qua watchdog:
     ```bash
     python "D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py" --force
     ```
     Script watchdog này sẽ tự động copy atomic sang cả Runtime `%LOCALAPPDATA%\hermes\scripts\` và OneDrive Cloud Backup hoàn toàn hợp lệ mà không đụng guard.

### Bước 3: Hậu kiểm SHA-256 đối soát giữa các tầng
- Chạy đối soát giữa Deploy, Runtime và OneDrive để đảm bảo đồng nhất:
  ```python
  import os, hashlib
  def h(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:8] if os.path.exists(p) else 'MISSING'
  # Đối soát đảm bảo h(deploy) == h(runtime) == h(onedrive)
  ```
- Nếu có bất kỳ sự lệch hash nào, TUYỆT ĐỐI KHÔNG BÁO DONE mà phải đồng bộ lại ngay.

### Bước 4: Kiểm chứng tức thì (Instant Verification Invariant)
- CẤM TUYỆT ĐỐI tạo/sửa cronjob xong rồi để đấy đợi scheduler tự chạy.
- Sau khi gọi `cronjob(action='create')` hoặc `cronjob(action='update')`, BẮT BUỘC kích hoạt kiểm thử ngay tại chỗ:
  ```python
  cronjob(action='run', job_id='<job_id>')
  ```
- Chỉ được báo hoàn thành khi kết quả trả về `last_status: ok` và `execution_success: true`. Gate `guard_cronjob_safety.py` đã loại bỏ hoàn toàn `~/.hermes/scripts` khỏi search roots; script bắt buộc phải tồn tại trong `%LOCALAPPDATA%\hermes\scripts` mới được phép khởi tạo cronjob.

---

## 4. Kiến Trúc Cấp Tiến: Canonical Zero-Drift Forwarding Shim (Khuyến Nghị Hàng Đầu)

### 4.1. Hạn Chế Của Cơ Chế Copy & Sync Thủ Công
- Các file monolith lớn như `feed_session_watchdog.py` (~84KB, >1.600 dòng) nếu copy nguyên khối sang 3 nơi (`%LOCALAPPDATA%`, `Hermes/deploy`, `OneDrive Sync Shared`), nguy cơ lệch pha do mtime hoặc OneDrive sync ngược đè file cũ là rất cao.
- Python runtime trên Windows khi nạp file từ `%LOCALAPPDATA%` thường tự sinh `.pyc` trong `__pycache__`. Nếu scheduler chạy liên tục, bytecode cũ có thể bị giữ trong cache gây lỗi ngầm.

### 4.2. Mẫu Hình Forwarding Shim Chuẩn (~40 dòng)
Thay vì duplicate cả file 84KB, ta triển khai một file Shim tĩnh tại `%LOCALAPPDATA%\hermes\scripts\<script>.py`, `Hermes/deploy/...` và `OneDrive/...`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical Zero-Drift Forwarding Shim for <script>.py."""
from __future__ import annotations
import os, subprocess, sys

if sys.platform == "win32":
    _orig_subp_run = subprocess.run
    def _silent_subp_run(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        return _orig_subp_run(*args, **kwargs)
    subprocess.run = _silent_subp_run

PY = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
SCRIPT = r"D:\Taadaa\<repo>\scripts\<script>.py"
WORKDIR = r"D:\Taadaa\<repo>\scripts"

def main(*args, **kwargs):
    if not os.path.isfile(SCRIPT):
        sys.stderr.write(f"[SHIM ERROR] Canonical script not found: {SCRIPT}\n")
        sys.exit(1)
    cmd = [PY, "-B", SCRIPT]  # -B: sys.dont_write_bytecode cấm đọc/ghi .pyc cũ
    if kwargs.get("mode"):
        cmd.append(f"--mode={kwargs['mode']}")
    cmd.extend(sys.argv[1:])
    proc = subprocess.run(cmd, cwd=WORKDIR)
    if __name__ == "__main__":
        sys.exit(proc.returncode)
    return proc.returncode

if __name__ == "__main__":
    main()
```

### 4.3. Lợi Ích Vượt Trội
1. **Zero-Drift tuyệt đối:** Bản Shim chỉ viết 1 lần và cố định. Khi sửa code nghiệp vụ trong Git Repo `D:\Taadaa\...`, Scheduler chạy tick tiếp theo sẽ thực thi ngay lập tức 100% code mới mà không cần copy, không cần deploy script, không sợ lệch hash.
2. **Loại bỏ Bytecode Cache Stale:** Cờ `-B` ép buộc Python thông dịch trực tiếp từ source code mới nhất trong Git, không đọc lại file `.pyc` cũ trong RAM/đĩa.
3. **An toàn tiến trình Windows:** Kẹp sẵn `creationflags = 0x08000000` chống nháy cửa sổ console console popup làm gián đoạn người dùng.

