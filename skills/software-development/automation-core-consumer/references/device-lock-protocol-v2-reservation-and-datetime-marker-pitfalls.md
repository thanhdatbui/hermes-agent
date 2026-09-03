# Device Lock Protocol v2 Reservation & Target Inventory Datetime Marker Pitfalls

## 1. Device Lock Protocol v2 Reservation Contract in Consumer Launchers

Khi các consumer runner / launcher (ví dụ PowerShell `run_parallel.ps1` hoặc Python launchers) tạo reservation lock trước khi spawn worker con, payload reservation BẮT BUỘC phải tuân theo chuẩn Protocol v2:

### Payload Specification
```json
{
  "machine": "57",
  "serial": "9885e64b4a434a3037",
  "pid": 12345,
  "host": "DESKTOP-HOSTNAME",
  "project": "register gmail",
  "command": "<redacted>",
  "started_at": "2026-08-22T00:00:00.0000000Z",
  "lock_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "run_id": "register-gmail-20260822_000000-abcd1234",
  "status": "queued_v2",
  "owner_active": true,
  "lock_protocol_version": 2,
  "process_started_at": "2026-08-22T00:00:00.0000000Z"
}
```

### Critical Rules
1. **`status` & `lock_protocol_version`:** Phải là `"status": "queued_v2"` và `"lock_protocol_version": 2`. Nếu ghi `"status": "queued"` hoặc thiếu `lock_protocol_version: 2`, khi worker con gọi `automation_core.device_lock.acquire_device_lock()`, hàm `_hold_path_guards` sẽ phát hiện lock phiên bản cũ chưa upgrade và từ chối claim -> raise `DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE`.
2. **`run_id` Propagation:** Parent launcher phải sinh `$runId` duy nhất một lần cho batch run, gán vào reservation lock payload, và truyền cho worker con qua biến môi trường `$env:CODEX_DEVICE_LOCK_RUN_ID = $runId`. Worker con sẽ đọc biến này để `acquire_device_lock` xác thực đúng reservation của parent và promote sang `status="running"`.
3. **Atomic Publication & Cleanup:** Khi tạo reservation, nên ghi file tạm rồi atomic move (hoặc dùng `FileMode.CreateNew`) để tránh partial/corrupted lock file. Khi release, dùng guarded CAS deletion (`.$fileName.takeover.lock`) với đầy đủ fingerprint matching (`lock_id`, `pid`, `host`, `run_id`, `process_started_at`).

---

## 2. Target Inventory Workbook Datetime Marker Conflict

### Triệu chứng
Trong quá trình preflight target detection (ví dụ `_detect_clean.py` / `target_inventory.py` của `Tiktok_Reg`):
`DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT: machine X`

### Nguyên nhân
- Trong Excel workbook (`taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`), cột `Device ID` / serial tại một số dòng bị dán nhầm chuỗi ngày giờ (ví dụ `'2026-08-18 18:27:39'`) hoặc cell dạng Excel datetime.
- Nếu helper `_is_inventory_date_marker` chỉ hỗ trợ định dạng date-only (`%d/%m/%Y`, `%d-%m-%Y`, `%Y-%m-%d`), các chuỗi timestamp có giờ phút giây sẽ bị coi là một device serial thứ 2 của máy X -> parser phát hiện máy X có 2 serial khác nhau gây conflict inventory.

### Cách xử lý chuẩn
1. Kiểm tra type `isinstance(value, (datetime, date))` trả về `True` ngay.
2. Bổ sung các format datetime đầy đủ vào allowlist `_DATE_MARKER_FORMATS`:
   - `"%Y-%m-%d %H:%M:%S"`
   - `"%d/%m/%Y %H:%M:%S"`
   - `"%d-%m-%Y %H:%M:%S"`
   - `"%Y-%m-%d"`
   - `"%d/%m/%Y"`
   - `"%d-%m-%Y"`
3. Giữ strict parsing (`datetime.strptime`) để tránh nhận nhầm device serial thật (dạng hex/alphanumeric) thành date marker.
