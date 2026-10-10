# TikTok Benign Popup Invariant: Contact & Friend Follow Suggestions

## Policy & Invariant Rule
- **Popup Type**: `contact_follow_suggestion` (gợi ý bạn bè, danh bạ, tài khoản được đề xuất).
- **Core Invariant**: Hệ thống **CHỈ ĐÓNG / BỎ QUA** (`dismiss_not_interested_button`, `dismiss_close_x`), **TUYỆT ĐỐI KHÔNG** tự động bấm `Follow` hoặc `Follow lại` người lạ từ popup gợi ý.
- Không được trả về `pre_action="tap_follow_button"` hay `follow_target` trong `detect_contact_follow_suggestion()`.

## Files & Handlers
1. `src/automation_core/tiktok/benign_popup.py`:
   - Hàm `detect_contact_follow_suggestion(root: ET.Element)`:
     ```python
     if dismiss_target is not None:
         return BenignPopupMatch("contact_follow_suggestion", markers, dismiss_target)
     return None
     ```
2. `tests/test_tiktok_benign_popup.py`:
   - `test_contact_follow_suggestion_in_feed_card_selects_follow_back`:
     - Phải assert `match.close_element.text == "Không quan tâm"` và `action.action == "dismiss_not_interested_button"`.
   - `test_contact_follow_suggestion_modal_dialog_selects_pre_action_follow_and_close_x`:
     - Phải assert `match.pre_action is None` và `action.action == "dismiss_close_x"`.
3. `tests/test_tiktok_startup.py`:
   - Dispatcher tests khi gặp popup feed card hoặc modal dialog:
     - Feed card: `result.actions == ("dismiss_not_interested_button",)` và tapped == `["Không quan tâm"]`.
     - Dialog: 2 captures `(before, clear)`, `result.actions == ("dismiss_close_x",)` và tapped == `["Đóng"]`.

## Verification Command
```bash
pytest tests/test_tiktok_benign_popup.py tests/test_tiktok_startup.py -k "contact_follow_suggestion"
```
