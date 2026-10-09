# Account Switcher Manual Row Reason Propagation & Mock Test Invariants

## Context & Root Cause

In `verify_and_switch_profile` (`python_runner/flows/feed_swipe_smoke.py`), when `_capture_profile_switcher_xml_with_add_phone_guard` detects a manual-needed screen (or missing expected account returning `switcher_manual_row` dict):

1. **Reason Propagation Rule**:
   Do NOT hardcode `switch_reason="account switcher blocked by manual-needed screen"`.
   Instead, propagate the actual reason from the detected row:
   ```python
   switch_reason=(
       switcher_manual_row.get("reason")
       or switcher_manual_row.get("safety_reason")
       or "account switcher blocked by manual-needed screen"
   )
   ```
   This ensures downstream error reporting and assertions (such as `account-switcher-missing-expected`) receive the specific diagnosis rather than a generic blocked string.

2. **Mock Test Invariants for Profile Switcher XML**:
   `_capture_profile_switcher_xml_with_add_phone_guard` and the outer switch loop can capture XML multiple times per attempt:
   - Initial capture: `profile_switcher_{attempt}`
   - If not yet detected as settled switcher: `profile_switcher_{attempt}_settled`
   - Retries over `PROFILE_SWITCH_MAX_ATTEMPTS` (attempts 1..2+)
   
   When mocking `_capture_xml_text` via `side_effect`, providing a short list (e.g., only 2-3 items) will raise `StopIteration` if the switcher logic triggers a retry or settling check. Always provide sufficient items or an iterator/function fallback for mock XML captures during switcher tests.
