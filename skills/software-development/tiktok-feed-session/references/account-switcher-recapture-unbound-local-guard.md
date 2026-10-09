# Account Switcher Recapture & UnboundLocalError Guard

## Context & Pitfall
In `feed_swipe_smoke.py` (`verify_and_switch_profile`):
When switching profiles on TikTok, `verify_selected_account(ctx, expected, ...)` checks if the profile matches the expected account.
If it raises `AccountSwitcherError`, a fallback recapture block examines `latest_identity` (`recaptured_xml`, `recaptured_username`, `recaptured_display_name`, etc.) to see if the profile actually switched despite missing @handle or placeholder usernames.

### The Pitfall
- If fallback logic (e.g. `if is_placeholder_candidate: ... else: ...`) is indented at the same level as `try:` instead of inside `except AccountSwitcherError:`, then whenever `verify_selected_account` succeeds without error, execution falls through to the unindented fallback block.
- Because `recaptured_xml` was only defined inside the `except` block, Python raises:
  `UnboundLocalError: cannot access local variable 'recaptured_xml' where it is not associated with a value`
- Furthermore, overwriting `verified = bool(...)` in the unindented block clobbers the `verified = True` set by successful `verify_selected_account`.

## Rules & Defenses
1. **Initialize Before Try**: Always initialize `recaptured_xml = ""` (and other fallback variables) before the `try-except` block.
2. **Keep Fallback in Except**: Ensure all fallback evaluation logic (`if is_placeholder_candidate: ... else: ...` and `selected_account_recaptured_without_handle`) remains strictly inside `except AccountSwitcherError:`.
3. **Targeted Verification**: Do NOT run the full pytest test suite across `python_runner/tests/` (over 2000+ tests that will timeout). Instead:
   - Run syntax compilation: `python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py"`
   - Run targeted test file: `pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_user_placeholder_switcher.py"`
