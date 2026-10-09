# Follow Gate & Warmup Retention Contract

## 1. Video Gate Contract (10 Videos Minimum)
- **Rule**: Nick/account must have posted at least 10 videos (`video_count >= 10`) to perform follow actions.
- **Fail-safe**: If `video_count < 10` or is missing/`None`/malformed/negative:
  - Follow budget is set to 0.
  - Follow hook is skipped immediately with status `skipped`, reason `under-10-videos-follow-disabled`, and action `skip_follow_under_10_videos`.
- **Target Repos**:
  - `tiktok-follow`: `FollowState.session_budget()` and `follow_engine.py` candidate filtering.
  - `tiktok-luot nuoi acc`: `multi_machine_feed_session.py` follow hook check.

## 2. Warmup Retention Contract (Across Same Day)
- **Problem**: Previously, when an account exited cooldown (`is_post_cooldown_warmup`), marking a single successful follow immediately reset `fail_streak = 0`. This caused subsequent runs on that same day to immediately exit warmup mode and jump back to full budget (9-12 follows), triggering re-block.
- **Contract Specification**:
  - `mark(uid, 'followed')`: Clears `follow_failed`, `cooldown_until_at`, and failure dates, but does **NOT** zero out `fail_streak` on the same day.
  - While on the same day, `fail_streak > 0` keeps the account in `is_post_cooldown_warmup == True`, limiting follow budget to warmup tier (3-5 follows).
  - `_roll_day()`: When host calendar date changes (`budget_date != today`), if `follow_failed` is `False`, then `fail_streak` is safely reset to `0`.
