# Device Lock Acquire Guard Unavailable Triage

## Symptom
`multi-machine-feed-session` crashes immediately upon startup (seconds 0–1) without dispatching any child workers:
`runner failed before completion: DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE: operation=acquire path_index=0`

## Root Cause
1. During the startup batch reservation phase in `python_runner/flows/multi_machine_feed_session.py`, the runner loops through all target machines to acquire queued reservations via `acquire_device_lock(status="queued", user_authorized=True)`.
2. Inside `automation_core/device_lock.py`, `_hold_path_guards(paths)` attempts an atomic exclusive file creation (`open("x")`) of `.takeover.lock` markers (e.g., `~/.codex/device-locks/.machine_1.lock.json.takeover.lock`).
3. If an orphan `.takeover.lock` marker remains from an abrupt process termination, or an incompatible active legacy lock exists, `_hold_path_guards` raises `_DeviceLockGuardUnavailable(index)`, translated into `DeviceLockTransactionError("DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE")`.
4. Because this exception is unhandled during the initial batch reservation loop, a single machine guard failure (e.g., machine 1 at `path_index=0`) aborts the entire multi-machine feed run for all 70+ machines.

## Triage & Resolution Steps
1. **Locate Guard Markers**:
   Inspect `~/.codex/device-locks/` (or `%USERPROFILE%\.codex\device-locks\`) for hidden orphan `.*.takeover.lock` files:
   ```bash
   ls -la ~/.codex/device-locks/.*.takeover.lock
   ```
2. **Check Dead-Owner Locks**:
   Check if the lock owner process is still active using `tasklist /FI "PID eq <pid>"`.
   Run the dead lock reaper or check cron job `reap-dead-owner-locks` (`b63730cc5c85`):
   ```bash
   python "D:\Taadaa\tiktok-luot nuoi acc\scripts\reap-dead-owner-locks.py"
   ```
3. **Verify Runner Resumption**:
   Once the guard marker/stale lock is cleared, subsequent cron triggers (every 15m) will acquire reservations and execute feed sessions across all available machines normally.
