# Vietnamese add-phone popup fix (2026-08-06)

## Symptom
`test_machine_5_vietnamese_add_phone_popup_uses_typed_close_action` failed:
`detect_tiktok_popup_action(root)` returned `None` for Vietnamese add-phone XML.

## Root cause
Core `detect_add_phone_popup` (`automation_core/tiktok/benign_popup.py:711`)
matches only English title markers:
- `"add phone"` / `"add your phone number"` (title/body)
- `"+84"` / `"vn +84"` (prefix)
- `"số điện thoại"` / `"phone number"` (input)
- `"tiếp tục"` / `"continue"` (button)
- close via `_close_candidate` (accepts `"đóng"` — VN close already OK)

The farm TikTok build renders the title as **"Thêm số điện thoại"** →
`add_phone_title_or_body` marker missing → required set incomplete → None.

## Fix (consumer-side, NO core patch)
In `python_runner/core/benign_popup.py`:

1. **`detect_add_phone_popup` wrapper** — try core first, then re-implement
   marker logic with `("thêm số điện thoại", "thêm sđt")` added to the title
   terms. Reuse core helpers `_all_values` / `_has_contains` / `_close_candidate`
   (they are re-exported into the wrapper namespace by
   `globals().update({...vars(_impl)...})` at the top of the file).
   Return `_impl.BenignPopupMatch("add_phone", markers, close)`.

2. **`detect_tiktok_popup_action` wrapper** — MUST override the dispatcher too:
   ```python
   def detect_tiktok_popup_action(root, **kwargs):
       match = detect_add_phone_popup(root)          # wrapper first
       if match is not None:
           return _impl._action_match(match)          # BenignPopupMatch -> TikTokPopupActionMatch
       return _impl.detect_tiktok_popup_action(root, **kwargs)
   ```
   Without this, the core dispatcher's hardcoded detector tuple calls the CORE
   leaf detector, never the wrapper → still None.

## Key facts
- `action.action == "dismiss_close_x"` comes from core `_dismiss_action("add_phone")`
  (map already exists in core — no consumer change needed for the action name).
- Close bounds asserted: `(936, 84, 1056, 216)` — the `Đóng` close-X button.
- English XML still matches via the core-first delegation (no regression).

## Verification
- `test_classifier.py`: 44 passed (was 43 + 1 fail before).
- `test_benign_popup.py` + `test_classifier.py` + `test_current_blocker_dismiss_smoke.py`: 142 passed, 14 skipped.
- Ad-hoc 8/8: VN detect, popup_type=add_phone, action=dismiss_close_x, bounds,
  English no-regression, pytest target passes.

## Files touched
- `python_runner/core/benign_popup.py` (+50 lines, two wrapper functions)
- `python_runner/tests/test_classifier.py` (WIP test committed earlier in
  `codex/tiktok-add-phone-vietnamese` merge, now passes)
- `docs/ui-compatibility.md` (add-phone Vietnamese popup entry)
