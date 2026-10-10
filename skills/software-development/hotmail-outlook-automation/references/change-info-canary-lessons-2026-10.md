# Change-info Canary Lessons (2026-10)

## Canonical eligibility

For the GPM PC Hotmail security flow, select accounts that have:

- Microsoft-domain mail with a valid current password and recovery mail when Microsoft asks for proof.
- TikTok registration present in `taikhoan_dat_v2_updated .xlsx` (ID + TikTok password).
- ChatGPT registration present (Cột 12 `PASS CHATGPT`).
- No active account/IP/proxy cooldown and no prior successful entry in `changed_emails`.

Do not require Codex Dual-OAuth presence in OmniRoute or 9Router. That gate was only useful while the flow depended on Graph refresh tokens for later OTP retrieval. After the password change, old Microsoft OAuth/Graph tokens are expected to be revoked and must be cleared from Cột 9 of `gmail_clean_v2.xlsx` after success.

## Verified five-step order

1. Sign in through the GPM profile and complete recovery-email proof if shown.
2. Add Authenticator/TOTP and verify the generated code; save the secret to Cột 4 and enable the overall two-step-verification switch.
3. Change the Microsoft password. Do not write the new password or mark success if Microsoft returns a temporary-service/error response.
4. Open `#DeleteTrustedDevices`, confirm the sign-out-everywhere dialog, and capture the result.
5. Relogin in the same GPM profile with the new password, enter TOTP, accept KMSI (`Có`/`Yes`), and only then update both password workbooks/state. Clear Cột 9 at this successful-write boundary.

## Selector/interstitial lessons

- Recovery proof can render as six separate `#codeEntry-0` … `#codeEntry-5` fields; fill each box, not only the legacy single OTC input.
- Relogin TOTP can use the newer `#floatingLabelInput5` UI as well as legacy OTC selectors.
- After Microsoft redirects during submit, avoid immediate `page.content()` calls; wait for `domcontentloaded` defensively and catch navigation races.
- **MSN Redirect Race during Relogin**: Calling `/logout.srf` after `#DeleteTrustedDevices` often triggers an uncontrolled browser redirect to `https://www.msn.com/vi-vn`, which aborts `page.goto("https://login.live.com")` with `Navigation interrupted by another navigation to msn.com`. Do not navigate to `/logout.srf`; navigate directly to `https://login.live.com` with bounded retries (2-3 attempts) and verify the URL is on `login.live.com` or `account.live.com` before interacting with the form.
- **Relogin Hard Gate**: Relogin with new password + TOTP + KMSI is NOT optional or a soft warning. If relogin fails or is interrupted, the run must fail-fast and NOT commit the password to Excel or mark the account completed.
- Microsoft can show repeated Terms/OK/KMSI/Passkey interstitials. Handle the specific visible control, tolerate navigation exceptions, and include a bounded FIDO/Passkey skip fallback. Do not treat a successful process exit as proof: verify the final URL, screenshot/OCR, workbook values, cleared token, and cooldown state.

## Evidence and safety

- Capture proof screenshots at each checkpoint, including the sign-out confirmation modal and final relogin/KMSI state.
- Never put passwords, TOTP secrets, OTPs, refresh tokens, or access tokens in reports or skill files; redact them.
- Keep the 24-hour cooldown on both the observed egress IP and the proxy endpoint. A different proxy endpoint must still be checked against its actual egress IP.
