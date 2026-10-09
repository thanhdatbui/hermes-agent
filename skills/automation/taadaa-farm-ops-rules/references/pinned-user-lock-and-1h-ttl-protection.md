# Pinned User Lock & 1-Hour TTL Protection Architecture (Taadaa Farm)

Date: 2026-09-20
Status: ACTIVE & ENFORCED

## 1. Problem Statement
Before 2026-09-20, operators running manual device actions (Canary runs, batch repairs, debug sessions) experienced device preemptions from background cronjobs (e.g. `run_tiktok.py`, `post_evening_avatar_watchdog.py`). If the manual script failed to acquire a lock or used a default lease, background tasks would view the machine as idle or invoke `FULL_SCOPE_TAKEOVER`, opening TikTok/Profile settings and aborting the operator flow mid-run.

## 2. Core Architecture

### A. Pinned Lock in `automation_core.device_lock`
- **Context Manager**: `DeviceContext(serial=serial, machine=str(stt), project="operator-canary", user_authorized=True)`
- **Metadata**:
  - `user_authorized: True`
  - `pinned: True`
  - `ttl_seconds: 3600`
  - `last_heartbeat: <timestamp>`
- **Preemption Resistance**:
  - Standard cronjobs (`user_authorized=False`) attempting to acquire or takeover a pinned device are hard-rejected with `DeviceLockNeedsUserDecision` or `DeviceLockUnavailable`.
  - Only explicit operator actions with `force_preempt=True` can reclaim the device.

### B. 1-Hour TTL Safety in `reap-dead-owner-locks.py`
- While cronjobs cannot steal pinned devices, deadlocks must be prevented if the operator process crashes or hangs indefinitely.
- The reaper runs every 5 minutes:
  1. **Dead Owner**: If `owner_alive is False`, the lock is immediately quarantined and released, eliminating zombie locks.
  2. **Active Owner TTL**: If the owner process is still alive but the lock age exceeds 3600s (`age_seconds >= 3600`), the reaper moves the lock to `quarantine/` with reason `pinned_1h_ttl`, freeing the physical machine for night/morning farm cycles.

## 3. Usage Pattern in Python Scripts
```python
from automation_core.device_lock import DeviceContext

with DeviceContext(serial=serial, machine=str(stt), project="operator-canary", user_authorized=True) as lease:
    # Exclusive access protected against cronjobs for up to 1 hour
    ...
# Lock automatically releases cleanly on block exit
```
