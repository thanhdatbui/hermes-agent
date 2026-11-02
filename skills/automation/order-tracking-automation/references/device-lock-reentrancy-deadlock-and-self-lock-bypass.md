# Device Lock Re-entrancy Deadlock & Self-Lock Bypass Pattern

## 1. The Non-Reentrant Device Lock Trap (Bẫy Tự Chờ Khóa Của Chính Mình)
- **Problem:**
  In Taadaa Farm automation, `automation_core.device_lock.operator_device_lock` writes a lock JSON file (`serial_{serial}.lock.json`) recording the current `pid`, `machine`, `serial`, and timestamps.
  When an outer orchestrator (e.g. `order_lifecycle.py` or a multi-machine batch runner) acquires the lock:
  ```python
  with operator_device_lock(serial=serial, timeout=10.0):
      exit_code, summary = run_once(...)
  ```
  Downstream utility functions inside child modules (e.g. `_adb_run` and `_adb_screencap` in `tiktok_app_order_sync.py`) often also wrap their ADB calls in `with operator_device_lock(...)` for defensive standalone execution.
  Because `operator_device_lock` protocol v2 treats any existing lock file as `active` without checking if the current caller is the existing lock owner's PID, the inner call times out waiting 20s on its own outer lock:
  `DeviceLockTimeoutError: timed out waiting for device lock: ... device lock active: pid=<same_pid> ...`
  Each ADB tap or screenshot burns 20 seconds, quickly exhausting the navigation timeout (38s) and aborting with `NO_TRACKING_ON_SCREEN` or timeout exit 124.

---

## 2. Canonical Solution: Self-Lock Detection (`_is_self_locked`)
Instead of nesting `operator_device_lock` blindly, child functions must inspect whether the current process already owns the active device lock:

```python
from contextlib import nullcontext
from pathlib import Path
import json, os

def _is_self_locked(serial: str) -> bool:
    lock_path = Path.home() / ".codex" / "device-locks" / f"serial_{serial}.lock.json"
    if not lock_path.is_file():
        return False
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        return data.get("pid") == os.getpid()
    except Exception:
        return False
```

### Wrapping Pattern in Sub-operations:
```python
def _adb_run(serial: str, *args: str, check: bool = True) -> str:
    ctx = nullcontext() if _is_self_locked(serial) else operator_device_lock(serial=serial, timeout=ADB_TIMEOUT_SECONDS)
    with ctx:
        completed = subprocess.run(
            ["adb", "-s", serial, *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=ADB_TIMEOUT_SECONDS,
            check=False,
        )
    if check and completed.returncode != 0:
        raise SyncError("ADB_FAILED", completed.stderr.strip())
    return completed.stdout
```

---

## 3. Invariants & Rules
1. **Zero Deadlock:** When running under an outer lease, inner ADB / screencap execution must take milliseconds, never block waiting for lock release.
2. **Standalone Compatibility:** When invoked standalone (e.g. `python tiktok_app_order_sync.py --machine 4 --target-order ...`), `_is_self_locked` returns `False`, safely triggering `operator_device_lock` to protect against collision with concurrent cronjobs.
