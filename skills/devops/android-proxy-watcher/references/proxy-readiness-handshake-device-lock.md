# Proxy Readiness Handshake → DEVICE_LOCK_FAILED (session 2026-08-07)

## Failure surface

A workflow that gates device acquisition on proxy readiness (e.g. `tiktok_workflow`
state machine, `ACQUIRE_LOCKS`) fails with:

```
[DEVICE_LOCK_FAILED] ACQUIRE_LOCKS: Không thể acquire device lock: proxy readiness
failed for <serial>: proxy_application:ADBError:adb command timed out: ('...adb.exe',
'-s', '<serial>', 'shell', 'am', 'broadcast', '--receiver-foreground', '-a...  [TRUNCATED]
```

Chain (core, read-only diagnosis):

1. `automation_core/device_lock.py` → `wait_for_proxy_ready()` (imported from
   `automation_core/readiness.py`), called with `readiness_timeout` (default 180s)
   unless `bypass_proxy_readiness=True`.
2. `readiness.py::wait_for_proxy_ready` polls the per-serial readiness file:
   - state `proxy_failed` → raises `RuntimeError("proxy readiness failed for <serial>: <error>")`
   - state `proxy_ready` (serial + optional boot_id match) → returns proof
   - deadline → `TimeoutError("proxy readiness timed out for <serial>...")`
3. `proxy_failed` is written by the watcher after an ADB `am broadcast
   --receiver-foreground -a <proxy-app-action>` timed out (device busy/slow ADB),
   with the ADBError text in the `error` field.

## Key file: readiness state per serial

```
~/.codex/device-readiness/<sha256(serial).hexdigest()[:24]>.json
```

Payload: `{serial, state: proxy_pending|proxy_ready|proxy_failed, boot_id, updated_at, error?}`.
Read it directly (Python):

```python
import hashlib, json, os
serial = "<serial>"
p = os.path.expanduser(f"~/.codex/device-readiness/{hashlib.sha256(serial.encode()).hexdigest()[:24]}.json")
print(json.dumps(json.load(open(p, encoding='utf-8')), ensure_ascii=False, indent=1))
```

## Pitfalls

- **The error string in `report.json` / log lines is TRUNCATED** at the broadcast
  args (~200 chars). Never diagnose from the truncated string — read the readiness
  file for the serial to get the real `error` field.
- **`proxy_failed` can be transient**: the watcher retries the broadcast and flips
  the file back to `proxy_ready` a few minutes later (observed: fail 17:49 → ready
  17:51). Re-read the file before declaring a real outage.
- This is fail-closed by design: the workflow keeps the UI/device lease for
  recovery (`Workflow chưa đạt DONE; giữ nguyên UI/device lease cho recovery`).

## Retry-over-live-worker trap (the actual lesson)

After a transient `DEVICE_LOCK_FAILED`, **check for an active lock BEFORE retrying** —
the fleet/scheduler often already re-spawned a legitimate worker for the same
machine (lock `started_at` ≈ a minute after the failure). Blind retry fails-closed
again with `device lock active` and only creates a spurious fail report.

Checklist:

1. `cat ~/.codex/device-locks/machine_<N>.lock.json` — if `owner_active: true`
   and the PID is alive, a worker owns the target.
2. PID alive: `wmic process where "ProcessId=<pid>" get ProcessId,CommandLine,CreationDate`
   (note: `tasklist //FI "PID eq N"` can return empty for live processes — use wmic).
3. Process tree: a legit worker spawns parent+child with nearly identical
   CreationDate (observed: `venv-core024\Scripts\python.exe` parent + `uv python`
   child, same second). Compare lock `started_at` vs your retry start time.
4. If owned → tail the owner's log/run dir (e.g. `D:\CodexRuntime\tiktok-video\worker-m72-direct.log`,
   `runs/run_<serial>_<ts>/report.json`) to confirm progress. Do not retry.
5. Only retry when the lock is absent OR the owner PID is provably dead.
