# ChatGPT Direct Registration: Candidate Selection and Evidence Verification

## Proven workflow

1. Query GPM Local API v3 (`/api/v3/profiles?page=1&per_page=...`) and retain the profile ID, exact profile name, Gmail, and proxy mapping.
2. Use the canonical direct-email flow in `scripts/chatgpt_gpm_direct_reg.py`; do not substitute Google SSO.
3. Candidate discovery must require all of:
   - profile name contains a `@gmail.com` account;
   - password is recoverable from the authoritative Gmail workbook;
   - the account is not already present in the ChatGPT completion state;
   - the profile is not an excluded/admin placeholder.
4. A dry run only proves candidate resolution. It does not prove account state or registration.
5. For every live attempt, preserve checkpoint screenshots and the final screenshot under `debug_screenshots/chatgpt_direct_reg/`.

## Hard success gate

Do not report `SUCCESS` from a worker log, Excel tag, exit code, or screenshot filename alone. Verify the physical final screenshot exists and is fresh, then run OCR/visual inspection on that exact file. A valid success screen must show the ChatGPT application surface and a logged-in artifact, such as the prompt composer plus profile/account identity. Typical OCR evidence from a verified result included `ChatGPT`, `Chau Ta`, and `Hôm nay bạn có tưởng gì?`.

If OCR shows login, OTP, an error, a blank page, or cannot read the target state, report `UNPROVEN`/failure and keep the account out of the completed set.

## OTP discipline

Use the newest OpenAI/ChatGPT message and read the message body, not only a Gmail list snippet. Capture the OTP-stage screenshot before submission and the post-OTP screenshot immediately after submission. Never reuse an older OTP from a prior thread/run; stale codes can produce `invalid code` even when Gmail retrieval succeeded.

## Reporting

Report compactly: profile ID, Gmail, exact status, evidence path, and one OCR quote. Distinguish `SUCCESS`, `ALREADY_LOGGED_IN`, `ALREADY_EXISTS`, `FAIL_*`, and `UNPROVEN`. Preserve the exact profile-to-Gmail mapping because duplicate Gmail names can exist on multiple GPM profiles.
