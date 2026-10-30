# Meta / Facebook OAuth Age Verification Automation Pitfalls

## Context & Flow
When automating signup/login on Meta AI services (e.g., Muse AI, Meta Account Center) that require age verification (>18 years old):
1. **Age Verification Choices:** Meta typically offers Credit Card verification OR Social Account linking (Facebook / Instagram).
2. **User Directives:** Users strictly reject adding personal credit cards (Visa/Mastercard) and mandate linking via disposable/clone social accounts.

## Critical Pitfalls & Technical Findings

1. **Purchased Clone Accounts with 2FA Mismatch:**
   - Purchased clone accounts (e.g. from shop/suppliers) often claim "ON 2FA" with a base32 TOTP secret, but in reality have WhatsApp/SMS OTP enforced (`+216...` or similar foreign numbers) upon web login from datacenter/proxy IPs.
   - When Meta OAuth detects a new IP, it diverts to two-factor verification via WhatsApp rather than presenting the TOTP secret input box.
   - Injecting raw cookie strings (`c_user`, `xs`) from stale purchases frequently fails with `c_user=deleted` (HTTP 400 Bad Request / expired session).

2. **React Form Submission vs. Standard Native Submit:**
   - Modern Meta / Facebook login forms (`https://www.facebook.com/login`) use React state-bound handlers.
   - Calling `input.press('Enter')` or `.click()` on obscured submit elements can hang or trigger an `Invalid request` state machine error.
   - Correct approach: Use the account recovery / identify flow (`/login/identify/?ctx=recover`) by email to locate the account profile, then select "Continue with Password" to avoid the initial frontend block.

3. **reCAPTCHA Enterprise & Cross-Origin Iframes:**
   - Meta Account Center checkpoints invoke Google reCAPTCHA Enterprise inside an iframe (`#captcha-recaptcha`).
   - Clicking the checkbox triggers image tile challenges that require either automated cloud bypass or visual coordinate solving.
