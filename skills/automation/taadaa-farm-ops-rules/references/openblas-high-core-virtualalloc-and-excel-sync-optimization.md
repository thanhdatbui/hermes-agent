# OpenBLAS Memory Allocation Fix trên High-Core Host & Tối Ưu Sync Excel Farm

## 1. Sự cố OpenBLAS VirtualAlloc trên Host Dual-CPU nhiều Core (56 Cores)
### Triệu chứng & Nguyên nhân
- **Triệu chứng**: Cron job hoặc script Python (đặc biệt là script watchdog/runner chạy định kỳ) bị crash đột ngột với mã thoát `exit code 1` và dòng thông báo từ stderr C-layer:
  ```text
  OpenBLAS error: Memory allocation still failed after 10 retries, giving up.
  ```
  Tiến trình sập ngay lập tức, không có Python traceback, `try...except` không bắt được.
- **Nguyên nhân gốc rễ**:
  - Host Windows Server / Workstation Dual-CPU có số core logic lớn (ví dụ: 56 logical processors).
  - Script nạp thư viện `openpyxl` (hoặc `pandas`, `scipy`). `openpyxl` kiểm tra optional dependency `numpy`, kéo theo C-extension OpenBLAS (`libscipy_openblas64*.dll`).
  - Mặc định, OpenBLAS thăm dò CPU và cố gắng cấp phát buffer bộ nhớ ảo (virtual memory chunk) cho toàn bộ 56 threads.
  - Khi farm hoạt động tải cao (hàng chục workers song song + nhiều tiến trình định kỳ), bộ nhớ ảo bị phân mảnh, hàm Win32 `VirtualAlloc` của OpenBLAS thất bại sau 10 lần thử và kích hoạt trực tiếp `exit(1)`.

### Giải pháp phòng vệ 3 lớp (Đã chuẩn hóa)
1. **Lớp 1 (Script Header - Runtime & Deploy)**:
   Khai báo biến môi trường thread caps ngay đầu file trước mọi lệnh `import` khác:
   ```python
   import os
   # Prevent OpenBLAS/MKL memory allocation failure on high-core hosts (56 cores)
   os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
   os.environ.setdefault("MKL_NUM_THREADS", "1")
   os.environ.setdefault("OMP_NUM_THREADS", "1")
   os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

   import subprocess
   import openpyxl
   ```
2. **Lớp 2 (Cron Scheduler Subprocess Runner)**:
   Trong `D:/Taadaa/Hermes/cron/scheduler.py` (hàm `_run_job_script`), tiêm trực tiếp vào `cron_env` của toàn bộ các jobs:
   ```python
   cron_env = _sanitize_subprocess_env(os.environ.copy())
   cron_env.setdefault("OPENBLAS_NUM_THREADS", "1")
   cron_env.setdefault("MKL_NUM_THREADS", "1")
   cron_env.setdefault("OMP_NUM_THREADS", "1")
   cron_env.setdefault("NUMEXPR_NUM_THREADS", "1")
   ```
3. **Lớp 3 (Windows User Environment)**:
   Cố định biến môi trường User trên hệ điều hành qua PowerShell:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('OPENBLAS_NUM_THREADS', '1', 'User')
   ```

---

## 2. Invariant Hiệu Năng openpyxl: Tuyệt đối CẤM `ws.cell()` trong chế độ `read_only=True`
- **Cơ chế gây lag**: Trong chế độ `openpyxl.load_workbook(path, read_only=True)`, worksheet được đọc dạng stream. Nếu gọi `ws.cell(row, col)`, openpyxl buộc phải re-parse toàn bộ luồng XML từ đầu cho từng ô. Với sheet 640 dòng x 4 cột, vòng lặp tốn hơn **60 - 90 giây** (hoặc timeout) thay vì **0.05 giây**.
- **Quy tắc bắt buộc**: Duyệt dữ liệu bằng `iter_rows(values_only=True)` với unpack phòng thủ:
  ```python
  # CHUẨN: Tốc độ < 0.05s
  for row in ws.iter_rows(min_row=2, values_only=True):
      if not row or row[0] is None:
          continue
      m_val = row[0]
      dev_val = str(row[1] or "").strip() if len(row) > 1 else ""
      id_val = row[2] if len(row) > 2 else None
      vids_val = row[3] if len(row) > 3 else None
  ```

---

## 3. Invariant Đồng Nhất Serial (Triệt tiêu MAPPING_CONFLICT)
- **Quy tắc**: Mỗi máy trên farm (STT 1..80) sở hữu 8 slot tài khoản. Cả 8 slot này **BẮT BUỘC** phải có cùng một Serial phần cứng (cột 10 trong `taikhoan_dat_v2_updated .xlsx`).
- **Bẫy thường gặp**: Khi thay thế tài khoản hoặc copy dữ liệu từ máy khác, quên cập nhật lại cột Serial ở dòng đó, dẫn đến 1 máy có 2 serial khác nhau. Hệ thống `SourceConfig._validate_machine_serials` sẽ ném lỗi `CRON_SOURCE_SYNC_EXC: MAPPING_CONFLICT` và chặn toàn bộ tiến trình sinh cấu hình cron.
- **Biện pháp**: Khi sửa bất kỳ slot nào, luôn chạy kiểm tra đối soát serial toàn máy:
  ```python
  # Kiểm tra máy có serial đồng nhất
  m_serials = {}
  for m, slot, serial in machine_data:
      if m in m_serials and m_serials[m] != serial:
          raise ValueError(f"SERIAL CONFLICT machine {m}: {m_serials[m]} vs {serial}")
      m_serials[m] = serial
  ```
