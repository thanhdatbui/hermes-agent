# Missing Follow Result & Unhandled Exception Boundary Contract

## Incident Context
When the parent feed runner (`multi_machine_feed_session.py` -> `_run_follow_hook`) invokes the standalone `follow_runner` (`follow_runner.run_follow`) as a subprocess, it parses stdout lines looking for `FOLLOW_RESULT <json>`.
If the child process crashes due to an unhandled exception before reaching `_print_result()`:
- Traceback is printed to stderr.
- stdout contains no valid `FOLLOW_RESULT` line.
- The parent process flags the execution as `missing_follow_result`, triggering a Farm Alert `• Script: tiktok-follow: missing_follow_result`.

## Root Cause Patterns

### 1. Unguarded `self.state` Access in `follow_engine.py`
`FollowEngine.__init__` accepts `state: FollowState | None`. When `run_session()` executes without state or when state is None:
- In `run_session()`, checking `if self.state.follow_failed or res.follow_failed:` raises `AttributeError: 'NoneType' object has no attribute 'follow_failed'`.
- **Rule**: All state property access in `FollowEngine` MUST use null-safe checking: `if (self.state is not None and self.state.follow_failed) or res.follow_failed:`.

### 2. Missing Generic Exception Boundary in CLI Entrypoint (`run_follow.py`)
In `run_follow.py`:
- `engine.run_session()` was previously only wrapped in `except ConfigError:`.
- If an unhandled exception (`AttributeError`, `FollowAdapterError`, `KeyError`, etc.) occurred inside `run_session`:
  - `result` variable was never assigned.
  - In `finally: result = cleanup_after_result(adapter, result)`, `UnboundLocalError` was raised.
  - The process exited abruptly with nonzero return code and zero stdout payload.
- **Rule**:
  1. Initialize `result = None` before the `try` block.
  2. Catch `except Exception as exc:` to capture unexpected crashes, log the traceback via `logger.exception`, and populate a fail-closed `SessionResult(status="MANUAL_REVIEW", failed=True, reason=f"UNHANDLED_EXCEPTION: {type(exc).__name__}: {exc}")`.
  3. This guarantees `_print_result(result, machine)` is ALWAYS executed, emitting a structured `FOLLOW_RESULT` JSON payload to stdout so the parent process receives a deterministic error rather than `missing_follow_result`.

### 3. Early Preflight Gate Exits in CLI Entrypoint (`run_follow.py`)
In `run_follow.py`, before `engine.run_session()` is reached, early preflight gates check:
1. Missing machine in workbook (`row is None`).
2. Device lock conflicts (`DeviceLockNeedsUserDecision` when another process holds the lock and not skip-eligible).
3. VPN check failures (`require_android_vpn`) or generic preflight exceptions.
- **Anti-Pattern**: Previously, these branches printed error messages to `sys.stderr` and immediately did `return 2`. As a result, `stdout` contained zero lines of `FOLLOW_RESULT`, causing the parent feed session (`multi_machine_feed_session.py` -> `_run_follow_hook`) to flag `missing_follow_result` and fire a red `GIỮ HIỆN TRƯỜNG FOLLOW` alert.
- **Rule**:
  1. Early preflight exits MUST emit a structured `FOLLOW_RESULT` via `_print_result()` before returning exit code 2:
     - `row is None` -> `_print_result({"status": "CONFIG_ERROR", "failed": True, "reason": msg}, machine)`.
     - `DeviceLockNeedsUserDecision` -> `_print_result({"status": "BLOCKED", "failed": True, "reason": msg, "details": {"device_lock": exc.owner}}, machine)`.
     - VPN/generic preflight error -> `_print_result({"status": "BLOCKED", "failed": True, "reason": msg, "details": {"preflight_error": str(exc)}}, machine)`.
  2. `_result_exit_code()` MUST map both `"CONFIG_ERROR"` and `"BLOCKED"` to exit code `2` (distinct from execution failure exit code `1` and clean exit code `0`).


## Verification & Canary Protocol
1. **Unit tests**:
   - Test `run_session` with `state=None` runs cleanly without `AttributeError`.
   - Test `run_follow.main` with a simulated exception in `run_session` emits a fail-closed `FOLLOW_RESULT` payload with exit code 1.
2. **Full test suite**: Run `PYTHONPATH=. pytest follow_runner/tests`.
3. **Live Canary**: Execute `python -m follow_runner.run_follow --machine <M> --config <config.yaml> --account-row-index <slot>` and verify stdout contains `FOLLOW_RESULT {"status": "OK", ...}` with exit code 0.
