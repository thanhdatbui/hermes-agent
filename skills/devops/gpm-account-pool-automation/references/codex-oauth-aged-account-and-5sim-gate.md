# Codex OAuth + 5SIM Aged-Account Gate

Reusable procedure for GPM ChatGPT profiles before paid phone verification.

## Eligibility
- Verify exact GPM v3 profile ID/name/email; reject hardcoded demo targets.
- Require an active `chatgpt-web` provider older than 48 hours and no existing Codex connection.
- A profile that required password + OTP during the current registration run is **new**, even when its GPM/provider row has an older creation timestamp.

## Pre-purchase gate
- Start the exact GPM profile and navigate OmniRoute Codex OAuth.
- Capture a fresh screenshot and inspect URL plus DOM/OCR.
- Buy a number only when the page is verified as OpenAI phone verification: `auth.openai.com` plus visible phone input/phone-verification marker.
- OCR showing `Welcome back`, `Email address`, `Continue`, or provider buttons means `BLOCKED_AT_CHATGPT_LOGIN`; do not guess or expose a password and do not buy a number.

## Pricing and bounded paid attempts
- Query 5SIM live API `/v1/guest/prices?product=openai`; use price, `rate24/rate72`, and inventory, not public “from” prices.
- Prefer Vietnam `virtual34` for the canary when its live rate is materially better than Colombia; Colombia is one bounded fallback.
- Maximum two attempts: VN then Colombia. Cancel immediately on rejection or OTP timeout; verify balance and `total_active_orders` afterward.

## Evidence and success gate
- Save screenshots before submit, after submit, after OTP entry, and final OAuth/Authorize.
- `pending=true`, callback interception, or process exit 0 is not success.
- Success requires physical UI evidence plus a real OmniRoute Codex connection ID.
- Always stop GPM in `finally`, including blocked/login/manual states.
- Keep runner targets configurable; never retain a wrong hardcoded account in `__main__`.

## Session lesson
The observed failure mode was OAuth returning to a ChatGPT “Welcome back / Email address / Continue” screen. This is a login/session blocker, not a phone-verification blocker; preserve that screenshot and stop before paid purchase.