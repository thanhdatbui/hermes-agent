# Captcha Puzzle Dismiss Contract and verify-bar-close Distinction

## Overview
In `automation_core.tiktok.benign_popup`, captcha puzzles and injected/banner overlays both may interact with elements named `verify-bar-close`.

## Distinction Invariant
1. **Banner Close (`verify-bar-close` wide)**:
   - When `verify-bar-close` spans across the screen (e.g. `elem_w >= 0.5 * right_max`), it is a GemPhoneFarm/TikTok injected banner bar.
   - It does NOT dismiss the captcha puzzle itself and must be excluded from `_find_captcha_puzzle_close_x`.
   - If no valid puzzle X is present, `detect_tiktok_popup_action` will fall back or fail closed (`restart_app`).

2. **Captcha Puzzle X (`verify-bar-close` compact)**:
   - On certain webview / captcha challenge dialogs, the top-right X button within the captcha box also carries `resource-id="verify-bar-close"` but has compact dimensions (e.g. bounds `[867,559][972,664]`).
   - When bounded in the top-right quadrant (`in_top_right`) and compact (`elem_w < 0.5 * right_max`), it represents the genuine puzzle close X.

## Action Enum Contract
- For `captcha_puzzle`, `_dismiss_action("captcha_puzzle")` returns `"dismiss_close_x"`, NOT `"tap"`.
- When writing unit tests verifying `detect_tiktok_popup_action(root)` for `captcha_puzzle`:
  ```python
  match = detect_tiktok_popup_action(root)
  assert match is not None
  assert match.popup_type == "captcha_puzzle"
  assert match.action == "dismiss_close_x"  # Standard action for close X dismissals
  assert match.close_element.resource_id == "verify-bar-close"
  ```
