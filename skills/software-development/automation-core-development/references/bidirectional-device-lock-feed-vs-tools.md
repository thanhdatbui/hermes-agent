# Bidirectional Device Lock Orchestration: Feed Session vs Operator Tools (2026-09-17)

## Problem Statement & Invariants
In the Taadaa farm (74 S7 devices), two distinct workloads contend for device control:
1. **Feed Sessions (Batch Nuôi)**: Long-running, multi-device or single-device automated workflows.
2. **Operator Tools / Maintenance Scripts**: Ad-hoc tasks (APK upgrades, 2FA setup, Gmail check, logouts, inspection).

### The Two Required Directions
- **Direction 1 (Operator Locks -> Feed Session Skips)**: If an operator locks a device to run maintenance, the upcoming feed batch must **cleanly skip** that device without failing the batch or escalating to `MANUAL_NEEDED`.
- **Direction 2 (Feed Session Runs -> Operator Script Waits)**: If a feed session is active on a device, operator tools must **wait/poll with timeout** until the feed session finishes and releases the device, rather than failing fast or colliding over ADB.

---

## Architectural Traps & Edge Cases (Audited by GPT-5.6 Sol & Claude Code)

### 1. PID Reuse Trap on Windows
- **Vulnerability**: Windows aggressively reuses Process IDs (PIDs). If process A dies and Windows allocates the same PID to process B, `psutil.pid_exists(pid)` or PowerShell `Get-Process -Id $pid` returns `True`, causing a dead lock to be treated as alive.
- **Rule**: Lock metadata MUST record `process_started_at` (process creation timestamp) in addition to `pid`. A lock is only valid if `current_proc.create_time == lock.process_started_at`.

### 2. Single-Machine No-Op Lock Defect
- **Vulnerability**: In `run_tiktok.py`, running in single-machine mode previously invoked `acquire_device_lock(user_authorized=False)`.
- **Under the hood**: `user_authorized=False` returned `_UnlockedDeviceLockLease`, which **never created a lock file on disk**. Outside scripts saw no file and assumed the device was free, causing concurrent ADB collisions.
- **Rule**: All single-machine runs that interact with the physical device MUST use `user_authorized=True` with `release_on_terminal=True` to guarantee a durable disk lock that is cleaned up even on crashes.

### 3. Preflight Batch Filtering vs Warning-Only Bug
- **Vulnerability**: In `run-feed-session.ps1`, `$machineList` was created *before* the lock check loop. When a live lock was detected, it only emitted `Write-Warning` after 600s, but still passed the locked machine into `run_tiktok.py`.
- **Rule**: Preflight PowerShell scripts must construct `$machineList` by filtering out machines with active locks *before* executing the runner.

### 4. Semantic Collapse in `_aggregate_rows`
- **Vulnerability**: In `multi_machine_feed_session.py`, `_aggregate_rows` lumped `skipped-device-locked` together with `needs-user-decision`:
  ```python
  elif final_statuses & {"skipped-device-locked", "needs-user-decision"}:
      status = ExitStatus.MANUAL_NEEDED
  ```
  If 1 out of 74 machines was locked by an operator, the entire batch exited with code 2 (`MANUAL_NEEDED`), spamming alarms.
- **Rule**:
  - `needs-user-decision`: Truly unexpected conflict -> Keep `MANUAL_NEEDED`.
  - `skipped-device-locked`: Expected transient state -> Return `SUCCESS` (or `SUCCESS_WITH_SKIPS`) as long as other runnable machines completed successfully.
  - Only escalate if **100% of requested machines were locked** (`NO_WORK_AVAILABLE`).

### 5. Double-Check Pattern with `.reaper.lock`
- **Vulnerability**: Contending on `.reaper.lock` on every acquire creates high disk I/O contention across 74 machines.
- **Rule**: Double-check pattern:
  1. Try `acquire_device_lock()`.
  2. If and only if it fails and owner PID is suspect, acquire `.reaper.lock`, re-validate, and clean up stale files.

---

## Canonical Patterns

### `wait_for_device_lock()` in `automation_core.device_lock`
```python
import time
from .device_lock import acquire_device_lock, DeviceLockUnavailable, DeviceLockNeedsUserDecision, DeviceLockLease

def wait_for_device_lock(
    *,
    machine=None,
    serial: str | None = None,
    project: str,
    timeout: float = 300.0,
    poll_interval: float = 5.0,
    lock_root=None,
    **kwargs,
) -> DeviceLockLease:
    """Poll and wait for a device lock to be released, then acquire it atomically."""
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return acquire_device_lock(
                machine=machine,
                serial=serial,
                project=project,
                lock_root=lock_root,
                user_authorized=True,
                release_on_terminal=True,
                **kwargs,
            )
        except (DeviceLockUnavailable, DeviceLockNeedsUserDecision) as exc:
            last_exc = exc
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))
    raise last_exc or TimeoutError(f"Timed out waiting for device lock: machine={machine}, serial={serial}")
```

### Operator Context Manager (`operator_device_lock`)
```python
from contextlib import contextmanager

@contextmanager
def operator_device_lock(*, machine=None, serial=None, project: str, timeout: float = 300.0, lock_root=None):
    """Context manager for operator tools: wait for ongoing feed sessions, lock, run, and auto-release."""
    lease = wait_for_device_lock(
        machine=machine,
        serial=serial,
        project=project,
        timeout=timeout,
        lock_root=lock_root,
    )
    try:
        yield lease
    finally:
        try:
            lease.release()
        except Exception:
            pass
```

### CLI Wrapper for Unmodified Tools (`tools/with_device_lock.py`)
```bash
python D:/Taadaa/tools/with_device_lock.py --machine 12 -- python D:/Taadaa/tools/upgrade_tiktok_safe_keep_login.py --machine 12
```
This avoids refactoring legacy maintenance scripts by wrapping their execution inside an acquired lease.
