# Chẩn đoán Cron Pipeline Đêm (Night Chain Reg Gmail -> Reg TikTok)

Tài liệu ghi lại các nguyên nhân cốt lõi khiến cron job `night-chain-reg-gmail-tiktok` thất bại trong quá trình chạy tự động không người can thiệp (no-agent launcher).

---

## 1. Phase 1 — Reg Gmail: Lỗi Device Lock Guard

### Triệu chứng
15/15 worker máy thất bại ngay lúc khởi động:
```text
FAILED (FAILED_OTHER) -> DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE: operation=acquire path_index=0
```

### Nguyên nhân
- `run_parallel.ps1` (PowerShell reservation launcher) tạo các file lock dự giữ chỗ (`queued`) trong `$lockRoot` (`~/.codex/device-locks/machine_XX.lock.json`).
- Payload được tạo bởi PowerShell chỉ ghi:
  ```json
  {
    "status": "queued",
    "owner_active": true
  }
  ```
  mà **thiếu** trường `"lock_protocol_version": 2`.
- Khi worker Python (`gmail_reg_v10.py`) khởi chạy và gọi `automation_core.device_lock.acquire_device_lock()`, core thực thi transaction context `_hold_path_guards()`.
- Tại đây, hàm kiểm tra lock hiện hữu:
  ```python
  if (
      legacy_owner
      and legacy_owner.get("lock_protocol_version") != _LOCK_PROTOCOL_VERSION
      and str(legacy_owner.get("status") or "").strip().lower() in {"queued", "running", "recovery"}
      and _owner_process_alive(legacy_owner) is not False
  ):
      raise _DeviceLockGuardUnavailable(index)
  ```
  Vì thiếu `lock_protocol_version: 2`, core nhận định đây là legacy lock không thể claim đè và raise `_DeviceLockGuardUnavailable`.

### Giải pháp kỹ thuật
Trong `run_parallel.ps1`, payload reservation phải luôn bao gồm:
```powershell
lock_protocol_version = 2
```

---

## 2. Phase 2 — Reg TikTok: Lỗi Target Inventory Conflict do Datetime String

### Triệu chứng
Preflight detection `_detect_clean.py` / `_run_all_targets.py` thất bại ngay lập tức:
```text
DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT: machine 7
Target detection failed with exit code 2
```

### Nguyên nhân
- File Excel `taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx` có các dòng chứa giá trị ngày giờ được paste vào cột `device ID` (ví dụ tại Máy 7 dòng 54 có `2026-08-18 18:27:39`).
- Module `scripts/target_inventory.py` của repo `Tiktok_Reg` dùng hàm `_is_inventory_date_marker()` để bỏ qua các cell chứa ngày tháng, nhưng chỉ hỗ trợ:
  ```python
  _DATE_MARKER_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d")
  ```
- Chuỗi datetime có giờ phút giây `YYYY-MM-DD HH:MM:SS` (hoặc format `datetime` string tương đương) không match bất kỳ format nào trong tuple trên, dẫn tới `_is_inventory_date_marker()` trả về `False`.
- Script đọc chuỗi ngày giờ này như một `serial` mới của máy 7, trong khi các dòng khác của máy 7 có serial `9885f63030454d3055` -> báo lỗi `TARGET_INVENTORY_CONFLICT`.

### Giải pháp kỹ thuật
Mở rộng `_DATE_MARKER_FORMATS` trong `scripts/target_inventory.py` hỗ trợ đầy đủ các định dạng ngày giờ:
```python
_DATE_MARKER_FORMATS = (
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S"
)
```
Hoặc dùng `datetime.fromisoformat()` / check date parser tổng quát.
