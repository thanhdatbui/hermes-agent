# PowerShell Native Exit Code, Pinned Python Runtime & Batch Alert Suppression Invariants

Đúc kết từ sự cố audit và triển khai hệ thống Batch Error Aggregator & Suppression trên Taadaa Phone Farm (07/09/2026 - 08/09/2026).

---

## 1. Cạm Bẫy Gọi Python Trần Trong Script PowerShell (`& $python` vs `python`)

### Hiện tượng & Hậu quả
- Trong các script launcher/batch PowerShell (như `run_tiktok_upload_batch.ps1`, `run-feed-session.ps1`), môi trường Python runtime luôn được phân giải và ghim chặt (pinned runtime) ở đầu script:
  ```powershell
  $python = (Resolve-Path $PythonPath).Path
  ```
- Khi thêm hook hoặc công cụ phụ trợ (như `batch_aggregator`), nếu vô tình gọi `python -m automation_core.batch_aggregator`:
  - Lệnh sẽ sử dụng `python.exe` ngẫu nhiên từ biến môi trường `PATH` của hệ điều hành host thay vì venv chuyên dụng của batch.
  - Kết quả: Ném lỗi `ModuleNotFoundError: No module named 'automation_core'`, hook fail âm thầm và không bao giờ chạy được, dù file code vẫn tồn tại trong venv.

### Quy chuẩn bắt buộc
- **BẮT BUỘC** luôn dùng cú pháp gọi biến runtime đã ghim:
  ```powershell
  & $python -m automation_core.batch_aggregator "$summaryPath" --telegram
  ```
- Tuyệt đối không gọi `python` trần trong bất kỳ launcher script PowerShell nào.

---

## 2. Cạm Bẫy `try/catch` Nuốt Lỗi Lệnh Native Exe Trong PowerShell

### Hiện tượng & Hậu quả
- Khi viết:
  ```powershell
  try {
      & $python -m some_module
  } catch {
      Write-Warning "Error: $_"
  }
  ```
- Trên **Windows PowerShell 5.1** và **PowerShell Core < 7.4**, kể cả khi đã đặt `$ErrorActionPreference = 'Stop'`, một tiến trình native (`.exe`) trả về non-zero exit code (ví dụ `exit 1`) **KHÔNG TẠO RA TERMINATING ERROR**.
- Hậu quả: Khối `catch` **không bao giờ được kích hoạt**. Lỗi in thẳng ra stderr, script tiếp tục chạy và người vận hành có cảm giác an toàn giả là lỗi đã được bắt.

### Quy chuẩn bắt buộc
- Luôn kiểm tra biến `$LASTEXITCODE` tường minh kết hợp với `try/catch` (để bắt cả `CommandNotFoundException` lẫn lỗi native exit code):
  ```powershell
  try {
      & $python -m automation_core.batch_aggregator "$summaryPath" --telegram
      if ($LASTEXITCODE -ne 0) {
          Write-Warning "batch_aggregator exit $LASTEXITCODE (summary vẫn đã ghi: $summaryPath)"
      }
  } catch {
      Write-Warning "batch_aggregator hook error: $_"
  }
  ```

---

## 3. Bất Biến Kiểu Trả Về Của Cơ Chế Chặn Alert (Alert Suppression Return Type)

### Hiện tượng & Hậu quả
- Khi bổ sung cờ chặn gửi alert đơn lẻ (`send_farm_machine_alert`) để phục vụ gom lỗi batch, nhánh bị chặn trả về một `dict` thông tin:
  ```python
  if _should_suppress_immediate_machine_alert():
      return {"status": "suppressed_for_batch", "machine": machine}
  ```
- Trong Python, một `dict` không rỗng luôn mang giá trị `bool(dict) is True` (truthy).
- Caller ở ngoài kiểm tra `if send_farm_machine_alert(...):` sẽ ngộ nhận là **alert đã được gửi thành công lên Telegram**, làm sai lệch logic audit và telemetry của hệ thống.

### Quy chuẩn bắt buộc
- Nhánh bị chặn bắt buộc phải trả về `False` để đồng nhất 100% với kiểu dữ liệu `bool` của hàm:
  ```python
  if _should_suppress_immediate_machine_alert():
      log.info("Immediate machine alert suppressed for machine %s (batch aggregation mode enabled)", machine)
      return False
  ```

---

## 4. Kỷ Luật Thực Thi Liền Mạch Đa Phase ("Làm xong hết luôn r báo")

- Khi người dùng đã duyệt kiến trúc và ra lệnh triển khai trọn gói (*"Làm xong hết luôn r báo đừng dừng lại báo từng phase nữa"*):
- Coordinator **BẮT BUỘC** duy trì điều phối worker tự động chạy nối tiếp qua toàn bộ các phase:
  1. Patch core/primitives $\rightarrow$ Verify syntax & unit test.
  2. Implement features/aggregator $\rightarrow$ Test dual-threshold.
  3. Hook runner integration $\rightarrow$ Review Claude CLI Opus High.
- **CẤM TUYỆT ĐỐI** dừng lại ở mỗi sub-phase nhỏ để xin xác nhận hay báo cáo tiến độ lắt nhắt, làm gián đoạn dòng suy nghĩ và gây bực bội cho người vận hành.
