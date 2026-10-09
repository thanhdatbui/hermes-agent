# Shift Upload Lock In-Process Coordination & Fast Scan (Case 104 - 2026-09-05)

## 1. Hiện tượng & Bối cảnh
- **Bối cảnh:** Watchdog Phiên 3 Ca 1 ngày 05/09/2026 ghi nhận 21 máy bị lỗi "Timeout/Quá giờ" khi hook đăng video (`_run_upload_hook`) kích hoạt đồng loạt: M1, M2, M13, M16, M17, M18, M24, M25, M31, M35, M38, M39, M41, M49, M53, M55, M60, M64, M77, M78, M80.
- **Artifact:** `upload_result.json` ghi `status="failed"`, `reason="shift_upload_lock_timeout_fail_closed"`.

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Tranh chấp khóa liên tiến trình không có điều phối luồng nội bộ:**
   - 40-74 worker threads trong cùng process Python đồng loạt gọi `_ShiftUploadLedger.claim_reservation`.
   - `_InterProcessFileLock` chỉ có file lock OS (`msvcrt.locking` trên Windows) mà không có `threading.RLock()` cấp process. Hàng chục luồng liên tục gọi `open()` và `locking()` rồi sleep jitter (20-80ms), gây nghẽn nghiêm trọng kernel I/O và lock thrashing.
2. **Quét thư mục đĩa lớn khi ĐANG GIỮ exclusive lock:**
   - Trong `claim_reservation`, khi đang giữ exclusive file lock, script chạy `report_root.glob(f"run_{serial}_{date_compact}_*/report.json")` trên `D:/CodexRuntime/tiktok-video/runs` (chứa hơn 48.000 thư mục).
   - Thao tác glob 48k thư mục tốn 100-300ms/máy khi ĐANG GIỮ exclusive lock. 40 máy xếp hàng nhân dồn thời gian chờ vượt quá 180s timeout, khiến 21 máy ở cuối hàng bị `TimeoutError`.
3. **Thất thoát deadline config:**
   - `_run_upload_hook` truyền `ctx.config` thay vì `deadline_config` vào `_ShiftUploadLedger`, làm mất thông tin deadline riêng biệt của child context.

## 3. Kiến trúc giải pháp chuẩn (Case 104)
### A. Khóa kép In-Process + Inter-Process (`_LOCAL_LEDGER_LOCK`)
```python
_LOCAL_LEDGER_LOCK = threading.RLock()

@contextmanager
def _acquire_local_ledger_lock(timeout: float | None = None, deadline: float | None = None):
    # Clamps wait time to min(timeout, deadline - now)
    # Uses Python RLock to serialize threads in user space with zero kernel lock thrashing
    ...
```
- Mọi phương thức `_ShiftUploadLedger` (`claim_reservation`, `record_launched`, `record_spawn_failed`, `complete_success`, `release_reservation`) đều bọc `with _acquire_local_ledger_lock(...)` trước `with _InterProcessFileLock(...)`.
- Tại bất kỳ thời điểm nào, tối đa chỉ 1 thread trong Python process chạm vào OS file lock.

### B. Fast Ground Truth Pre-scan với `os.scandir`
- Thay `report_root.glob(...)` bằng `_find_ground_truth_reports()` dùng `os.scandir` lọc prefix `f"run_{serial}_{date_compact}_"`.
- Đưa thao tác quét và đọc JSON report ra **TRƯỚC** khi chiếm lock.
- Thời gian giữ exclusive lock giảm từ ~100-300ms xuống chỉ còn ~1-3ms (chỉ đọc/ghi JSON lịch sử). 40 máy giải quyết xong trong ~80ms.

### C. Nâng `lock_timeout` và chuẩn hóa `deadline_config`
- `lock_timeout` mặc định nâng lên `300.0s` (hỗ trợ override qua `shift_upload_lock_timeout_seconds`).
- Truyền đúng `deadline_config` tại `_run_upload_hook`.

## 4. Verification Standard
- Cú pháp: `python -m py_compile python_runner/flows/multi_machine_feed_session.py`.
- Unit tests: `pytest python_runner/tests/test_upload_hook.py` (bao gồm `test_shift_upload_ledger_local_lock_concurrency`, `test_shift_upload_ledger_find_ground_truth_reports_fast_scandir`, `test_shift_upload_ledger_lock_timeout_config_override`).
