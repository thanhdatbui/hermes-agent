# Obfuscated Story Composer Recovery

## Trigger

A feed-session capture is classified as `unknown TikTok state` while the exact XML shows a focused TikTok `EditText` and a Samsung/OEM IME. This commonly occurs after text entry has replaced the Story placeholder and the build exposes short or empty resource IDs.

## Evidence pattern

Treat the scene as a Story quick-reply/composer only when the same capture contains the bounded combination:

- TikTok package `com.ss.android.ugc.trill`.
- Full-screen feed/video container (the incident used `com.ss.android.ugc.trill:id/szi`).
- Exactly one focused TikTok `EditText`.
- Camera action (`Mở máy ảnh` / `Open camera`).
- Sticker/GIF action (`Mở nhãn dán, GIF và biểu tượng cảm xúc` or equivalent).
- Send action (`Gửi` / `Send`).
- A visible system IME, including Samsung `com.sec.android.inputmethod`.

Do not rely on `story_reply_input`, `story_quick_reply`, or the placeholder text: these may disappear or be obfuscated after the user types.

## Safety exclusions

Reject the structural fallback when the exact tree contains known DM/chat or comment ownership markers, including `message_input`, `chat_room`, `im_title_bar`, `im_root`, `chat_input`, `comment_list`, or `comment_container`, or comment labels such as `Thêm bình luận` / `Add a comment`.

## Recovery contract

1. Persist and inspect the exact XML and matching screenshot before acting.
2. Classify the bounded composer as an allowlisted benign Story overlay.
3. Send one `BACK` to dismiss the IME; recapture fresh XML and screenshot.
4. If the composer remains, send one more `BACK`; recapture and require the composer to be gone and a known feed state to be visible.
5. If either recapture is missing, malformed, or does not prove the postcondition, fail closed as manual-needed/UNPROVEN. Never replace this with blind swipes.

## Regression coverage

Keep both a positive fixture for the post-text-entry layout (`szi` + focused `EditText` + camera/sticker/send + Samsung IME) and a negative fixture with DM/comment ownership markers. Also exercise the two-BACK recapture path with mocked fresh XML states.
