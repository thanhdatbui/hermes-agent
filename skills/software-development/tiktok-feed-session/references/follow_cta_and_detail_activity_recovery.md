# Follow CTA & Video Detail Activity Recovery Reference

## 1. Follow CTA with Low X Bounds
- **Issue**: Buttons like "Follow lại", "Follow back", "Theo dõi lại" on video cards or recommendation sheets may start at $x_0 < 50$ (e.g. bounds `[36, 1625][840, 1757]`).
- **Fix**:
  - In `dismiss_follow_friends_suggestion_popup`, check bounds allowing $x_0 \ge 0$.
  - When `followed_count > 0` and no semantic 'X' close button exists, look for top header back button (`:id/bq7` / `Quay lại` / `Back`) or invoke `send_device_back_key(ctx)` to exit back to the main feed.

## 2. Static Video Comment Bar Disambiguation
- **Issue**: Static bottom comment placeholder on video posts (`"Thêm bình luận..."`, `com.ss.android.ugc.trill:id/eg4`) with keyboard closed and no focused input was previously misclassified as `comment_input_overlay`.
- **Fix**:
  - `detect_comment_input_overlay` requires active input evidence: either `has_focused_input`, `keyboard_detected`, or open `comment_drawer` / `comment_list` before classifying as an overlay.

## 3. Video Detail View (`DetailActivity`) Detection & Swipe Recovery
- **Issue**: When navigated to a single video post in `DetailActivity`, standard feed detection previously failed because `bottom-create` was absent.
- **Fix**:
  - `detect_feed_controls`: Allow detection when `right_rail_markers >= 2` even without `bottom-create`. Require dark contrast (`dark >= 0.04`) to prevent false positives on solid bright/ad screens.
  - `detect_startup_ad_splash`: Explicitly rejects startup ad when right-rail feed markers $\ge 2$.
  - `_swipe_recovery_on_stuck`: When stuck on `DetailActivity` or a screen with a Back button (`:id/bq7` / `Quay lại`), tap back or send `BACK` key to return to `MainActivity` / feed before resuming feed swipes.

## 4. Virtual Environment Sync
- Whenever modifying `automation-core`, sync to site-packages immediately:
  ```bash
  cp -rf src/automation_core/* "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/"
  ```
