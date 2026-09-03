# Device Lock Protocol v2 & Target Inventory Datetime Markers (2026-08-22 Incident)

## 1. PowerShell Reservation Lock Protocol v2 (`queued_v2`)

### Triệu chứng & Nguyên nhân gốc
Khi chạy launcher PowerShell (ví dụ `run_parallel.ps1`) tạo reservation trước khi spawn worker Python (`gmail_reg_v10.py`):
- Worker Python gọi `automation_core.device_lock.acquire_device_lock` bị crash với:
  ```
  DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE: operation=acquire path_index=0
  ```
- **Nguyên nhân**: `automation_core.device_lock` (Protocol v2) kiểm tra `_hold_path_guards`. Nếu file lock đang tồn tại có `status` là `"queued"` hoặc thiếu `lock_protocol_version: 2` trong khi process PID của launcher PowerShell vẫn còn sống, `automation_core` sẽ coi đây là reservation của protocol v1 chưa nâng cấp và từ chối chuyển giao lock (raise `_DeviceLockGuardUnavailable`).

### Chuẩn payload Reservation Lock bắt buộc cho PowerShell Launcher
Trong hàm `Try-ReserveQueuedLock`, payload JSON ghi ra file `.lock.json` bắt buộc phải có:
```powershell
$payload = [ordered]@{
    machine               = $Machine
    serial                = if ($Serial) { $Serial } else { "" }
    pid                   = $PID
    host                  = [System.Net.Dns]::GetHostName()
    project               = "register gmail"
    command               = $MyInvocation.Line
    started_at            = [DateTimeOffset]::UtcNow.ToString("o")
    lock_id               = $lockId
    run_id                = $runId
    status                = "queued_v2"              # BẮT BUỘC: queued_v2 (không dùng "queued")
    lock_protocol_version = 2                        # BẮT BUỘC: số nguyên 2
    owner_active          = $true
    process_started_at    = ([System.Diagnostics.Process]::GetCurrentProcess().StartTime.ToUniversalTime().ToString("o"))
}
```

### Hàm giải phóng Reservation (`Release-QueuedReservations`)
Khi cleanup, phải đối chiếu đúng `status = "queued_v2"`:
```powershell
function Release-QueuedReservations {
    foreach ($reservation in @($reservedLocks)) {
        foreach ($path in @($reservation.paths)) {
            Remove-OwnedQueuedLock -Path $path -ExpectedHost ([System.Net.Dns]::GetHostName()) -ExpectedPid $PID -ExpectedLockId $reservation.lock_id -ExpectedRunId $runId -ExpectedStatus "queued_v2"
        }
    }
}
```

---

## 2. Xử lý Datetime Metadata trong Cột Device ID (Target Inventory)

### Triệu chứng & Nguyên nhân gốc
Trong quá trình phát hiện target (ví dụ `_detect_clean.py` / `scripts/target_inventory.py` của `Tiktok_Reg`):
- Script báo lỗi dừng:
  ```
  DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT: machine 7
  ```
- **Nguyên nhân**: Trong Excel (`taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`), người vận hành dán nhầm chuỗi ngày giờ (ví dụ `'2026-08-18 18:27:39'`) vào cột `Device ID` thay vì cột `Ngày tạo`. Script parser chỉ lọc các format date-only (`%d/%m/%Y`, `%d-%m-%Y`, `%Y-%m-%d`), dẫn đến việc chuỗi datetime bị coi là một serial thiết bị thứ 2 hợp lệ của cùng một máy -> gây xung đột duplicate serial.

### Quy tắc chuẩn hóa Parser Date Markers
Trong mọi parser đọc target inventory từ Excel:
1. **Mở rộng `_DATE_MARKER_FORMATS`** bao gồm cả định dạng datetime đầy đủ:
   ```python
   _DATE_MARKER_FORMATS = (
       # Date-only
       "%d/%m/%Y",
       "%d-%m-%Y",
       "%Y-%m-%d",
       # Full datetime with seconds
       "%Y-%m-%d %H:%M:%S",
       "%d/%m/%Y %H:%M:%S",
       "%d-%m-%Y %H:%M:%S",
   )
   ```
2. **Kiểm tra cả `datetime`/`date` object**:
   ```python
   def _is_inventory_date_marker(value: Any) -> bool:
       if isinstance(value, (datetime, date)):
           return True
       if not isinstance(value, str):
           return False
       clean = value.strip()
       if not clean:
           return False
       for fmt in _DATE_MARKER_FORMATS:
           try:
               datetime.strptime(clean, fmt)
               return True
           except ValueError:
               continue
       return False
   ```
