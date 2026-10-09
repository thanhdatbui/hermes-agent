# Device Lock "blocked" State & Canary Discipline

## The Lock Loop Problem

When a farm incident occurs (e.g., `identity mismatch`, `follow timeout`, `MANUAL_REVIEW`), the parent feed session (`multi_machine_feed_session.py`) sets the device lock status to **`"blocked"`**:

```python
# Lines 3870, 3907 in multi_machine_feed_session.py
lock_holder["lease"].set_status("blocked")
```

This is **by design** - `"blocked"` means "hold the scene for operator triage". The lock is retained even if the owner process dies, up to the TTL (90 minutes default in `reap-dead-owner-locks.py`).

## Why This Creates a Loop

1. Incident → lock status = `"blocked"` (machine 74)
2. Watchdog `reap-dead-owner-locks.py` sees `"blocked"` → **keeps lock** (lines 169-175)
3. Developer fixes code, wants to run canary
4. Canary tries to acquire lock → rejected because lock is `"blocked"`
5. Developer can't run canary → can't verify fix → stuck

## Correct Discipline

**Sau khi fix code xong:**

1. **KHÔNG xóa file lock thủ công bằng `rm`/`del`** (phá hỏng audit trail).
2. **Kiểm tra liveness của PID:**
   - Nếu PID đã chết (`pid_alive=False`, alert `GIỮ HIỆN TRƯỜNG` thường đi kèm PID đã dừng): Chạy canary ngay với cờ `--force-preempt`:
     ```bash
     python -m follow_runner.run_follow --machine <N> --config config/machine<N>.yaml --account-row-index <slot> --force-preempt
     ```
   - `run_follow.py` sẽ tự động takeover lock cũ qua `acquire_device_lock(force_preempt=True)` và **tự động release lease trong `finally:`** khi canary hoàn tất.
   - **TUYỆT ĐỐI KHÔNG bắt user phải gõ "Mở khóa máy N"** hay từ chối canary khi PID cũ đã chết.
3. **Nếu PID đang sống thật (`pid_alive=True`):** Tiến trình farm đang thực sự chạy trên thiết bị (ví dụ cron ca mới đã takeover), lúc này mới báo BLOCKED và đợi ca kết thúc.

## Key Files

- `python_runner/flows/multi_machine_feed_session.py` lines 3870, 3907 - sets `"blocked"`
- `scripts/reap-dead-owner-locks.py` lines 169-175 - TTL retention for `"blocked"`
- `tools/watch_device_locks.py` - monitoring + Telegram reporting
- `automation_core/device_lock.py` - core lock API

## Stale Lock Detection (Before Declaring BLOCKED)

When inspect_machine reports a lock, **always check PID liveness** before concluding BLOCKED:

```python
import psutil
lock = inspect_device_lock(machine=74)
pid = lock.get("pid")
if pid:
    try:
        p = psutil.Process(pid)
        if not p.is_running():
            print("LOCK IS STALE - PID dead, safe to preempt")
        else:
            print("LOCK ACTIVE - real owner running")
    except psutil.NoSuchProcess:
        print("LOCK IS STALE - PID not found")
```

Most `GIỮ HIỆN TRƯỜNG` alerts coincide with dead PIDs (farm process already stopped). The lock remains because TTL hasn't expired.

## Canary Preemption Protocol

If operator authorizes preemption:
1. Use `acquire_device_lock(machine=74, takeover_scope="operator_preempt")`
2. Verify both machine and serial aliases point to new lease
3. Run canary
4. Release only the canary lease after cleanup

Never use `SAME_PROJECT_RECOVERY` or `FULL_SCOPE_TAKEOVER` without explicit authorization.