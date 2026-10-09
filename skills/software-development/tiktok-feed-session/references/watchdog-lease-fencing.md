# Multi-Machine Watchdog & Lease Release Fencing

## 1. Race Condition: Watchdog vs Worker Lease Release
Khi worker đã hoàn thành nhiệm vụ (`goal_completed == True`) và bắt đầu nhả lease:
- Worker gọi `_claim_success_release(timing)` -> set `timing["success_release_started"] = True`.
- Trong lúc worker đang thực hiện I/O ghi handoff evidence và gọi `lease.finish(succeeded=True)`, nếu thời gian chạm ngưỡng `deadline_mono`, watchdog tuyệt đối **KHÔNG ĐƯỢC cướp quyền** (`_claim_watchdog_terminal` phải trả về `False`).
- Nếu watchdog cướp quyền lúc này, watchdog sẽ set `terminalized = True` và ghi artifact fallback `failed`, phá vỡ kết quả chạy thành công của worker.

### Quy tắc CAS trong `_claim_watchdog_terminal`:
```python
def _claim_watchdog_terminal(timing: dict[str, Any], *, force: bool = False) -> bool:
    ...
    def _elect() -> bool:
        if timing.get("terminalized") or timing.get("publication_owner") == "watchdog":
            return False

        # QUAN TRỌNG: Worker đang nhả lease hoặc đã nhả xong -> Watchdog không được cướp quyền
        if timing.get("success_release_started") or timing.get("success_release_completed"):
            return False

        if not force and time.monotonic() < deadline:
            return False
        ...
```

---

## 2. Tránh Invert Status sau khi Lease đã Release Thành Công
Trong `_release_under_lock`:
- Khi `lease.finish(succeeded=True)` đã chạy xong, lease của thiết bị đã thực sự được nhả về hệ thống (file lock / SQLite state đã giải phóng).
- **CẤM** đo lại `now >= deadline_mono` sau khi release để lật ngược kết quả (`_record_completion` trả về `False` -> `lease_release_failed = True` -> biến `goal_completed = False`).
- Vì I/O ghi file evidence và giải phóng file lock có thể mất vài chục đến vài trăm ms, việc kiểm tra deadline sau release sẽ vô tình biến session thành công thành `failed` với lỗi giả `lease-finish-failed` / `lease release or handoff failed`.

### Quy tắc Completion trong `_release_under_lock`:
```python
lease.finish(succeeded=True)
_write_recovery_handoff_evidence(...)
now = time.monotonic()
def _record_completion():
    # Không kiểm tra deadline_mono ở đây nữa, lease đã giải phóng thành công
    timing["success_release_completed_at"] = now
    timing["success_release_completed"] = True
    return True
```
