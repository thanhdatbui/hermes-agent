# Case UI-41: Path B Restore Over-Back Navigation Prevention & Search Stranding

## Context & Problem
In TikTok Follow Mode 2 (`mode2_follow_followers.py`), after following a user from an anchor's follower/following list:
1. `_verify_row_after_tap` verifies that the row relationship state updated to `followed`.
2. Path B verification (`_path_b_verify`) opens the user's profile to cross-check identity and relationship status.
3. On the profile, `_path_b_verify` verifies identity and confirms `classification == "followed"`.
4. Next, `_path_b_verify` calls `adapter.back()` to restore the UI back to the follower list.
5. If the first post-back UI dump experiences transient latency (RecyclerView still re-rendering) and `_on_follower_list(restore_nodes)` evaluates to `False`, the retry loop on `attempt > 0` immediately issued another back action (`adapter.back()` or top-left back tap).
6. This secondary back over-navigates (double back), popping out of the follower list and out of the anchor profile, stranding the device on the parent Search Results screen (e.g. Tab Top for the anchor UID).
7. Stranded on Search Results, `_on_follower_list` fails all remaining checks, returning `manual` and triggering `MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)`.

## Root Cause
Blind retry back execution in `_path_b_verify`:
- The restore loop issued a secondary `adapter.back()` / back button tap whenever `_on_follower_list` was False, without checking what screen the app was currently displaying.
- If the first back already navigated out of the profile into the follower list (or an intermediate transition), a second back immediately navigated out of the follower list into Search Results.

## Remediation & Defensive Rules
1. **Settling Delay & Polling in Follower List Restore**:
   - After the initial `adapter.back()`, execute 2 dump polls (with 1.5s / 1.0s delay) to accommodate uiautomator / RecyclerView rendering latency before declaring `_on_follower_list` unproven.
2. **Strict Profile-Proven Guard for Retry Back in `_path_b_verify`**:
   - Crucially, only issue a retry back action (`tap_center(back_btn)` or `adapter.back()`) if the current screen is STILL PROVEN to be on the target Profile screen:
     `handle_node, _ = _find_header_handle_node(restore_nodes, uid)`
     `still_on_profile = handle_node is not None and not _is_search_history_screen(restore_nodes)`
   - If `still_on_profile` is False (the screen has already left the profile, e.g. `_is_search_history_screen` / Search Results, Feed, or an unproven screen), DO NOT issue another back action.
   - Fail-closed to `manual` and preserve current UI state to avoid cascading backwards through the app stack.

## Verification Checklist
1. Unit test reproducing transient post-back dump lag where follower list takes 2 polls to re-render (`test_path_b_verify_delayed_follower_list_render_polls_twice_without_retry_back`) -> proves `_path_b_verify` restores without issuing secondary back.
2. Unit test verifying that if UI lands on Search Results after back (`test_path_b_verify_skips_retry_back_when_on_search_results_preventing_over_back`), retry back is suppressed and over-navigation is prevented.
3. Unit tests for dropped back on profile with/without back button (`test_path_b_verify_retries_back_when_first_back_dropped`, `test_path_b_verify_retries_adapter_back_when_no_back_button_on_dropped_screen`) verify retry back executes only when proven on profile.
4. Focused test suite `test_mode2_follow_followers.py` passes 100% (188/188 tests).
