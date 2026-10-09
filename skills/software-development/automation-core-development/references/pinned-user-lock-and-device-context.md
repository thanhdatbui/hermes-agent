# Pinned Lock TTL 1h, DeviceContext & Reaper Rules

## Overview
Pinned locks (`pinned=True` / `user_authorized=True`) represent explicit operator/user locks that must not be preempted or bypassed by automated tasks, while still protecting against permanent orphan locks through a 1-hour TTL and owner liveness checks.

## Key Invariants

### 1. Payload & Metadata
When `user_authorized=True`:
- `pinned: bool = True`
- `user_authorized: bool = True`
- `last_heartbeat: str` (ISO 8601 UTC timestamp)
- `ttl_seconds: int = 3600` (1 hour)

### 2. Takeover / Preempt Gating
- Automated callers (`user_authorized=False`):
  - If a device is already locked with `pinned=True` or `user_authorized=True`, raise `DeviceLockNeedsUserDecision`. Never silently skip or auto-takeover.
- Preempt / Takeover callers:
  - Standard takeover requests (`takeover_scope != TAKEOVER_SCOPE_OPERATOR_PREEMPT`) are strictly rejected on pinned locks.
  - Only explicit operator force preemption (`force_preempt=True` / `takeover_scope == TAKEOVER_SCOPE_OPERATOR_PREEMPT`) can reclaim a pinned lock.

### 3. Heartbeat Mechanism
- `DeviceLockLease.heartbeat()` and `DeviceLock.heartbeat()`:
  - Updates `last_heartbeat` in the JSON payload of all alias lock files.
  - Touches the file modification time (`mtime`) to signal active ownership to file-age checkers.

### 4. DeviceContext Context Manager
Convenience context manager for callers:
```python
class DeviceContext:
    def __init__(
        self,
        serial: str,
        machine: str | int = "1",
        *,
        project: str = "operator",
        user_authorized: bool = True,
        **kwargs,
    ):
        self.lock = DeviceLock(
            serial=str(serial),
            machine=str(machine),
            project=project,
            user_authorized=user_authorized,
            **kwargs,
        )

    def __enter__(self):
        return self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.lock.__exit__(exc_type, exc_val, exc_tb)
```

### 5. Reaper Logic (`reap-dead-owner-locks.py`)
- If `owner_alive is False`: Reap immediately, even if `pinned=True` (handles process crash / killed agent).
- If `owner_alive is True` or indeterminate:
  - If `age_seconds >= LOCK_TTL_SECONDS` (3600s / 1 hour): Reap with reason `pinned_timeout_1h` or `user_lock_expired`.
  - If `age_seconds < LOCK_TTL_SECONDS`: Strictly protect, DO NOT reap.
