# Zero-Following Relation Screen Detection and Search-Retry Prevention

## Incident Context (Case UI-26 / Machine 21 `ngoc.phan39`)

When an anchor account has 0 Following:
1. Runner searches anchor and taps the "Đã follow" (Following) tab.
2. TikTok opens an empty relation list screen displaying header `Đã follow 0` and empty illustration text (without a `RecyclerView`).
3. If `_open_following_tab` only checks profile header stats (which might be scrolled off, low in the viewport, or styled differently) and does not inspect the opened relation screen, `_open_following_tab` times out or returns `False` without setting `_last_anchor_follow_outcome = "zero_following"`.
4. As a result, `run_mode2` treats the failure as a generic tab opening error and executes the recovery ladder:
   $$\text{recover\_ui()} \longrightarrow \text{\_back\_to\_feed()} \longrightarrow \text{\_open\_following\_tab(engine, uid)\text{ (attempt 2)}}$$
   This causes the runner to navigate back to Feed and search the exact same 0-Following anchor a second time, wasting quota and time.

---

## Technical Solution & Best Practices

### 1. Dual-Surface Zero-Following Detection (`_is_zero_following_screen_or_profile`)
- Check both the Profile Header stats AND the Relation Screen Tab Headers:
  - **Relation Screen Header**: Match `android:id/text1` or `FOLLOWER_TAB_RESOURCE_ID` (`id/sdn`) where text matches `r"^(follower|followers|người theo dõi|đã follow|following)(?:\s+(\d+))?$"` with count `0`.
  - Accept both `selected=True` and unselected headers, as TikTok 46.x may emit transient hierarchy states without the `selected` attribute.
  - Whitelist Vietnamese and English labels: `"đã follow"`, `"following"`, `"đang follow"`, `"đang theo dõi"`.

### 2. Polling Stability (Handling Stale Dumps After Tap)
- A single dump immediately after `tap_center` may still show the pre-tap profile or intermediate loading state.
- Require **2 consecutive zero-following observations** during polling in `_open_following_tab` before concluding `zero_following`:
  ```python
  if _is_zero_following_screen_or_profile(nodes):
      zero_following_consecutive += 1
      if zero_following_consecutive >= 2:
          engine._last_anchor_follow_outcome = "zero_following"
          return False
  else:
      zero_following_consecutive = 0
  ```
- If polling deadline expires and the final dump still proves zero-following, assign `_last_anchor_follow_outcome = "zero_following"` as fallback.

### 3. Immediate Skip in Runner Loop (`run_mode2`)
- When `_open_following_tab` returns `False` with `_last_anchor_follow_outcome == "zero_following"`:
  - Execute `_back_to_feed(engine)` (with fallback to `recover_ui() + _back_to_feed()`).
  - `continue` immediately to the next anchor UID in the session queue.
  - **Never invoke the retry ladder** for zero-following anchors.
