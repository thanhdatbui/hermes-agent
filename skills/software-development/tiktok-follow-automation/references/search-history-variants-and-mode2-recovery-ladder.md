# Search History Variants, Search Back Selectors & Mode 2 Recovery Ladder (Case UI-31)

## Overview
When navigating back to Feed before searching anchors in Mode 2 (`_back_to_feed` in `follow_runner/flows/mode2_follow_followers.py`), devices often get stuck on search history screens or profile roots if selectors drift or if 1 Home tap is insufficient on slow devices.

## Key Learnings & Architecture

1. **Search History Detection (`_is_search_history_screen`)**:
   - Modern TikTok 46.x uses various input and suggestion resource IDs: `id/ho3`, `id/search_input`, `id/et_search`, `id/tvl_his`, `id/tvl_view_more`, `id/et_search_kw`.
   - **Fail-Closed Package Gate**: All nodes must strictly match `is_tiktok_package(node.package)`. Never treat a raw `EditText` at `top_y < 300` as Search history without verifying TikTok package ownership and confirming search submit/history markers, preventing false positive triggers on foreign apps or comment input overlays.
   - Dual Search Indicator Requirement: Require both a search submit identifier (`has_search_submit`) AND a search input/history marker (`has_history_or_input`), while ensuring absence of bottom navigation (`has_bottom_nav is False`).

2. **Expanded Search Back Button Suffixes (`_SEARCH_BACK_SUFFIXES`)**:
   - Expanded list of Back button candidates: `id/bow`, `id/bqp`, `id/bq8`, `id/bq7`, `id/bq9`, `id/bqc`, `id/bqe`, `id/bqq`, `id/back_btn`, `id/back`, `id/btn_back`, `id/iv_back`, `id/left_icon`, `id/action_bar_left_action`, or `content_desc in {"Quay lại", "Back"}`.
   - Strictly filter out non-TikTok packages (`is_tiktok_package(node.package)`).
   - Prioritize clickable elements and sort by proximity to the top-left corner `(x < 250, y < 250)`.

3. **Profile Root Navigation Retries**:
   - When on Profile root with bottom nav, allow up to 2 semantic `Home` taps (`home_taps < 2`) to accommodate slow layout/render cycles before falling back to `press_back()`.

4. **Mode 2 Recovery Ladder Before Seed Search**:
   - In `run_mode2`, when `_back_to_feed(engine)` fails before seed search, execute `engine.recover_ui() and _back_to_feed(engine)` as a bounded recovery step before escalating to `MANUAL_REVIEW: không quay về được feed trước seed search`.
