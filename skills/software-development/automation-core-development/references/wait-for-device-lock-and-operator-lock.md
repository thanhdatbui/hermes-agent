# wait_for_device_lock and operator_device_lock Pattern

## Context & Purpose
When operator tools or high-priority automations need a device that might be temporarily held by another routine (e.g. cron run or transient step), polling with timeout and dead-owner cleanup prevents immediate lock contention failures.

## Core Primitives

### 1. `DeviceLockTimeoutError`
- Subclasses `TimeoutError`.
- Attributes: `machine`, `serial`, `owner` dict, `waited_seconds`.

### 2. `wait_for_device_lock`
- Polls `acquire_device_lock` until success or timeout deadline.
- Handles `DeviceLockUnavailable` and optionally `DeviceLockNeedsUserDecision`:
  - `wait_on_user_decision: bool = True`: when True, waits/retries if a lock needs user decision; when False, raises `DeviceLockNeedsUserDecision` immediately.
  - `release_on_terminal: bool | None = None`: Explicitly forwarded to `acquire_device_lock`. When `None`, defers to `acquire_device_lock` default (`_default_release_on_terminal()`). Forwarded explicitly from `operator_device_lock(release_on_terminal=True)` to prevent silent kwargs drift.
- Dead-owner reaping: When `reap_dead_owner=True`, inspects `_owner_process_alive(owner)`. If owner PID is dead, removes stale lock candidate files via `device_lock_paths(...)` under `lock_root`.
  - TOCTOU mitigation: Inspects candidate JSON with `_safe_read_json(candidate)` to ensure `lock_id` and `pid` strictly match the dead owner before unlinking.
  - Spin prevention: Checks `if time.monotonic() >= deadline: break` before calling `continue` after cleanup so reaping cannot spin past timeout.
- Raises `DeviceLockTimeoutError` with detailed diagnostics on expiration, recording actual monotonic elapsed time in `waited_seconds`.

### 3. `operator_device_lock`
- Context manager yielding `DeviceLockLease`.
- Wraps `wait_for_device_lock`.
- Ensures `lease.release()` is called on exit if `release_on_terminal=True` and lease hasn't already been released. Any release failure is logged via `log.warning` rather than silently swallowed.

## Testing Guidelines
- Always pass `lock_root=tmp_path` and `bypass_proxy_readiness=True` to isolate tests from real devices/proxy health checks.
