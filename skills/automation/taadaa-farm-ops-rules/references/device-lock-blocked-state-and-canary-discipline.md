# Device Lock "blocked" State & Canary Discipline (Farm Context)

## The Lock Loop Problem (Related to Alert [MÁY N])

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

## Correct Discipline (After Fixing Code)

1. **Do NOT delete lock files manually** (breaks audit trail)
2. **Run canary only after operator clears the lock**: Operator types `"Mở khóa máy 74"` or `"Unlock all"` in Telegram → gateway calls reap/release
3. **Or wait for TTL expiry** (90 min) - watchdog will auto-reap
4. **Then run canary** with `python D:/Taadaa/tools/inspect_machine.py 74` + `python follow_runner/run_follow.py --machine 74 ...`

## Stale Lock Detection (Before Declaring BLOCKED)

When `inspect_machine.py` reports a lock, **always check PID liveness** before concluding BLOCKED:

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

## Key Files
- `python_runner/flows/multi_machine_feed_session.py` lines 3870, 3907 - sets `"blocked"`
- `scripts/reap-dead-owner-locks.py` lines 169-175 - TTL retention for `"blocked"`
- `tools/watch_device_locks.py` - monitoring + Telegram reporting
- `automation_core/device_lock.py` - core lock API