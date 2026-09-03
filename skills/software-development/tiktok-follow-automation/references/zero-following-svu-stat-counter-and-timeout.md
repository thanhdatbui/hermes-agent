# Case UI-40: Zero-Following Stat Counter `id/svu` & Follow Timeout Prevention

## Context & Root Cause (Incident Máy 59 ngocanh.34589, Anchor @longtuong10)

On TikTok 46.x profile headers:
- The numeric stat counter (e.g. `0` for Following, `8` for Followers) renders with `resource-id="com.ss.android.ugc.trill:id/svu"` (`android.widget.TextView`).
- The semantic stat label (e.g. `Đã follow` / `Follower`) renders with `resource-id="com.ss.android.ugc.trill:id/svt"` (`android.widget.TextView`).
- If `_STAT_COUNTER_IDS` in `verify_follow.py` or `stat_suffixes` in `mode2_follow_followers.py::_is_zero_following_profile` omits `id/svu`, the vertical column center alignment check skips the numeric `0` counter node.
- Consequently, `_is_zero_following_profile` returns `False` on an empty Following anchor.
- `_open_following_tab` attempts to tap the inert `Đã follow` header area, fails to open a relation list, leaves `engine._last_anchor_follow_outcome = "manual"`, and triggers the full recovery ladder (UI recovery, back to feed, re-search anchor).
- Repeated anchor re-search cycles consume time until the 1200s feed watchdog triggers a `follow-timeout` farm alert.

## Prevention & Resolution Rules

1. **Comprehensive Stat Counter Suffixes**:
   Ensure `_STAT_COUNTER_IDS` in `verify_follow.py` and `_is_zero_following_profile` in `mode2_follow_followers.py` include all modern TikTok stat counter resource-ids:
   ```python
   _STAT_COUNTER_IDS = (
       "id/sdn", "id/shq", "id/svt", "id/svs", "id/suu", "id/sut", "id/svu",
   )
   stat_suffixes = tuple(_STAT_COUNTER_IDS) + ("id/sdn", "id/sug", "id/sub", "id/tv_count", "id/count")
   ```

2. **Column-Aligned Zero Following Detection**:
   In `_is_zero_following_profile`, match the `Đã follow` / `Following` label node (case-insensitive) and find the vertically aligned stat counter node (`abs(label_center_x - node_center_x) <= 45.0` and `abs(label_center_y - node_center_y) <= 120.0`) with text/desc equal to `"0"`.

3. **Outcome Marking & Clean Feed Restoration**:
   When `_is_zero_following_profile` detects 0 Following:
   - Set `engine._last_anchor_follow_outcome = "zero_following"`.
   - Restore Feed cleanly via `_back_to_feed(engine)` without triggering recovery ladder re-search.
   - Non-fatally skip to the next eligible anchor in Mode 2.
