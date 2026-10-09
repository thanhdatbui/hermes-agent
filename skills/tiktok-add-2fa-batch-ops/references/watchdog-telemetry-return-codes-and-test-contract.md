# Telemetry, Return Code Constants & Verification Contract for Night TikTok 2FA Watchdog

## 1. Context & Purpose
When orchestrating batch 2FA runs across multiple farm clusters (Kibe: 1-80, Admin: 201-280 via SSH), watchdogs must adhere to standardized return code handling, structured logging telemetry, and explicit state persistence so that external health checkers and closeout gates (OmniRoute / Sol Web) can evaluate execution health accurately.

## 2. Return Code Standardization
In `run_batch_live_2fa.py`, batch runs yield specific exit codes:
- `EXIT_SUCCESS = 0`: All targeted batches executed and completed successfully.
- `EXIT_SAFE_SKIP = 4`: All targets were safely skipped (e.g. accounts already have 2FA enabled, or ceded to another ongoing runner).
- Non-acceptable codes (`1`, etc.): Execution error, missing runner, or subprocess exception.

```python
EXIT_SUCCESS = 0
EXIT_SAFE_SKIP = 4  # All targets skipped safely or already have 2FA
ACCEPTABLE_RETURN_CODES = (EXIT_SUCCESS, EXIT_SAFE_SKIP)
```

Combined dual-cluster code resolution rule:
- If both clusters exit with acceptable return codes (`0` or `4`):
  - Result is `EXIT_SUCCESS (0)` if at least one cluster succeeded with 0.
  - Result is `EXIT_SAFE_SKIP (4)` if all clusters skipped with 4.
- If any cluster failed (`code not in (0, 4)`):
  - Result is `max(kibe_code, admin_code)` (or first non-acceptable code).

## 3. Observability & Telemetry Protocol
Watchdog telemetry must not rely solely on `sys.stdout`/`sys.stderr` prints:
1. **Logging Handler**: Use standard `logging.getLogger("night_tiktok_2fa_watchdog")` configured with timestamp format `[%(asctime)s] [%(levelname)s] %(message)s`.
2. **State Persistence**: When calling `save_state(today_str, details)`, persist structured breakdown:
   - `code`: Process return code.
   - `status`: `"success"` (code acceptable and `failed == 0`), `"partial_failure"` (code acceptable but `failed > 0`), or `"failed"`.
   - `success_count`, `failed_count`, `skip_count`.
   - `failure_reason`: Explicit message explaining why state is partial or failed (e.g., `"Runner exited with non-acceptable return code 1"` or `"{fail} target machines failed during 2FA execution"`).
   - `clusters`: Dict containing parsed breakdowns for `"kibe"` and `"admin"`.

## 4. Test Verification Suite Patterns
When authoring unit tests for such watchdogs in `tests/test_cron_night_tiktok_2fa_watchdog.py`:
1. **SSH EncodedCommand Verification**:
   - Assert `cmd[0] == "ssh"` and target host is `"admin-farm"`.
   - Extract the `-EncodedCommand` payload, decode base64, and decode `utf-16le` to verify script contents.
2. **Return Code Matrix**:
   - Test (0, 0) -> 0.
   - Test (4, 0) -> 0.
   - Test (4, 4) -> 4.
   - Test (1, 0) -> 1.
3. **Feed Runner Conflict**:
   - Mock `psutil.process_iter` with both matching cmdlines (`multi_machine_feed_session`, `run-feed-session.ps1`, `run_follow`) and benign processes to ensure accurate gating.
4. **State Persistence**:
   - Test atomic write to temporary file and verify `failure_reason` and `clusters` structure.
