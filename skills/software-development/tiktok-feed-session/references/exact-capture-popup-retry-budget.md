# Exact-Capture Ownership and Popup Retry Budget

## Overview & Failure Signature
- **Error:** `capture-invalid: ATX_SESSION_UNAVAILABLE` or timeout cascade during popup probing.
- **Root Cause:** When `_feed_session_flow` captures a step (such as `baseline` or `profile_preflight`), it already obtains an exact, authoritative `ui.xml` + screenshot. However, subsequent blind-popup checkpoints (e.g. `baseline_gemphonefarm_blind_popup` or `profile_preflight_gemphonefarm_blind_popup`) running rule probes (such as `journal_back`, `close_all_desc`) with `trying > 1` would default to `retry_after_initial_miss=True`.
- On an initial miss against the supplied XML, `_gem_blind_probe_detector` would sleep and trigger a second UI capture via `_capture_xml_text(ctx, f"{checkpoint}_{rule.name}_probe_{attempt}")`.
- If TikTok was in a loading or transitioning state (e.g., `manual-needed:loading`), this redundant second capture frequently failed or hit `ATX_SESSION_UNAVAILABLE`, masking the true initial state with a false capture exception.

## Invariant Contract
1. **Owning Boundary Passes `retry_after_initial_miss=False`:**
   - Any checkpoint called with an already-captured row containing exact XML (`initial_xml_text` / `row`) must pass `retry_after_initial_miss=False`.
   - Specifically:
     - `baseline_gemphonefarm_blind_popup`
     - `profile_preflight_gemphonefarm_blind_popup`
     - `swipe_{N}_after_gemphonefarm_blind_popup`
2. **Behavior on Initial Miss with `retry_after_initial_miss=False`:**
   - `_gem_blind_probe_detector` immediately returns `(initial_xml_text, None)`.
   - No `time.sleep()`.
   - No call to `_capture_xml_text` or ATX dump.
3. **Preserve Retries for Non-Owning Checkpoints:**
   - Checkpoints without pre-supplied exact XML (where `initial_xml_text is None`) continue to use default `retry_after_initial_miss=True`.
4. **Post-Action Recapture Remains Mandatory:**
   - When a popup detector matches and an action is executed, a fresh recapture (`_capture_step`) must still take place to verify popup dismissal.

## Regression Test Recipes
In `python_runner/tests/test_feed_swipe_smoke.py`:
- `test_non_retrying_blind_checkpoint_does_not_consume_capture_budget`: Mock `_capture_xml_text` and verify it is not called when `retry_after_initial_miss=False` and initial XML misses.
- `test_post_swipe_popup_checkpoint_does_not_retry_initial_rule_misses`: Verify `_maybe_run_gemphonefarm_blind_popup_checkpoint` threads `retry_after_initial_miss=False` through to `_run_gemphonefarm_blind_popup_checkpoint`.
