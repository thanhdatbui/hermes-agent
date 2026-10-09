# Multi-Step Login Checkpoint Artifacts & Sequence Verification

## Core Problem
In multi-step web login flows (e.g. OpenAI login requiring Email -> Continue -> Password -> Submit, or redirecting to Google SSO), agents frequently:
1. Conclude that a redirect happened from a late error screenshot or Playwright traceback, without providing the visual proof of the preceding steps.
2. Claim that checkpoint screenshots exist after patching the code, before actually rerunning the script.
3. Fail to deliver the exact images showing the input values filled in the form before submission.

## Mandatory Step-by-Step Evidence Order
For any browser automation claim involving multi-step authentication:
1. **Checkpoint 1 (Landing):** Screenshot showing the initial landing page before any interaction.
2. **Checkpoint 2 (Pre-Submit Identifier):** Screenshot with the email/username visibly filled in the input field, BEFORE clicking Continue/Submit.
3. **Checkpoint 3 (Immediate Post-Submit / Branch Decision):** Screenshot taken <= 3 seconds after clicking Continue/Submit showing the resulting page (either the password form or an unexpected redirect to Google SSO / Cloudflare).
4. **Checkpoint 4 (Pre-Submit Secret):** If on the password page, screenshot with password field populated (or masked indicator) before submission.
5. **Checkpoint 5 (Terminal Outcome):** Final authenticated home screen (no login buttons, visible profile menu) OR terminal error page.

## Validation Protocol Before Reporting
- Never cite a file path as evidence unless its existence, size > 0, and current-run timestamp are verified via filesystem inspection.
- If any required checkpoint artifact is missing on disk, state `UNPROVEN: Missing checkpoint <N> screenshot` rather than explaining the expected behavior.
- Always run WinRT OCR on the actual images to quote verbatim text before concluding which authentication path was taken.
