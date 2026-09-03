# Live OTP recovery: focus + mailbox identity gate (2026-08-12)

## What happened

- Target was STT30 / serial `ce0217126cd4bc640c`.
- Initial evidence proved TikTok was foreground in `CommonFlowActivity` with the
  numeric OTP markers. The shell `uiautomator dump` did not produce a usable file,
  so focus/activity plus screenshot were the authoritative initial evidence.
- Outlook was opened in Chrome and a real vertical pull-to-refresh was performed.
  The newest TikTok row was selected using visible row order/time evidence; the
  reader recorded `time_evidence=Y` and `reason=newest-first DOM row with time token`.
- A critical identity failure surfaced: `_open_outlook_inbox_verified` can accept
  an Outlook inbox after URL/session checks while the visible Microsoft surface
  belongs to a different mailbox or login context. A URL containing
  `outlook.live.com/mail` is not proof that the target Hotmail account is active.
- Mailbox handoff also changed/lost TikTok focus. The expected OTP activity was no
  longer foreground, and Recents/Gmail/Play Store overlays interfered. There was
  no explicit post-submit `otp-enter`/accepted proof. The safe result was
  `FINAL_BLOCKED` with `OTP_INPUT_UNVERIFIED`, not a claim of success.

## Durable procedure

1. Capture TikTok focus/activity/screenshot before opening mail.
2. Pull-refresh Outlook exactly once, then save inbox XML/screenshot.
3. Verify target mailbox identity from visible masked account evidence or a trusted
   source-row match; reject URL-only proof and any conflicting account identity.
4. Select only the newest TikTok numeric-code row using timestamp/order evidence.
   Do not scan background DOM tabs or choose the first six-digit string.
5. Save the opened-message XML/screenshot and extract only from that message.
6. Before typing, restore TikTok without clearing data or starting signup; recapture
   focus/activity/XML and require the OTP markers plus a real input node.
7. After one submit, recapture. Success requires a verified post-OTP transition or
   explicit accepted result. If focus is another app, the activity disappeared, or
   the handler emitted no accepted proof, stop as `OTP_INPUT_UNVERIFIED`.
8. Never resend or reuse a prior code merely to compensate for lost focus or
   uncertain mailbox identity. Do not enter a password without explicit scope.

## Evidence bundle

The live artifact directory was:

`C:\Users\Kibe\AppData\Local\Tiktok_Reg\live_otp_STT30_20260812_002541\`

Relevant evidence types: initial/final focus and activity dumps, before/after
screenshots, Outlook pull-refresh screenshot, selected newest-mail XML/screenshot,
reader log, final decision, and repo status. Keep OTP/password values redacted in
reports; the artifact may be access-controlled evidence, not user-facing output.
