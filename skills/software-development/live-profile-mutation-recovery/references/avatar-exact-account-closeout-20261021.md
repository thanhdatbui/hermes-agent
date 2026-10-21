# Avatar exact-account closeout

## Lesson
A canonical avatar runner can report `FORCED_REPLACED_VERIFIED`, `Avatar=OK`, and exit 0 while the later screenshot shows another logged-in account. The runner's mechanical success must not be promoted to semantic success.

## Required evidence record

- Target: machine number, serial, Tik slot, username, display name.
- Source: exact avatar path and source-folder binding; inspect the actual image, not just its filename.
- Mutation: canonical runner command, device-lock evidence, and upload log covering push, edit profile, gallery selection, crop/save, and network completion.
- Read-back: fresh screenshot after the mutation, with OCR/UI XML proving the target username and display name on the same profile surface.
- Visual: inspect the screenshot for the intended avatar, no black frame, no Launcher/SplashActivity, no popup, and no wrong account.

## Failure classification

- `FORCED_REPLACED_VERIFIED` / workbook `Avatar=OK`: mechanical workflow success only.
- Screenshot of another account: `WRONG_ACCOUNT_EVIDENCE`; discard it and do not attach it as proof.
- Black/sleep frame, Launcher, SplashActivity, or missing username: `POST_VERIFY_INVALID`.
- Correct username plus avatar visual match: `VERIFIED_SUCCESS`.

## Recovery

If the runner force-stops TikTok to Home after upload, reacquire the device lock and use the canonical account-switcher/profile verification path. Do not assume the foreground account remains the target. If the account switcher cannot be confirmed, stop and report `FINAL_BLOCKED` with the exact screenshot/OCR/log paths rather than tapping through blindly.

## Communication

When the user already chose the avatar option, do not ask again. Keep updates concise: `state -> evidence -> blocker/next action`. Never say “verified” from an exit code alone.
