# Search History Back Recovery, Feed Precondition, and Home Tab Navigation

## Context: Case UI-31 (Machine 50 `hng.th.v713`)

When running Mode 2 or Mode 1 follow flows, the runner must ensure a verified Feed precondition before searching anchor seeds or UIDs. On devices running TikTok 46.x with the Samsung soft keyboard open, navigating back to Feed can fail if the Search History surface or Back icon selectors drift, or if the recovery ladder is omitted.

## 1. Home Tab Navigation vs Device Home Key
- **Home Tab in TikTok App:** Refers strictly to the in-app bottom navigation tab labeled "Trang chủ" / "Home" (`content-desc in {"Trang chủ", "Home"}` located at `y >= height * 0.85`). Tapping this navigates from Profile ("Hồ sơ") root back to the main video Feed. It does NOT invoke the Android device home key (`KEYCODE_HOME` / `press_home()`).
- **Sluggish Device Retry:** On slow devices, tapping the "Trang chủ" tab once may not immediately switch the UI state. Allow up to 2 semantic Home taps on Profile root before falling back.

## 2. Search History Screen Detection
TikTok 46.x displays search autocomplete/history cards with diverse layout selectors:
- Input/Text fields: `id/ho3`, `id/tv_search_textview`, `id/search_input`, `id/et_search`, `id/et_search_kw`, or `class == "android.widget.EditText"` at header (`y < 300`).
- History card markers: `id/tvl_his`, `id/tvl_view_more`, or text in `{"Tìm kiếm", "Search", "Bạn có thể thích", "Tìm kiếm gần đây", "Lịch sử tìm kiếm", "Search history"}`.
- Absence of bottom navigation: `not has_bottom_nav`.

## 3. Back Icon Selector Whitelist & Prioritization
When fullscreen Search is detected, use the semantic top-left Back icon before falling back to `press_back()`, because hardware/keycode Back may only dismiss the Samsung soft keyboard:
- Suffix whitelist: `("id/bow", "id/bqp", "id/bq8", "id/bq7", "id/bq9", "id/bqc", "id/bqe", "id/bqq", "id/back_btn", "id/back", "id/btn_back", "id/iv_back", "id/left_icon", "id/action_bar_left_action")` or `content_desc in {"Quay lại", "Back"}`.
- Spatial bounding: `_node_left_x(n) < 250 and _node_top_y(n) < 250`.
- Prioritization: Sort candidates preferring `clickable=True` first, then by Euclidean distance to `(0, 0)`.

## 4. Feed Precondition Recovery Ladder
In `run_mode2` (and across all follow flows), whenever `_back_to_feed(engine)` returns `False` before seed search or after recovery:
- Bounded recovery fallback: Call `engine.recover_ui() and _back_to_feed(engine)`.
- Fail-closed threshold: Only emit `MANUAL_REVIEW: không quay về được feed trước seed search` if the recovery ladder also fails to restore Feed.
