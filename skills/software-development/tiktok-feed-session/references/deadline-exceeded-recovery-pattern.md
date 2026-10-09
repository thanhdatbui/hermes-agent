# RunPlanDeadlineExceeded Graceful Recovery Pattern

## Context & Problem
In `multi-machine-feed-session` and `feed-session-smoke`, individual machine feeds run under an outer deadline (`_deadline_monotonic` / `_hard_deadline_monotonic`). During long sessions with multiple slow XML dumps, network delays, or post-swipe popup probes (e.g. `swipe_N_after_gemphonefarm_blind_popup`), the deadline can expire mid-swipe or during post-action capture.

Previously, both `feed_swipe_smoke` and `feed_session_smoke` caught `RunPlanDeadlineExceeded` and unconditionally marked `final_status = "failed"` with `ExitStatus.FAIL`, regardless of how many swipes had been completed. This caused false-positive Farm Alerts (`🚨 [MÁY N] DỪNG PHIÊN: run plan max_duration_seconds exceeded...`) even when the account had successfully and cleanly completed multiple valid swipes (e.g. 9 swipes on Máy 11).

## Graceful Completion Architecture

Inside both `feed_swipe_smoke` and `feed_session_smoke` in `flows/feed_swipe_smoke.py`:
When `RunPlanDeadlineExceeded` is caught:
1. Inspect `partial = ctx.config.get("_feed_swipe_partial_result")`.
2. Extract:
   - `completed = int(partial.details.get("total_swipes_completed") or partial.details.get("actual_swipe_count") or 0)`
   - `target = int(partial.details.get("selected_total_videos") or partial.details.get("total_swipes_requested") or 1)`
3. Evaluate outcome:
   - **`completed >= target and target > 0`**:
     - `final_status = "success"`
     - `result = FlowResult(ExitStatus.SUCCESS, "feed session completed at deadline", partial.details)`
   - **`0 < completed < target`**:
     - `final_status = "degraded"`
     - `stop_msg = f"session deadline reached after {completed}/{target} swipes completed"`
     - `result = FlowResult(ExitStatus.DEGRADED, stop_msg, partial.details)`
     - This allows `multi_machine_feed_session` to treat the machine as `degraded` (acceptable), run full cleanup (pressing HOME, closing app, releasing locks), and avoid firing false Farm Alerts.
   - **`completed == 0`**:
     - `final_status = "failed"`
     - `result = FlowResult(ExitStatus.FAIL, str(exc), partial.details)` (genuine failure before any valid swipes).

## Unit Testing
- Test suite: `python_runner/tests/test_feed_swipe_smoke.py`
- Test cases:
  - `test_feed_session_smoke_deadline_exceeded_writes_failed_summary_and_cleans_up` (0 swipes -> `ExitStatus.FAIL`)
  - `test_feed_session_smoke_deadline_exceeded_with_partial_swipes_returns_degraded` (5/10 swipes -> `ExitStatus.DEGRADED`)
- Command: `pytest python_runner/tests/test_feed_swipe_smoke.py -k "deadline" -v` (< 2s)
