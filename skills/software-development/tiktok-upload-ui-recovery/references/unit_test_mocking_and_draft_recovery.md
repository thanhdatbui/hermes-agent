# TikTok Draft Resume & Profile Video Tile Testing Patterns

## 1. FakeAdapter Mocking Requirements for `_resume_draft_from_profile`
When testing draft recovery flows (`_resume_draft_from_profile` in `StateMachine`):
- The method relies on both `_tap_if_found` and `_find_ui_element` (or fallback search helpers) to inspect hierarchy states.
- If a mock `FakeAdapter` only implements `_tap_if_found` without `_find_ui_element`, `_resume_draft_from_profile` raises `AttributeError: 'FakeAdapter' object has no attribute '_find_ui_element'`, causing the test to fail.
- Always include stub or minimal matcher for `_find_ui_element(xml_text, **kwargs)` returning a mock node or `None`.

## 2. Mocking UI XML for `_profile_video_tile_records`
`StateMachine._profile_video_tile_records(xml_text)` extracts clickable video tiles but applies geometric validation:
- It computes `screen_width = max(bounds[2])` and `screen_height = max(bounds[3])`.
- It expects each tile to satisfy width heuristics (`min_width = max(160, int(cell_width * 0.65))` up to `1.35 * cell_width` where `cell_width = screen_width / 3.0`) and height heuristics (`min_height = screen_height * 0.15` to `0.55`).
- In synthetic XML fixtures:
  - You MUST include a root or outer container node defining full screen dimensions (e.g., `bounds="[0,0][1080,1920]"`), OR
  - Ensure individual tile bounding boxes conform to realistic 3-column grid width/height ratios relative to the max coordinates present in the XML. Otherwise `records` will evaluate to `[]`.

## 3. Fast Focused Pytest Execution
- Always target the specific test module (e.g. `tests/test_upload_failure_recovery.py`) rather than the entire test suite.
- Set command timeout to at least 45-60s on Windows host because rootdir scanning / module collection can take 10-15s before test execution starts.
