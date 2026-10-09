# Preflight Exception & Device Lock Boundary Emits FAIL-CLOSED FOLLOW_RESULT (Case UI-48)

## Incident Context
When a follow runner subprocess is triggered by the parent feed runner (`multi_machine_feed_session.py` -> `_run_follow_hook`), the parent parses stdout looking for `FOLLOW_RESULT <json>`.
If the child process encounters an early preflight failure (e.g. device lock conflict with an existing process, VPN connection timeout / down, or safe workbook mapping error):
- Previously, `run_follow.py` printed the error message to `stderr` and executed `return 2`.
- `stdout` contained zero lines starting with `FOLLOW_RESULT `.
- The parent process received an empty result payload and flagged `status: "missing_follow_result"`, `exit_code: 2`, `reason: ""`, triggering a false-alarm Farm Alert: `• Script: tiktok-follow: missing_follow_result` with an empty reason string.

## Root Cause Patterns
1. **Preflight Gates Exit Raw Without Structured Result**:
   - In `follow_runner/run_follow.py`, lines 413-455:
     - When `acquire_device_lock` raised `DeviceLockNeedsUserDecision` and was not skipped by feed hook allowances, code executed `return 2`.
     - When `require_android_vpn` failed or timed out, code caught `except Exception as exc:` and executed `return 2`.
     - When safe workbook mapping had no row for the target machine (`row is None`), code executed `return 2`.
   - In all three cases, `_print_result` was bypassed, leaving `stdout` completely empty.

2. **Exit Code & Payload Contract Standardization**:
   - `_result_exit_code(status, failed)` returned `1` for all failure states except `FOLLOW_FAILED` (clean exit 0).
   - Pre-engine CLI tests in `test_cli.py` expected exit code `2` for `CONFIG_ERROR` and `BLOCKED` states.

## Fix Standard (Case UI-48)
1. **Emit Structured Payload on Preflight Block**:
   ```python
   # Device lock blocked:
   msg = f"BLOCKED: [device-lock] máy {args.machine} ({row.serial}) đang được User khóa bởi {exc.owner.get('project', '?')} (pid {exc.owner.get('pid', '?')}) — safe-skip, KHÔNG can thiệp."
   print(msg, file=sys.stderr)
   return _print_result({
       "status": "BLOCKED",
       "reason": msg,
       "followed": [], "skipped": [], "failed_ids": [],
       "failed": True,
       "details": {"device_lock": exc.owner},
   }, args.machine)

   # VPN / Preflight exception:
   except Exception as exc:
       if device_lock_lease is not None and hasattr(device_lock_lease, "release"):
           try:
               device_lock_lease.release()
           except Exception:
               pass
       msg = f"BLOCKED: preflight device-lock/VPN fail-closed: {exc}"
       print(msg, file=sys.stderr)
       return _print_result({
           "status": "BLOCKED",
           "reason": msg,
           "followed": [], "skipped": [], "failed_ids": [],
           "failed": True,
           "details": {"preflight_error": str(exc)},
       }, args.machine)
   ```
2. **Exit Code Alignment**:
   - In `_result_exit_code(status, failed)`:
     ```python
     if status in ("CONFIG_ERROR", "BLOCKED"):
         return 2
     ```
   - Guarantees CLI test backward compatibility (exit code 2) while ensuring stdout contains the complete `FOLLOW_RESULT` JSON line.

3. **Per-Machine Canary Config (`config/machine<N>.yaml`) & Script Default**:
   - `config/machine<N>.yaml` must be populated with machine-specific bounds (`budget_per_session: 1`, `feed_timeout_seconds: 90`).
   - `scripts/run-follow.ps1` default parameters must match the active machine under triage.

## Verification Protocol
- Focused test suite in `follow_runner/tests/test_cli.py`:
  - `test_preflight_vpn_failure_emits_blocked_follow_result`
  - `test_preflight_device_lock_blocked_emits_blocked_follow_result`
  - `test_preflight_missing_machine_emits_config_error_follow_result`
