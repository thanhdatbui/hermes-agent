# Case UI-48: Preflight Exception & Device Lock Boundary Emits Fail-Closed FOLLOW_RESULT To Prevent Missing Follow Result

## Incident Context (Máy 6 `bch.ngc.ngc91`)
When the parent feed runner (`multi_machine_feed_session.py` -> `_run_follow_hook`) executes the standalone `follow_runner` (`follow_runner.run_follow`) as a subprocess, it captures stdout lines searching for `FOLLOW_RESULT <json>`.
If the subprocess exits before reaching `_print_result()`:
- `stdout` contains zero lines starting with `FOLLOW_RESULT`.
- The parent process marks the outcome as `missing_follow_result` with empty `reason: ""` (discarding `stderr`).
- Triggers a red Farm Alert `🚨 [FARM ALERT: MÁY N] DỪNG PHIÊN • Triệu chứng: missing_follow_result • Hiện trường: GIỮ HIỆN TRƯỜNG FOLLOW`.

## Root Cause Analysis
In `follow_runner/run_follow.py`, preflight checks (lines 413–455) enforce device-lock exclusivity and Android VPN liveness before touching the physical device.
Previously:
1. When `acquire_device_lock()` raised `DeviceLockNeedsUserDecision` and was not skipped by feed session privileges, or raised another lock exception (`DeviceLockUnavailable`, `DeviceLockTransactionError`):
   - The script printed an error to `sys.stderr` and executed `return 2`.
2. When `require_android_vpn()` failed (e.g. ADB lag, Wi-Fi disconnected, tunnel timeout, or preflight exception):
   - The outer `except Exception as exc:` caught it, printed `BLOCKED: preflight device-lock/VPN fail-closed: {exc}` to `sys.stderr`, and executed `return 2`.
3. In both cases, `_print_result()` was bypassed entirely. Because `run_follow.py` exited with code 2 without writing `FOLLOW_RESULT` to `stdout`, the parent runner classified it as `missing_follow_result`, obscuring the real failure reason.

## Architectural Contract Fix (Case UI-48)
1. **Preflight Device-Lock Guard:**
   When device-lock preflight is blocked:
   ```python
   msg = (f"BLOCKED: [device-lock] máy {args.machine} ({row.serial}) đang được "
          f"User khóa bởi {exc.owner.get('project', '?')} (pid "
          f"{exc.owner.get('pid', '?')}) — safe-skip, KHÔNG can thiệp.")
   print(msg, file=sys.stderr)
   return _print_result({
       "status": "BLOCKED",
       "reason": msg,
       "followed": [],
       "skipped": [],
       "failed_ids": [],
       "failed": True,
       "details": {"device_lock": exc.owner},
   }, args.machine)
   ```
2. **Preflight VPN & Exception Boundary:**
   When VPN preflight or any pre-engine device check fails:
   ```python
   except Exception as exc:
       msg = f"BLOCKED: preflight device-lock/VPN fail-closed: {exc}"
       print(msg, file=sys.stderr)
       return _print_result({
           "status": "BLOCKED",
           "reason": msg,
           "followed": [],
           "skipped": [],
           "failed_ids": [],
           "failed": True,
           "details": {"preflight_error": str(exc)},
       }, args.machine)
   ```
3. **Exit Code Mapping (`_result_exit_code`):**
   Ensure `_result_exit_code` returns code 2 for `CONFIG_ERROR` and `BLOCKED`, keeping CLI contract compatibility with existing test assertions while guaranteeing `FOLLOW_RESULT` is always printed to stdout.
   ```python
   def _result_exit_code(status: str, failed: bool = False) -> int:
       if status == "OK" and not failed:
           return 0
       if status == "FOLLOW_FAILED" and not failed:
           return 0
       if status in ("CONFIG_ERROR", "BLOCKED"):
           return 2
       return 1
   ```
4. **Machine Config & Canary Defaults:**
   - Add `config/machine<M>.yaml` for canary machines so execution doesn't depend on stale defaults.
   - Point `scripts/run-follow.ps1` to the incident machine and its configuration.
