# Register Gmail Runner Startup Preflight Triage Runbook (2026-09-24)

## 1. Hiện tượng & Nhận diện Lỗi "LỖI KHỞI ĐỘNG RUNNER"
- **Triệu chứng Telegram Alert**:
  ```text
  - Phase 1 (Reg Gmail - Code 1): LỖI KHỞI ĐỘNG RUNNER
    + Tổng máy: 0
    + Success (0)
    + Fail (0)
  ```
- **Dấu hiệu định vị hiện trường O(1)**:
  - Kiểm tra `D:\CodexRuntime\codex_gmail_debug-register-gmail\`:
    + Hoàn toàn **KHÔNG có thư mục `logs_parallel_<timestamp>`**.
    + Hoàn toàn **KHÔNG có file `lock_scope_audit_<run_id>.json`**.
  - **Kết luận**: Runner bị văng trong giai đoạn Preflight PowerShell/Python, trước khi chạm tới bước Reservation Device Locks (trước dòng 544 của `run_parallel.ps1`).

---

## 2. Bốn Trạm Gác Preflight (4 Preflight Gates) & Điểm Gãy Thường Gặp

Khi `run_all.ps1` gọi `run_parallel.ps1`, luồng đi qua 4 trạm kiểm soát bắt buộc:

### Trạm 1: `g.load_device_map_from_excel()` (Dòng 76 `run_all.ps1` & Dòng 375/395 `run_parallel.ps1`)
- **Nguồn workbook**: `PROXY_DIENTHOAI_PATH` hoặc `GMAIL_DEVICE_MAP_WORKBOOK`.
- **Pitfall 1 (Cross-Farm Workbook Ambiguity)**:
  `run_all.ps1` có đoạn fallback cũ:
  ```powershell
  if (-not $env:PROXY_DIENTHOAI_PATH -and -not $env:GMAIL_DEVICE_MAP_WORKBOOK) {
      if (Test-Path "D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx") {
          $env:PROXY_DIENTHOAI_PATH = "D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx"
      }
  }
  ```
  Nếu máy Kibe bị mất biến `GMAIL_DEVICE_MAP_WORKBOOK`, script sẽ nhận diện file của `admin` (chứa máy 201-280) thay vì `kibe` (máy 1-80). Sau đó sang Trạm 4 sẽ văng ngay vì `machine:201` không có trong `AssignmentManifest`.
- **Pitfall 2 (Conflicting Serials)**:
  Nếu `taikhoan_run_safe.xlsx` có 1 máy chứa 2 serial khác nhau trên các dòng (hoặc bị dán nhầm chuỗi ngày giờ vào cột Device ID), `load_device_map_from_excel()` sẽ raise:
  `RuntimeError: Device map has conflicting valid serials for machine(s): X`.

### Trạm 2: Cooldown Ready Machines (`g.get_machines_ready()`) (Dòng 470 `run_parallel.ps1`)
- **Nguồn workbook**: `GMAIL_EXCEL_FILE` (mặc định `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`).
- Đọc ngày tạo từ Cột 7: Xử lý cả `datetime`, `date`, và Excel serial integer (ví dụ `46272` tương ứng tháng 09/2026).
- **Pitfall PowerShell Syntax Trap**:
  Trong `run_parallel.ps1`:
  ```powershell
  $pythonCode = @"
  import sys
  try:
      import gmail_reg_v10 as g
      result = g.get_machines_ready($cooldownDays, quiet=True)
      print(','.join(map(str, result)))
  except Exception as e:
      print(f'ERROR: {e}', file=sys.stderr)
      sys.exit(1)
  "@
  ```
  Trong double-quoted here-string (`@" ... "@`), PowerShell tự động mở rộng biến `$e` thành chuỗi rỗng `""`. Khi có lỗi, Python chạy lệnh `print(f'ERROR: {}')` sẽ quăng `SyntaxError: f-string: empty expression not allowed`, làm biến dạng thông báo lỗi gốc.

### Trạm 3: Môi trường Phân bổ (`AssignmentManifest & Worker ID`) (Dòng 523 `run_parallel.ps1`)
- Bắt buộc phải có:
  - `$env:GMAIL_ASSIGNMENT_MANIFEST` trỏ tới `C:\Users\Kibe\AppData\Local\automation-core\assignments\register-gmail.json`.
  - `$env:GMAIL_WORKER_ID` khớp với `owner_id` trong file json (`taadaa-writer-3c47f89f35e44795a79267e09fbcc72d`).
- Nếu chạy từ subagent/cron mà quên export 2 biến này vào process `env`, PowerShell throw ngay:
  `Set GMAIL_ASSIGNMENT_MANIFEST and GMAIL_WORKER_ID before selecting targets.`

### Trạm 4: Thẩm định Danh sách Máy Phân bổ (`assert_assigned`) (Dòng 535 `run_parallel.ps1`)
- Kiểm tra toàn bộ máy trong `$machineList` xem có thuộc trường `resources` của manifest không.
- Nếu lọt máy không thuộc phân bổ (hoặc dính dải máy admin 201-280), script throw:
  `Machine assignment preflight failed: machine:X not assigned`.

---

## 3. Khắc phục Lỗ hổng Nuốt Log trong Watchdog (`post_noon_chain_watchdog.py`)
- **Nguyên nhân mất log**: Trong `post_noon_chain_watchdog.py`, `run_gmail_batch()` thu thập `proc.stdout + "\n" + proc.stderr` vào `g_out`. Tuy nhiên khi `g_code != 0 and g_tot == 0`, script chỉ in ra header `LỖI KHỞI ĐỘNG RUNNER` mà không hiển thị trích đoạn `g_out` ra Telegram hay log file.
- **Giải pháp**:
  Bổ sung trích xuất 10-15 dòng cuối của `g_out` (loại bỏ dòng trống) vào bản tin alert Telegram khi phát hiện `LỖI KHỞI ĐỘNG RUNNER`, giúp Coordinator biết ngay dòng lỗi mà không cần lục tìm logcat.

---

## 4. Script Kiểm Tra Preflight Nhanh (Deterministic Diagnosis Script)
Khi nghi ngờ Runner lỗi khởi động, Coordinator ủy thác worker chạy 1 script chẩn đoán duy nhất:
```python
import os, sys, traceback

os.environ["PYTHONPATH"] = r"D:\Taadaa\register gmail;D:\Taadaa\automation-core\src"
sys.path.insert(0, r"D:\Taadaa\register gmail")
sys.path.insert(0, r"D:\Taadaa\automation-core\src")

manifest_path = os.environ.get("GMAIL_ASSIGNMENT_MANIFEST", r"C:\Users\Kibe\AppData\Local\automation-core\assignments\register-gmail.json")
worker_id = os.environ.get("GMAIL_WORKER_ID", "taadaa-writer-3c47f89f35e44795a79267e09fbcc72d")

import gmail_reg_v10 as g
from automation_core.assignments import AssignmentManifest

# 1. Device Map
dmap = g.load_device_map_from_excel()
print(f"Device Map OK: {len(dmap)} devices")

# 2. Cooldown
ready = g.get_machines_ready(5, quiet=True)
print(f"Cooldown OK: {len(ready)} ready: {ready}")

# 3. Assignment Manifest
m = AssignmentManifest.load(manifest_path)
m.assert_owner(worker_id)
for stt in ready:
    m.assert_assigned(f"machine:{int(stt)}")
print("Assignment Preflight OK: 100% passed")
```
