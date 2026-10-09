# TikTok Swipe and Upload Verification Patterns

## 1. Upload Verification vs Profile Refresh

When inspecting repeated downward swipes on a device, do not assume they belong to upload verification:

- **Upload Verification (`VERIFY_POST`)**:
  - Operates after `POST` is triggered.
  - In `scripts/tiktok_workflow/post_verifier.py`, `PostVerifier.verify_post()` only polls device screenshots and checks UI markers (`post_success`, `upload_done`, `video_published`, `mute_warning`, `captcha_dialog`, `login_dialog`, `post_failed`).
  - It does NOT perform a pull-to-refresh or swipe-down action to reload the feed/profile.
- **Profile / Follow Verification**:
  - Pull-to-refresh (swiping down from near top/middle of profile) is a distinct pattern used in follow verification (e.g. `mode2_follow_followers.py` / `_reload_profile`) to bypass cached UI and ensure a follow action did not get silently reverted by TikTok backend.
- **Tile / Thumbnail Discovery**:
  - Downward swipes (scrolling down the grid) are also used when discovering video thumbnails/covers or drafts on profile surfaces.

## 2. Investigation Discipline

1. Check both `PostVerifier` and the state machine's concrete post-handling logic before asserting whether a post step reloads UI.
2. If repeated swipes appear during an alleged upload flow, check whether the state machine dropped into a fallback/recovery branch (e.g. draft resumption, avatar check, or unexpected profile navigation).
3. If deep code inspection or worker delegation times out, present the distinction honestly as unconfirmed rather than inventing or assuming a mechanism.
4. Keep the explanation direct: state clearly whether upload uses swipe reload, point out where swipe-reload actually lives, and explain that any unexplained swipe indicates an unexpected state transition or recovery attempt.
