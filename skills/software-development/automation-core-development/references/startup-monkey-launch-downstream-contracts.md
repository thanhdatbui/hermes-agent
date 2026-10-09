# Startup Monkey Launch and Downstream Focus Contracts

## Context
`prepare_app_for_automation` in `automation_core/startup.py` handles stopping and relaunching the target app, standardizing resolution/rotation, and polling focus verification.

## Invariants & Pitfalls

### 1. Do Not Skip Monkey Launch Pre-Check
- **Anti-pattern**: Calling `cur_pkg, cur_act = focus_reader()` before the monkey launch and short-circuiting with `status: already_foreground`.
- **Impact**: Downstream consumer unit tests (e.g. `test_device_prepare.py` in `tiktok-luot nuoi acc`) mock ADB execution and expect `monkey` commands to always be dispatched during prepare/smoke flows. Bypassing monkey breaks downstream test suites.
- **Rule**: Always execute the monkey launch command; do not skip it based on pre-existing focus.

### 2. Differentiate Command Failure vs Timeout/Exception
- **Command Failure (`launched.ok is False`)**:
  - Occurs when ADB returns a non-zero exit code (e.g. invalid package, command syntax error, execution failure).
  - Downstream tests such as `test_prepare_tiktok_launch_command_failure_stops_immediately` enforce that a command-level launch failure terminates immediately with `failed` status and **must not poll focus** (`focus_mock.assert_not_called()`).
- **Timeout / ADB Exception (`except Exception`)**:
  - Occurs when ADB times out (e.g. Samsung device load, monkey process hanging, transport delay).
  - Only in exception/timeout scenarios should recovery via foreground focus verification be attempted if configured, ensuring normal command failures are not masked by extraneous focus polling.
