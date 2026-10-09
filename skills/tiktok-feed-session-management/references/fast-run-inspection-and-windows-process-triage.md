# Fast O(1) Feed Run Inspection & Windows Process Triage

## 1. Foreground Terminal Call Invariant
Mọi lệnh `terminal` foreground trên máy chủ Windows bắt buộc phải truyền tham số `timeout <= 60s` (ví dụ `timeout=30` hoặc `timeout=15`).
Nếu thiếu tham số `timeout`, lệnh sẽ bị chặn ngay lập tức bởi guard:
`[GUARD_FOREGROUND_TIMEOUT_MISSING] Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= 60s hoặc chạy background=True.`

## 2. Cấu Trúc Runtime Live & O(1) Run Manifest Inspection
- Đường dẫn run chuẩn:
  `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<N>-<HHMMSS>/<timestamp>/run_manifest.json`
- CẤM TUYỆT ĐỐI dùng recursive glob `**` (`glob.glob('D:/Taadaa/runtime/**/...')`) hoặc `os.walk` diện rộng trên `D:/Taadaa/runtime/` — sẽ kích hoạt ngay `[GUARD_DANGEROUS_ROOT]`.
- Cách lấy danh sách ca/phiên trong ngày an toàn:
  ```python
  import os
  date_live = 'D:/Taadaa/runtime/kibe/live/2026-09-29'
  runs = sorted(os.listdir(date_live))  # e.g. ['row-1-060051', 'row-1-080036']
  ```
- Cách bóc tách lý do fail của toàn bộ 80 máy:
  Đọc trực tiếp file `run_manifest.json` ở thư mục con của run (`multi_machine_summary` list chứa `machine`, `final_status`, `stop_reason`). Không cần quét đệ quy các thư mục `machines/machine_X`.

## 3. Pitfall Kiểm Tra Tiến Trình Trên Host 56 Cores
- **Vấn đề:** Khi farm đang chạy đồng thời hàng chục worker, việc dùng `psutil.process_iter(['name', 'cmdline'])` trong Python trên Windows/MSYS có thể mất >30 giây và bị timeout (124) do overhead truy vấn thông tin chi tiết từng tiến trình trong toàn bộ hệ thống.
- **Giải pháp:** Sử dụng lệnh Windows-native nhanh tức thì:
  ```bash
  tasklist /fi "imagename eq python.exe"
  ```
  Hoặc truy vấn PowerShell có chọn lọc:
  ```bash
  powershell "Get-Process -Name python -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"
  ```
