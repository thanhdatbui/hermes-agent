# Fast Targeted Auto-Login Recovery & Verification Invariants

## Context & Purpose
When `feed_swipe_smoke.py` encounters an account switcher mismatch or missing target account during profile preflight, it attempts auto-recovery via `_run_fast_targeted_login` (`tiktok_login_v1.py`) before falling back to full reconciliation (`reconcile_tiktok_accounts.py`).

## Critical Invariants for Closeout Gate & Code Auditor (Score >= 85)

### 1. Verification of Stdout Post-Conditions (False Positive Prevention)
- **Problem**: A subprocess returning `returncode == 0` does **not** guarantee login success. The engine may exit cleanly without logging in (e.g. account missing, premature exit, unhandled prompt).
- **Rule**: Require explicit success markers in `fast_proc.stdout`:
  ```python
  is_verified_success = (
      fast_proc.returncode == 0
      and ("SUCCESS LOGIN" in stdout_text or "success" in stdout_text.lower() or "thành công" in stdout_text.lower())
  )
  ```
- **Telemetry Disambiguation**:
  - Differentiate cleanly between process execution failure (`returncode != 0`) and unverified success (`returncode == 0` but marker missing).
  - Use distinct action names in `ctx.logger.log`:
    - `finish_fast_login` on `is_verified_success == True` with `"verified_stdout": True`
    - `fast_login_unverified_stdout_fallback_reconcile` when `fast_proc.returncode == 0 and not is_verified_success` with `"unverified_stdout": True` and `"fail_reason"`
    - `fast_login_failed_fallback_reconcile` when `fast_proc.returncode != 0`
    - `fast_login_exception_fallback_reconcile` on exception/timeout

### 2. Multi-Tier Python Environment Resolution
When executing the reconcile or recovery script, resolve the interpreter across fallbacks:
1. `ctx.config.get("reconcile_python")`
2. `DEFAULT_RECONCILE_PYTHON` (checked against `TIKTOK_RECONCILE_PYTHON`, `RECONCILE_PYTHON`, and physical disk paths for `automation` and `tiktok-reg-recovery` virtualenvs)
3. If neither exists on disk, safely fall back to `Path(sys.executable)`.

### 3. Required Test Suite Coverage for Closeout Gate
Any patch affecting recovery logic must include:
1. **Positive Test**: Fast login returncode 0 + marker present -> returns `True`, logs `finish_fast_login`.
2. **Negative / Unverified Stdout Test**:
   - `returncode == 0` with empty stdout -> returns `False`, triggers fallback, logs `unverified_stdout: True`.
   - `returncode == 0` with non-matching stdout -> returns `False`, logs `unverified_stdout: True`.
3. **Execution Failure Test**: `returncode != 0` -> returns `False`, logs failure with returncode and stderr excerpt.
4. **Timeout / Exception Fallback Test**: Subprocess timeout -> triggers exception log and falls back to reconcile.
5. **Fail-Closed Dead-Man Guard**: Repeated recovery attempt on the same missing account is strictly rejected (`_auto_login_recovered_accounts`).
6. **Interpreter Resolution Test**: Tests all env var overrides and non-existent path fallback to `sys.executable`.
