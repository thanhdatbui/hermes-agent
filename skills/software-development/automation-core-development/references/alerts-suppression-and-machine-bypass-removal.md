# Alerts Suppression & Machine Alert Bypass Removal

## Context & Contract
In `automation_core/alerts.py`, individual machine failure alerts are sent via `send_farm_machine_alert()`.
When running in automated batch or farm modes, immediate single-machine alerts must be suppressed so that failures are aggregated into batch/cluster summaries rather than spamming Telegram channels.

### Suppression Logic
- Controlled by `_should_suppress_immediate_machine_alert()`:
  Suppressed by default unless `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT` is explicitly set to truthy (`1`, `true`, `yes`, `on`).
- Historical Bypass (Removed):
  Earlier implementations bypassed suppression whenever `error_reason` contained account-missing keywords (`account-switcher-missing-expected`, `account_missing`, `account-missing`, `thiếu nick`, `mất nick`, `account missing`).
  This caused noisy immediate alerts during batch runs. Removing this bypass enforces that all machine failure conditions respect batch aggregation mode.

### Test Contract (`tests/test_alerts.py`)
- Tests checking missing account conditions when suppression is active must assert:
  ```python
  assert result is False
  send_text.assert_not_called()
  # or send_photo.assert_not_called()
  ```
- Tests running under immediate mode (`AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT=1` and `FORCE_TEST_ALERT_DISPATCH=1`) continue to verify successful dispatch.

## Windows Pytest Path Invariant
- Windows Python virtualenvs running under Git-Bash / MSYS do not resolve MSYS POSIX path arguments like `/d/Taadaa/...`.
- Passing `/d/Taadaa/...` to `pytest` produces:
  `ERROR: file or directory not found: /d/Taadaa/... (exit code 4)`
- **Rule**: Always pass relative paths (e.g. `tests/test_alerts.py`) with `workdir` set to the repo root, or Windows drive-letter paths (e.g. `D:/Taadaa/...` or `D:\Taadaa\...`).
