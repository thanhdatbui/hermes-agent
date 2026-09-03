# Before-Swipe Launcher Focus Recovery Architecture

## Context & Problem
During TikTok feed automation (`feed_swipe_smoke.py` / `_feed_session_flow`), the app can lose focus to the system launcher or SystemUI during startup observation or after popup dismiss actions before the main swipe loop begins (`before_swipe` phase). Previously, launcher recovery was only wired into post-swipe steps and baseline, leaving `before_swipe` vulnerable to unhandled launcher focus loss failures.

## Two-Layer Recovery Architecture

### Layer 1: In-Place Startup Retry Recovery (`_capture_before_swipe_with_startup_retry`)
Inside `_capture_before_swipe_with_startup_retry`:
- When `_is_launcher_focus_loss(ctx, row)` detects launcher focus:
  1. Calls `_relaunch_and_poll_tiktok_focus(ctx, after_launch_delay_seconds=POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS)`.
  2. If relaunch succeeds, recaptures step `before_swipe_launcher_recovery_recapture` with `expected="Home/For You feed"`, `action="observe"`, `swipe_count=0`, `require_feed=True`.
  3. If recapture status is `ExitStatus.SUCCESS` or `ExitStatus.DEGRADED`, immediately returns the recaptured row.
  4. Otherwise, updates `row` and `last_row` with the recaptured state.

### Layer 2: Pre-Swipe Fallback Checkpoint (`_feed_session_flow`)
Inside `_feed_session_flow` (around line 19104), when evaluating `before.get("status") in {"failed", ExitStatus.MANUAL_NEEDED.value}`:
- Checks `if _is_launcher_focus_loss(ctx, before)`:
  1. Calls `_recover_post_swipe_launcher_focus(ctx, after=before, expected="Home/For You feed", swipe_count=0, artifact_prefix=artifact_prefix)`.
  2. If recovered (`status` in `{ExitStatus.SUCCESS.value, ExitStatus.DEGRADED.value}`):
     - `before = launcher_recovered`
     - Updates `results[-1] = before`
     - Calls `_store_partial_result(ctx, results, max_swipes, **result_kwargs)`
  3. Bypasses subsequent stuck swipe recovery and continues cleanly into the swipe loop.

## Unit Testing
- Test suite: `python_runner/tests/test_before_swipe_launcher_recovery.py`
- Command: `pytest python_runner/tests/test_before_swipe_launcher_recovery.py -v` (runs < 30s)
