# In-Feed & Modal Follow Friends Suggestion Contract (Case 57)

## Contract Overview
- **In-feed suggestion cards** ("Bạn bè với...", "Follow bạn", "Gợi ý follow" with "Follow lại" & "Không quan tâm"):
  - Classified under `contact_follow_suggestion` in `automation_core.tiktok.benign_popup`.
  - Direct action: `action="tap_follow_back"`.
  - Behavior: taps "Follow lại" / "Follow" button directly without stopping or skipping feed swipe.

- **Modal dialogs** ("Follow bạn bè của bạn" / "Follow your friends" with list of suggested users and close `✕`):
  - Configured with `pre_action="tap_follow_button"` targeting a clickable Follow button under the dialog title bounds (excluding already-followed labels `"Đã follow"` / `"Following"`).
  - Main action: `action="tap_follow_back_and_close"` targeting the close button `✕` (`:id/e63`, `:id/c3t`, or semantic close control).
  - If no follow buttons remain, action falls back to `action="dismiss_close_x"`.

## Dispatcher Handling in `automation_core.tiktok.startup`
- `dismiss_tiktok_popups` handles `pre_action in {"tap_follow_button", "tap_follow_back"}`:
  1. Taps the `pre_action_element`.
  2. Recaptures UI hierarchy.
  3. Continues to the primary dismiss action (closing modal `✕`).
  4. Recaptures and verifies that the dialog is completely dismissed.
