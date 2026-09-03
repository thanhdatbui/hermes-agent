# Follower List Profile Recovery, Bottom Cutoff & Account Alias Synchronization (Cases UI-38, UI-39, UI-40)

## 1. Case UI-38: Follower List Active Recovery from Profile Screen

### Symptom & Root Cause
In Mode 2 (`mode2_follow_followers.py`), when traversing an anchor's Following/Follower list, the UI may transiently enter a profile screen (e.g. after Path B cross-verification or if a touch event taps a username row).
Previously, when `_classify_follower_surface(nodes)` returned `"invalid"`, `run_mode2` only performed 2 passive sleep retries (`time.sleep(1.0)`). If the UI remained on the profile screen, the runner raised:
`MANUAL_REVIEW: rời khỏi màn follower list giữa chừng`
and locked the device for manual review.

Furthermore, in `_path_b_verify`, if the initial `adapter.back()` call was dropped or delayed by TikTok/system UI, the subsequent restore attempts (`for attempt in range(3):`) only dumped the UI without retrying Back navigation.

### Solution Pattern
1. **Top-Left Back Button Finder (`_find_top_left_back_button`)**:
   Locates the back icon in the top-left region (`x < 250, y < 250`) belonging to an official TikTok package (or packageless node) with resource-id matching `_SEARCH_BACK_SUFFIXES` or `content_desc`/`text` in `{"Quay lại", "Back"}`. Sorts by clickable preference and proximity to `(0, 0)`.
2. **Active Bounded Recovery (`_recover_follower_list`)**:
   Attempts up to 2 active recovery actions: tries tapping `_find_top_left_back_button(nodes)`, falling back to `engine.adapter.press_back()`. Sleeps 1.2s, re-dumps UI, and checks if surface is restored to `"populated"` or `"empty"`.
3. **Loop Integration**:
   In `run_mode2`, when `surface == "invalid"` after passive retry, calls `_recover_follower_list(engine)`. If recovery succeeds (`True`), continues the follower traversal loop seamlessly.
4. **Path B Restore Retry**:
   In `_path_b_verify`, if `attempt > 0` and not `_on_follower_list(restore_nodes)`, actively retries back navigation (tap back icon or `adapter.back()`) before re-dumping UI.

---

## 2. Case UI-39: Follower Row Bottom Cutoff & Viewport Clipping

### Symptom & Root Cause
In Mode 2 RecyclerView, the bottom-most follower row near the screen bottom (e.g. `y >= 1820..1868` on 1080x1920) is frequently partially clipped. While username and avatar nodes appear in the accessibility dump, its relationship action button (`follow_button`) is outside the viewport (`y > 1920`) and missing (`r["follow_button"] is None`).
Previously, `missing_button_rows` unconditionally marked any row without a button as a layout failure:
`MANUAL_REVIEW: follower row không có nút follow semantic`

### Solution Pattern
1. Calculate dynamic screen bottom bounds:
   `max_screen_y = max(1920, *(n['bounds'][1] + n['bounds'][3] for n in nodes if n.get('bounds')))`
   `bottom_cutoff_y = max_screen_y - 180`
2. Scope `missing_button_rows` validation to fully visible rows only:
   `r.get("cluster_y", (0, 0))[1] < bottom_cutoff_y and r.get("cluster_y", (0, 0))[0] < (bottom_cutoff_y - 70)`
3. Partially clipped bottom rows are safely skipped in the current batch and fully processed with action buttons after the next scroll.

---

## 3. Case UI-40: FollowEngine Account Alias Synchronization

### Symptom & Root Cause
When the running machine's own account appears in the anchor's follower list, TikTok does not render a relationship button (only a chevron `>`). Case UI-32 skips self-account rows, but `run_mode2` looked up `active_account` via `getattr(engine, "account_id", "")` and `getattr(engine, "active_account", "")`, while `FollowEngine` historically stored only `self.active_account_handle`. This caused `active_account` to resolve to empty `""`, falsely flagging self-account rows as missing button rows.

### Solution Pattern
1. Added `getattr(engine, "active_account_handle", "")` to the fallback chain in `run_mode2`.
2. Initialized and assigned `self.active_account` and `self.account_id` alongside `self.active_account_handle` in `FollowEngine` across all setup and switch paths.
