# Device Lock Release Ownership Mismatch — Consumer Pattern Fix (2026-08-12)

## Problem
`DEVICE_LOCK_RELEASE_OWNERSHIP_MISMATCH` when calling `reservation.release()` in finally block after worker has already released/upgraded the lock.

## Root Cause
- Orchestrator acquires reservation lock (run_id A)
- Worker acquires actual lease lock (run_id B, different lock_id)
- Worker finishes, calls `lease.finish(succeeded=True)` → releases lock files
- Orchestrator finally block calls `reservation.release()` with `strict=True`
- Core verifies `lock_id` match → mismatch (run_id A ≠ run_id B) → raises error

## Fix: Use `release_with_audit(strict=False)` in Consumer Finally Block
```python
finally:
    for reservation in reservations.values():
        try:
            reservation.release_with_audit(reason="reservation cleanup after reconcile batch")
        except Exception:
            pass
```

## Why This Works
- `release_with_audit` → `_release_lease_paths(..., strict=False)`
- `strict=False` skips `lock_id` verification
- Only removes lock files still owned by THIS lease (matching host+pid+run_id)
- Worker's lock files (different run_id) are preserved
- No crash, no orphan locks from reservations that never reached worker

## Where Applied
- `tiktok-log-in/login_runner/account_reconcile.py` line 794 (finally block)
- Pattern should be used by ALL consumers that acquire reservations then hand off to workers

## Core API Reference
- `DeviceLockLease.release()` — strict=True, for explicit release by owner
- `DeviceLockLease.release_with_audit()` — strict=False, for cleanup after handoff
- `DeviceLockLease.finish(succeeded=True)` — success path, releases automatically
- `DeviceLockLease.finish(succeeded=False)` — failure path, sets status=handoff, KEEPS lock

## Anti-Pattern (What NOT To Do)
```python
# WRONG - crashes if worker already released
for r in reservations.values():
    r.release()  # strict=True by default

# WRONG - ignores lock ownership entirely
import os; os.remove(lock_path)

# CORRECT - uses audit release
for r in reservations.values():
    try:
        r.release_with_audit(reason="cleanup")
    except Exception:
        pass
```