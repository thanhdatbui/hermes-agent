# Lock Force Preempt Protocol for Live Canary

## Problem
When a farm incident triggers `GIỮ HIỆN TRƯỜNG`, the lock status is set to `"blocked"` (in `multi_machine_feed_session.py` lines 3870, 3907). This lock is retained by the watchdog `reap-dead-owner-locks.py` for up to 90 minutes TTL even if the owner PID is dead. Developer cannot run canary because `acquire_device_lock` rejects locked machines.

## Solution: `force_preempt=True`

When operator explicitly authorizes canary despite lock:
```python
from automation_core.device_lock import acquire_device_lock

lease = acquire_device_lock(
    machine=74,
    serial="ce061606c21e153d03",
    project="tiktok-follow-canary",
    command="test canary",
    force_preempt=True  # Override "blocked" status
)
```

## When to Use
- Lock status = "blocked" AND PID is dead (stale lock)
- Operator wants to verify fix immediately without waiting 90min TTL
- **NOT when PID is alive** (farm actually running) — respect active session

## Post-Canary Protocol
1. Canary pass → operator types `"Mở khóa máy 74"` or `"Unlock all"`
2. Gateway calls reap/release API to clear lock
3. Next cron batch acquires fresh lock normally

## Machine 74 Case (2026-09-03)
- First alert: `identity mismatch` → lock "blocked", PID 144872 (dead)
- Developer tried canary → rejected by lock
- Second check: cron started new feed-session, new lock PID 140456 (ALIVE)
- **Correct decision:** Canary blocked because farm actually running, not stale lock

## Decision Tree
```
lock exists?
  NO → run canary directly
  YES → status == "blocked"?
    NO → status == "running"?
      NO → check PID
        PID dead → force_preempt canary
        PID alive → BLOCKED (farm running)
      YES → BLOCKED (farm running)
    YES → check PID
      PID dead → force_preempt canary (stale blocked)
      PID alive → BLOCKED (farm running)
```

## Key Files
- `automation_core/device_lock.py` — `acquire_device_lock(force_preempt=True)`
- `scripts/reap-dead-owner-locks.py` lines 169-175 — TTL retention for "blocked"
- `references/device-lock-blocked-state-and-canary-discipline.md`
- `references/live-unlock-rerun-and-concise-report.md` § Stale lock detection