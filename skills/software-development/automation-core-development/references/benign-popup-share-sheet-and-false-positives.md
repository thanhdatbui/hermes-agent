# Benign Popup False Positives & Share Sheet Dismissal

## 1. False Positives in `detect_contact_follow_suggestion`
- **Issue**: Short or conversational keywords like `"mời bạn"` in `detect_contact_follow_suggestion` (`automation_core/tiktok/benign_popup.py`) trigger false positives on LIVE room comments (e.g. *"Nhà có tiệc, mời bạn chung vui!"*) or regular video captions. Combined with a follow button on screen, the screen gets erroneously classified as a contact follow suggestion popup, causing `manual-needed:popup` fail-closed stops.
- **Rule**: Avoid broad colloquial phrases (`"mời bạn"`). Keep keyword sets strictly anchored to contact sync domain terms: `"mời bạn bè"`, `"thêm bạn bè"`, `"đồng bộ danh bạ"`.

## 2. Share Sheet / Bottom Sheet Handling (`share_sheet`)
- **Issue**: When closing friend suggestions or tapping share elements, TikTok often pops up the bottom Share sheet (`Gửi đến` / `Send to`, with `com.ss.android.ugc.trill:id/tv_title` and `Sao chép Liên kết`). Swiping up does not dismiss a native bottom sheet, causing the session to fail with `manual review required: unknown`.
- **Solution**:
  - Detect via `detect_share_sheet` in `detect_allowed_generic_popup`.
  - Action MUST be `"press_back"` (`input keyevent BACK`). Android BACK dismisses bottom sheets cleanly and returns focus to the feed.
