# Windows PID reuse and retained device-lock takeover

## Failure signature

A recovery runner uses `allow_takeover=True`, but returns `SKIPPED_LOCKED` although the original worker is gone. The lock PID may now belong to an unrelated Windows service. Lock metadata can still show `status=recovery` and `owner_active=true`; those fields describe the old lease and are not liveness proof.

## Diagnosis

1. Compare machine and serial lock records: `pid`, `host`, `lock_id`, `run_id`, `status`, `process_started_at`.
2. Query the current PID creation time and compare it with `process_started_at` (preferred) or lock `started_at` (legacy lock).
3. Treat a current process created after the recorded owner as PID reuse, even when the PID number matches.
4. On Windows, protected processes such as `svchost.exe` can deny `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)`. Use a bounded WMI `CreationDate` fallback. If neither WinAPI nor WMI can establish creation time and liveness is unknown, fail closed.

## Core implementation requirements

- Declare `ctypes` signatures for `OpenProcess`, `GetExitCodeProcess`, `GetProcessTimes`, and `CloseHandle`; `OpenProcess.restype` must be `ctypes.c_void_p` to avoid truncating 64-bit HANDLE values.
- `_owner_process_alive` should return immediately only for definite dead (`False`). For unknown liveness (`None`), still compare process creation time when available.
- Store `process_started_at` in every new lock.
- Legacy fallback: if current process creation is later than lock `started_at` by more than tolerance, classify the old owner as dead/reused.
- Takeover must remain atomic through `acquire_device_lock(..., allow_takeover=True)` and preserve `takeover_from` metadata.

## Regression coverage

- Current Windows process probes as alive and has a creation timestamp.
- Definite dead PID can be taken over.
- Same live process predating the lock cannot be taken over.
- Reused PID with changed creation time can be taken over.
- Unknown liveness plus known changed creation time detects reuse.
- Unknown liveness plus unavailable creation time remains locked.
- Consumer CLI threads `--takeover-lock` to `allow_takeover=True`.
- Verify the replacement owns both machine and serial locks before any device action.

## Operational sequence

`inspect locks -> verify old owner/PID reuse -> VPN readiness -> atomic takeover -> verify new lock owner -> recover/recapture -> retry exact target -> final verifier`

Do not delete the retained lock manually between verification and runner launch; that introduces a race with schedulers or other sessions.
