# RunPlanDeadlineExceeded Handling Contract in Feed Session Flows

## Overview
When a feed session (`feed_swipe_smoke` or `feed_session_smoke`) exceeds its allotted run plan deadline, `RunPlanDeadlineExceeded` is raised from within `_feed_session_flow`.

Previously, this unconditionally failed the session (`ExitStatus.FAIL`), causing false-alarm failures even if the session had already completed all target swipes or a substantial portion of them before hitting the deadline cutoff.

## Graceful Completion Contract
Both entrypoints (`feed_swipe_smoke` and `feed_session_smoke`) catch `RunPlanDeadlineExceeded` and inspect `ctx.config["_feed_swipe_partial_result"]`:

```python
partial = ctx.config.get("_feed_swipe_partial_result")
if isinstance(partial, FlowResult):
    completed = int(partial.details.get("total_swipes_completed") or partial.details.get("actual_swipe_count") or 0)
    target = int(partial.details.get("selected_total_videos") or partial.details.get("total_swipes_requested") or 1)
    if completed >= target and target > 0:
        partial.details["final_status"] = "success"
        partial.details["stop_reason"] = ""
        partial.details.setdefault("summary", {})["stop_reason"] = ""
        partial.details["summary"]["reason"] = "feed session completed at deadline"
        result = FlowResult(ExitStatus.SUCCESS, "feed session completed at deadline", partial.details)
    elif completed > 0:
        stop_msg = f"session deadline reached after {completed}/{target} swipes completed"
        partial.details["final_status"] = "degraded"
        partial.details["stop_reason"] = stop_msg
        partial.details.setdefault("summary", {})["stop_reason"] = stop_msg
        partial.details["summary"]["reason"] = stop_msg
        result = FlowResult(ExitStatus.DEGRADED, stop_msg, partial.details)
    else:
        partial.details["final_status"] = "failed"
        partial.details["stop_reason"] = str(exc)
        partial.details.setdefault("summary", {})["stop_reason"] = str(exc)
        partial.details["summary"]["reason"] = str(exc)
        result = FlowResult(ExitStatus.FAIL, str(exc), partial.details)
```

## Testing Pattern
When testing deadline handling:
- Mock or raise `RunPlanDeadlineExceeded`.
- Provide a `_feed_swipe_partial_result` with mock `FlowResult` containing target `details`.
- Verify:
  - `completed >= target` returns `ExitStatus.SUCCESS`.
  - `0 < completed < target` returns `ExitStatus.DEGRADED`.
  - `completed == 0` returns `ExitStatus.FAIL`.
