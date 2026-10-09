# Persistent Device Lock Keeper & Preemption Guard

Use when acquiring an ad-hoc, inspection, or canary device lock on the farm to prevent Cronjobs from preempting the target device.

## The Pitfall: Write-and-Forget Lock
- Writing a lock file via a short-lived process (e.g. `python -c "..."` using `os.getpid()`) leaves a dead PID on disk immediately.
- Cron schedulers check `psutil.pid_exists(pid)`. When PID is dead, it is treated as a stale lock and reclaimed, clobbering interactive sessions.

## The Fix: `device_lock_keeper.py`
Located at `D:/Taadaa/tools/device_lock_keeper.py`:
- Spawns a detached background daemon with a living PID.
- Heartbeats every 10s updating `last_heartbeat` and `expires_at = now + ttl`.
- Has an ownership guard (matches `lock_id` before deletion, fail-closed on mismatch or absent keeper).
- Supports graceful shutdown via sentinel file (`machine_<M>.stop`).

Commands:
```bash
python D:/Taadaa/tools/device_lock_keeper.py start --machine <N> --project "<task>" --ttl 120
python D:/Taadaa/tools/device_lock_keeper.py status --machine <N>
python D:/Taadaa/tools/device_lock_keeper.py stop --machine <N>
```
