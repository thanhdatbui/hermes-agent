# Handling "Không gian sự kiện" (Event Space) & Non-Standard Startup Overlays

## Problem & Root Cause
- TikTok occasionally surfaces promotional or event screens during launch or feed transitions, such as **"Không gian sự kiện"** (Event Space).
- These screens frequently trigger `manual-needed:startup-ad` ("startup ad/splash marker detected") in `python_runner/core/classifier.py` or startup checks.
- Traditional startup ad handlers in `python_runner/flows/feed_swipe_smoke.py`:
  - `_startup_ad_skip_selector` only searches for traditional skip buttons (`STARTUP_AD_SKIP_TERMS` like "Bỏ qua quảng cáo", "Skip ad") and CTA close buttons ("Đóng", "Close", "Mua ngay").
  - If not found, it falls back to `DEFAULT_SKIP_TAP_CENTER = (950, 1700)` (bottom right), which fails on "Không gian sự kiện" because this screen requires exiting via the top-left navigation back arrow (`Quay lại`, `Navigate up`, `Back`, `←`).
  - After 3 retries, the run fails with `manual-needed:startup-ad-stuck`.

## Dismissal Pattern & Implementation
1. **Target files**:
   - `python_runner/flows/feed_swipe_smoke.py` (`_find_startup_ad_skip_button`, `_startup_ad_skip_selector`, `_perform_startup_ad_skip`)
   - Alternatively / supplementary: `python_runner/flows/benign_popup_registry.py` for feed-time popup detection.

2. **Detection Logic**:
   - Detect Event Space markers in UI XML:
     ```python
     EVENT_SPACE_TERMS = ("không gian sự kiện", "event space", "khong gian su kien")
     ```
   - Identify top-left back navigation button:
     - Text or content-desc matching: `{"quay lại", "navigate up", "back", "←", "<", "quay lại màn hình trước"}`
     - Resource IDs matching: `{"btn_back", "iv_back", "back_btn", "action_bar_back", "title_bar_back", ":id/bq7"}`
     - Position bounds check: `top < int(SCREEN_HEIGHT_PX * 0.20)` and `left < int(SCREEN_WIDTH_PX * 0.40)`

3. **Selector & Action Dispatch**:
   - In `_startup_ad_skip_selector(row)`:
     ```python
     back_btn = _find_event_space_back_button(attempt)
     if back_btn and back_btn.center:
         return {
             "source": "startup-ad",
             "action": "tap_back_button",
             "text": back_btn.text,
             "content_desc": back_btn.content_desc,
             "bounds": back_btn.bounds,
             "center": back_btn.center,
         }
     ```
   - In `_perform_startup_ad_skip`:
     - Ensure `action in {"tap_skip_ad", "tap_close_ad", "tap_default_skip", "tap_back_button"}` includes `"tap_back_button"` so the tap command `["input", "tap", x, y]` executes cleanly.

4. **Turn-Budgeting in Large Flow Files**:
   - `feed_swipe_smoke.py` is >22,000 lines.
   - Do NOT run broad regex or recursive search.
   - Target lines ~5570–5850 directly for startup ad handlers.
