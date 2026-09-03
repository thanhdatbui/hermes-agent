# In-Feed Ad False-Positive Popup Classification and Swipe Recovery Seam

## Incident Signature
- **Alert:** `[MÁY XX] DỪNG PHIÊN` / `unexpected popup/dialog marker detected`.
- **Screen:** TikTok In-Feed interactive advertisement (e.g. "Tìm hiểu thêm", "Thêm vào giỏ hàng", "Đóng").
- **Root Cause Chain:**
  1. Broad substring match in `classifier.py` (`popup_terms` containing generic `"Đóng"` or `"Close"`).
  2. Classified as `manual-needed:popup` with reason `"popup/dialog marker present"`.
  3. `_safety_from_row()` converts this into `SAFETY_MANUAL_NEEDED`.
  4. `ManualReasonGuard` and baseline/safety checks abort the session immediately before `_swipe_recovery_on_stuck` or normal feed swipe loop is ever executed.

## Key Pitfalls & Rules
1. **Never hypothesize gesture absorption without log evidence:** Do not assume an in-feed overlay blocks touch/swipe gestures unless `log.jsonl` confirms swipe commands (`input swipe ...`) were executed and recaptured XML remained on the same video.
2. **Generic keyword matching in `popup_terms`:** Broad terms like `"Đóng"` or `"Close"` without container/dialog structural anchors (e.g. `android:id/button`, `packageinstaller`, dialog classes) will match feed ads, shopping tags, and captions, stopping feed runs unnecessarily.
3. **Execution order between Safety Guard and Recovery:** When a screen is classified as `manual-needed:*`, safety guards often fail-close the session before stuck-recovery hooks run. To allow swipe recovery, recovery logic must either precede the manual stop gate or the classifier must not over-classify benign feed elements as blocker popups.
