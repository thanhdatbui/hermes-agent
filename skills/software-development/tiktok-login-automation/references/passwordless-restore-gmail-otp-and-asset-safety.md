# Recovery Pattern: passwordless TikTok restore, Gmail OTP, and asset safety

## Trigger
Use this when a TikTok account was incorrectly removed from a device, the account is passwordless, and the linked Gmail remains on the Android device.

## Non-negotiable safety
- Never label an account "junk" because it is absent from the current workbook.
- An account absent from Excel is `DATA_DESYNC/UNRECORDED_ASSET`: freeze, capture/OCR, search backups/logs, and ask the User. Do not logout, clear data, remove the app, or retry destructive actions.
- Only a verified parasite account may be logged out: exact OCR username, exactly one registry owner, `owner_stt != current_stt`, and User approval. Use the technical guard before ADB.
- For live UI, acquire the device lock first, keep the lock through verification, and release only after capture-before-cleanup.

## Restore sequence
1. Read the tracking row and verify the device binding; a blank TikTok password can be a legitimate passwordless account and requires `--otp-only`.
2. Inspect the device and capture a pre-action screenshot. Wake S7 devices before UI input: `input keyevent 224 && input keyevent 82`.
3. Open the TikTok account switcher. If a One-tap / "Chào mừng bạn trở lại" entry for the target exists, select that account rather than starting a fresh login flow.
4. If TikTok shows email verification, click **Gửi lại mã** exactly once and record the request time. Use the existing Gmail helper with `not_before=<request_time>`; do not accept a stale code from an old inbox message.
5. Gmail on Samsung S7 may show the OS-update modal first. Dismiss it via the visible **Đóng** control before account switching or mailbox reads. Verify the Gmail account in the selected-account UI, not only `dumpsys account`.
6. Enter the fresh OTP through the existing login helper. On OTP timeout or ambiguous UI, stop with `FINAL_BLOCKED` and preserve artifacts; do not blindly loop.
7. Verify the exact target username in the TikTok Switcher through UI XML and screenshot. Only then report `VERIFIED_SUCCESS`; capture before force-stop/Home.

## Diagnosis from the M3 incident
- `dumpsys account` proving the Gmail exists is not sufficient: Gmail can be signed into a different selected mailbox.
- An old TikTok mail/code can be visible in the inbox while fresh-code retrieval fails. Treat the old code as stale; resend and use a timestamp gate.
- A watchdog must not hold the device lock and then invoke a child login script that also requires the same lock. Either let the child own the lock or pass an explicit supported inherited-lock contract. Never bypass the lock.
- Pause a failing watchdog after one bounded failed attempt; inspect its output/artifacts before resuming.
