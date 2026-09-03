# Case UI-33: Search Not Found vs Navigation Failure & Skip Semantics

## Context & Incident
When `tiktok-follow` searches for a target UID (in Mode 1 direct search or Mode 2 seed anchor search), TikTok executes the search query and displays the results tabs (`Top`, `Người dùng` / `Users`, `Video`, `Cửa hàng` / `Shop`...).

If the target UID does not exist on TikTok or returns only unrelated/approximate accounts without the exact `@uid` / `tv_aweme_id`, `_wait_search_result` times out and returns `None`.

### Anti-Pattern
Treating `_wait_search_result == None` as a generic navigation error (`nav_error` -> `return False`). This caused:
1. The runner to trigger the recovery ladder (`engine.recover_ui()`).
2. Retrying search navigation a second time and failing again.
3. Raising `MANUAL_REVIEW: search navigation fail sau ladder (lần 2)` and triggering a red Farm Alert (`GIỮ HIỆN TRƯỜNG`), halting the entire session unnecessarily.

## Solution & Pattern (Case UI-33)
1. **Differentiate `not_found` from `nav_error`:**
   - Use `_is_search_screen_or_results(xml_text)` to prove that the UI is genuinely on a TikTok search screen or search results list (verifying top search bar, search tabs, and search context without feed bottom nav).
   - If `_wait_search_result` returns `None` but `_is_search_screen_or_results` is `True`, classify the outcome as `not_found` rather than `nav_error`.

2. **Mode 1 Direct Search (`follow_one_uid` & `run_mode1`):**
   - On `not_found`, call `_back_to_feed(engine)` to restore Feed state.
   - Return `("skipped", "ID không khớp sau search (không tìm thấy @<uid> trong kết quả tìm kiếm) — bỏ qua")`.
   - Record the missing UID in `res.failed_ids` and continue to the next UID in the session queue without consuming budget or raising `MANUAL_REVIEW`.

3. **Mode 2 Seed Anchor Search (`_open_following_tab` & `run_mode2`):**
   - On `not_found`, set `engine._last_anchor_follow_outcome = "not_found"`.
   - In `run_mode2`, catch `not_found` alongside `zero_following`: safely return to Feed (`_back_to_feed`) and `continue` to the next eligible anchor in the pool.

4. **Search Screen Detection Expansion:**
   - In `_is_search_history_screen` / `_is_search_screen_or_results`, include tab labels (`Top`, `Người dùng`, `Video`, `Cửa hàng`...) to ensure `_back_to_feed` recognizes the search results interface and issues the top-left Back button to cleanly return to Feed.
