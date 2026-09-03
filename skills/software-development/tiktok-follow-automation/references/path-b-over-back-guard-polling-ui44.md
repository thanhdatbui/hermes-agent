# Case UI-44: Path B Over-Back Guard with Polling & Profile-Verified Retry

**Incident:** Farm Alert Machine 10, `anhtruong840`, `MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)`

**Root Cause:** In `mode2_follow_followers.py` `_path_b_verify`, after successful profile verify:
1. Initial `adapter.back()` to return to follower list
2. RecyclerView render lag → `_on_follower_list` returns `False` on first dump
3. Old retry loop (`for attempt in range(3)`) issued secondary back blindly
4. Double-back cascaded: Profile → Follower List → Search Results (anchor `trinh.trinh.dinh`)
5. Subsequent dumps all failed → returned `manual` → `MANUAL_REVIEW`

**Fix Applied (D:\Taadaa\tiktok-follow\follow_runner\flows\mode2_follow_followers.py):**

1. **Polling for render lag:** After initial back, poll 2 times (1.5s, 1.0s) waiting for `_on_follower_list` to become True before any retry.

2. **Over-Back Guard (CRITICAL):** Only issue retry back if BOTH conditions proven by UI dump:
   - `_find_header_handle_node(restore_nodes, uid)[0] is not None` (still on target profile)
   - `not _is_search_history_screen(restore_nodes)` (not stranded on Search Results)
   
   If screen exited profile → never issue secondary back → fail-closed to `manual`.

3. **Extended selectors:**
   - `_find_top_left_back_button`: added resource-id suffixes `bq3`..`bq6`, `action_bar_back`, `img_back`; content-desc/text variants `Trở lại`, `Close`, `Đóng`
   - `_is_search_history_screen`: added `id/c0c`, `Recent searches`, `Xem thêm`, `Xóa tất cả`

4. **Session timeout guards:** Added `has_time_for_next_action(reserve_seconds=60.0)` checks in Mode 2 loops (anchor, scroll, row) and Mode 1 UID loop.

**Tests Added (test_mode2_follow_followers.py):**
- `test_path_b_verify_skips_retry_back_when_on_search_results_preventing_over_back`: Verifies exactly 1 back call, 0 retry back when UI is on Search Results
- `test_path_b_verify_delayed_follower_list_render_polls_twice_without_retry_back`: Verifies polling recovers without retry back

**Verification:**
- Plan-review: **APPROVED** (9Router `plan-review` model)
- Unit tests: **186/186 passed** (test_mode2_follow_followers.py), **499/499** full suite
- Live canary Machine 10: 600s+ run, `followed: 93`, `skipped: 2`, `failed: 0`, `follow_failed: false` — no `Path B fail` recurrence
- Git: committed as `03ce89f`, pushed to `origin/master`, SHA verified

**Anti-Pattern:** Blind retry navigation without screen-state proof. Always verify current UI context before issuing a back action in recovery flows.

**Related References:**
- `path-b-restore-over-back-prevention.md` (Case UI-41, predecessor)
- `follower-surface-transient-recovery.md`
- `search-history-back-recovery-and-home-tab.md` (search screen detection)