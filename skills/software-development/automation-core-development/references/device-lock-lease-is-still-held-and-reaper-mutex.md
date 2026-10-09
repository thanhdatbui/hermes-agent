# DeviceLockLease is_still_held() & Reaper Mutex Protection

## 1. DeviceLockLease.is_still_held() (Active Ownership Check)

### Motivation
In long-running worker operations, a device lock might be forcefully preempted (`force_preempt`), reaped due to timeout, or cleared by an operator. A worker continuing blindly after losing its lock risks corrupting device state or clobbering another runner.

### Implementation Pattern (`automation_core.device_lock`)
```python
class DeviceLockLease:
    ...
    def is_still_held(self) -> bool:
        """Return True if this lease is still the active owner on all its paths."""
        if self._released:
            return False
        for path in self.lock_paths:
            try:
                _raw, owner = _read_json_snapshot(path)
                if not owner or owner.get("lock_id") != self.lock_id or owner.get("pid") != self.pid:
                    return False
            except Exception:
                return False
        return True
```

### Unlocked Lease Invariant
`_UnlockedDeviceLockLease` overrides `is_still_held()`:
```python
class _UnlockedDeviceLockLease(DeviceLockLease):
    def is_still_held(self) -> bool:
        return not self._released
```
Because unlocked runs never create lock files on disk, querying disk snapshots would fail. The unlocked lease remains logically held until released or exited.

---

## 2. Reaper Mutex (`.reaper.lock`) & Watchdog Race Prevention

### Motivation
When `reap-dead-owner-locks.py` cleans up orphan, expired, or dead-owner locks, concurrent execution of `watch_device_locks.py` (e.g. from scheduled tasks or Hermes cron) can inspect locks mid-transition and trigger false-positive alert notifications.

### Reaper Side (`reap-dead-owner-locks.py`)
Acquire `.reaper.lock` before scanning, and release in `finally`:
```python
reaper_lock = LOCK_ROOT / ".reaper.lock"
try:
    reaper_lock.write_text(str(datetime.now(timezone.utc).timestamp()), encoding="utf-8")
    # ... perform quarantine sweeps ...
finally:
    try:
        if reaper_lock.exists():
            reaper_lock.unlink()
    except OSError:
        pass
```

### Watchdog Side (`watch_device_locks.py`)
In `scan_active_locks()`, detect active reaper execution and skip:
```python
reaper_lock = lock_root / ".reaper.lock"
if reaper_lock.exists():
    try:
        mtime = reaper_lock.stat().st_mtime
        now_ts = datetime.datetime.now().timestamp()
        if (now_ts - mtime) < 120:
            print("[watchdog] Reaper is currently running, skipping this tick to avoid false alert.")
            return []
    except OSError:
        pass
```

### Alert Threshold Policy
- `ALERT_THRESHOLD_MINUTES = 90` (reduced from 120m): Alerts when a device lock has been held continuously for > 90 minutes.
- When reaper runs preflight, any lock > 60m TTL with dead/unverifiable owner is moved to quarantine before the watchdog scan evaluates active locks.
