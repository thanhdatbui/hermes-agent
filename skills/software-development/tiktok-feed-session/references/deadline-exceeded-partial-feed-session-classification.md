# Feed Session Deadline Exceeded Handling & Partial Swipes Classification

## Context & Problem
During `multi-machine-feed-session` execution across the farm (up to 80-160 devices with 40 parallel workers), a device can hit the allotted time budget (`_deadline_monotonic` / `DEFAULT_DEVICE_TIMEOUT_SECONDS`) during the swipe loop or during post-swipe UI recapture (`ensure_run_plan_deadline` raising `RunPlanDeadlineExceeded`).

Previously, in both `feed_session_smoke` and `feed_swipe_smoke` (`flows/feed_swipe_smoke.py`), the `except RunPlanDeadlineExceeded as exc:` block unconditionally set:
```python
partial.details["final_status"] = "failed"
partial.details["stop_reason"] = str(exc)
result = FlowResult(ExitStatus.FAIL, str(exc), partial.details)
```
Even when the account had already verified profile, logged in, and successfully completed valid video swipes (e.g. 9 swipes on May 11).

## Impact
1. **False Positive Farm Alert**: In `multi_machine_feed_session.py`, `_send_farm_machine_alert_once` triggers whenever `child.final_status not in ("success", "degraded")`. Marking timeout as `failed` generated false alerts (`[MÁY 11] DỪNG PHIÊN: run plan max_duration_seconds exceeded before capture swipe_9_after_gemphonefarm_blind_popup attempt 1`).
2. **Abandoned Cleanup**: Because `final_status == "failed"`, `finalize_feed_session_cleanup` skipped normal post-session app cleanup (pressing HOME, stopping TikTok), leaving the device stuck on the video screen.

## Resolution
In `flows/feed_swipe_smoke.py` (`feed_session_smoke` and `feed_swipe_smoke`), check `total_swipes_completed` / `actual_swipe_count` from `_feed_swipe_partial_result`:

1. `completed >= target and target > 0`:
   - `partial.details["final_status"] = "success"`
   - `result = FlowResult(ExitStatus.SUCCESS, "feed session completed at deadline", partial.details)`
2. `0 < completed < target`:
   - `partial.details["final_status"] = "degraded"`
   - `stop_msg = f"session deadline reached after {completed}/{target} swipes completed"`
   - `result = FlowResult(ExitStatus.DEGRADED, stop_msg, partial.details)`
   - Runs post-session cleanup, releases lock cleanly, and does NOT trigger Farm Alert.
3. `completed == 0`:
   - `partial.details["final_status"] = "failed"`
   - `result = FlowResult(ExitStatus.FAIL, str(exc), partial.details)`
