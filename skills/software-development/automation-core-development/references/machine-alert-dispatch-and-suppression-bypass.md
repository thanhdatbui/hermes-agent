# Farm Machine Alert Dispatch & Suppression Bypass Rules

## Context & Architecture
`send_farm_machine_alert` in `automation_core.alerts` handles dispatching alerts (banner screencap + Telegram alert) when a farm machine encounters an error during feed/upload/follow/reg workflows.

## Alert Suppression Mechanism
To prevent alert storms during batch operations, immediate machine alerts are suppressed by default when running in batch aggregation mode:
- Controlled by `_should_suppress_immediate_machine_alert()`
- Checks environment variable `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT` (default: suppressed if unset, '0', or 'false')

## Missing Account Bypass Rule
Critical exceptions must bypass suppression even when `_should_suppress_immediate_machine_alert()` returns True:
- **Missing Account Errors:**
  Any error reason containing:
  - `account-switcher-missing-expected`
  - `account_missing`
  - `account-missing`
  - `thiếu nick`
  - `mất nick`
  - `account missing`
- **Rationale:** If an account is missing from a machine's account switcher, automated batch runs cannot proceed with that account, and manual intervention or immediate triage is required. Delaying or aggregating these alerts leaves devices idle or stuck.

## Test Verification
When updating `automation_core.alerts`, verify with:
```bash
pytest D:/Taadaa/automation-core/tests/test_alerts.py
```
Ensure test coverage includes:
- Suppression when env var is unset and error is generic (`test_send_farm_machine_alert_suppressed_when_env_unset`)
- No suppression when `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT=1` (`test_send_farm_machine_alert_not_suppressed_when_env_is_1`)
- No suppression when missing account keywords appear regardless of suppression setting (`test_send_farm_machine_alert_not_suppressed_when_account_missing`)
