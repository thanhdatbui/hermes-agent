# Pitfall: Consumer-local Wrappers and Canonical Navigation Error Translation

## Context
When writing consumer-local wrappers around canonical `automation_core.tiktok.account_switcher` (such as `open_profile_root` or `open_account_switcher`) to provide fallback recovery (e.g. `recover_ui_dump` on `ATX_SESSION_UNAVAILABLE`), be aware of how canonical navigation handles and translates errors.

## The Canonical Exception Path Pitfall
In canonical `automation_core.tiktok.account_switcher`:
1. `open_profile_root` loops for `attempts` (default 3).
2. On failure, it passes the caught `AccountSwitcherError` to `recover_navigation_failure(adapter, exc)`.
3. `recover_navigation_failure` only matches specific error codes:
   - `{"UI_DUMP_FAILED", "UI_DUMP_UNAVAILABLE", "uiautomator_idle_state_error", "uiautomator_null_root_node"}` -> calls `recover_ui_dump()`
   - `{"PROFILE_SUBPAGE_STUCK", "SWITCHER_STILL_OPEN"}` -> calls `_back()`
   - `{"SWITCHER_ANCHOR_AMBIGUOUS", "SWITCHER_NOT_CONFIRMED", "PROFILE_ROOT_NOT_CONFIRMED"}` -> calls `restart_profile_navigation()`
   - All other codes -> raises `AccountSwitcherError("NO_HANDLER_IMPLEMENTED", failure.code)`!
4. `open_profile_root` catches that inside `except AccountSwitcherError: pass` on non-final attempts.
5. If attempts exhaust without recovery, `open_profile_root` re-raises `last` (if it was an `AccountSwitcherError`) or wraps it in `AccountSwitcherError("PROFILE_ROOT_NOT_CONFIRMED") from last`.

## Consumer Wrapper Pattern
If a consumer-local wrapper attempts to catch only exact `exc.code == "ATX_SESSION_UNAVAILABLE"`, it will fail to intercept errors if:
- Canonical recovery wrapped/translated the code into `NO_HANDLER_IMPLEMENTED` (with `"ATX_SESSION_UNAVAILABLE"` in `str(exc)` or `exc.args`), OR
- Canonical navigation wrapped the final failure into `PROFILE_ROOT_NOT_CONFIRMED` with `exc.__cause__` holding the original `ATX_SESSION_UNAVAILABLE`.

### Recommended Check
When writing bounded recovery in consumer wrappers:
```python
def is_atx_session_unavailable(exc: Exception) -> bool:
    if not isinstance(exc, AccountSwitcherError):
        return False
    if exc.code == "ATX_SESSION_UNAVAILABLE":
        return True
    if exc.code == "NO_HANDLER_IMPLEMENTED" and "ATX_SESSION_UNAVAILABLE" in str(exc):
        return True
    cause = getattr(exc, "__cause__", None)
    if isinstance(cause, AccountSwitcherError) and cause.code == "ATX_SESSION_UNAVAILABLE":
        return True
    return False
```
This ensures bounded `recover_ui_dump()` is triggered reliably while strictly preserving fail-closed behavior for all other error codes.
