# In-Feed Friend Suggestion Card ("Bạn bè với..." / "Follow lại") Handling

## Incident Analysis (Machine 54 - 2026-08-24)
- **Symptom:** Session stopped with `manual-needed:popup` / `unexpected popup/dialog marker detected` on feed video with an in-feed suggestion card ("Bạn bè với...", username "Bích Ngọc Ngọc", buttons "Không quan tâm" & "Follow lại").
- **Root Cause Chain:**
  1. `repost_sheet_close` in `GEMPHONEFARM_BLIND_POPUP_RULES` matched `resource-id="...:id/title"` of the creator name, falsely believing a "Bài đăng lại" sheet was open and failing to find a close-X button.
  2. `follow_back_suggestion` rule used `contains(@text, "Người mà bạn có thể biết")`, which was ignored by `find_by_gem_xpath` (exact matching only) and did not match the card's "Bạn bè với..." text.
  3. `detect_contact_follow_suggestion` classified the screen as `manual-needed:popup` due to "Bạn bè", "Follow lại", and "Không quan tâm", but modal dismissal failed because in-feed cards lack modal X controls.
- **Operator Policy & Handling:**
  - In-feed suggestion cards with `Follow lại` are part of ordinary video feed content.
  - When encountering these in-feed cards on feed (`For You` / `Đề xuất`), tap the `Follow lại` button directly (or swipe past) to resolve the card and maintain natural feed browsing without stopping the session.
  - Fix `repost_sheet_close` XPath to strictly require exact `text="Bài đăng lại"` to avoid false-positive matches on creator titles (`:id/title`).
