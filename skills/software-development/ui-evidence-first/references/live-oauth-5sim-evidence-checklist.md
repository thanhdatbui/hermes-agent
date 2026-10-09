# Live OAuth / 5SIM evidence checklist

Use for bounded live browser OAuth flows that may purchase phone verification.

## Before the first purchase

- Create a fresh run id/artifact directory; do not reuse or infer from old `codex_*.png` files.
- Start the profile and attach to the intended page.
- **OpenAI OAuth landing & authentication sequence:**
  - Detect login landing (`auth.openai.com/log-in` / "Welcome back" / "Continue with Google") and click visible Google login button before expecting Google chooser.
  - Select exact target email in Google account chooser via explicit attributes (`data-identifier`, `data-email`) rather than generic substring.
  - Check for manual blockers early: password prompts, 2FA/challenge URLs (`challenge/pwd`, `challenge/totp`), and CAPTCHAs. Capture checkpoint screenshot and fail-closed as `BLOCKED` without buying. Exclude target `add-phone` itself from blocker checks.
  - Poll up to 15s for redirect away from Google back to authenticated OpenAI session before navigating to canonical `https://auth.openai.com/add-phone`.
  - Capture `oauth_authenticated` checkpoint screenshot prior to phone DOM verification.
- Verify the exact URL and phone-verification DOM (phone input plus an expected page marker).
- Save a fresh gate screenshot and DOM/UI snapshot, including URL and selector counts.
- If the gate fails, save a fresh failure screenshot/snapshot, return a blocked result, and purchase nothing.

## Bounded order ladder

1. Attempt the requested primary country/operator once.
2. If the service rejects the number or no OTP arrives, cancel/refund immediately.
3. Use only the one explicitly authorized fallback. Never add countries/operators or retry the primary blindly.
4. Verify country prefix map covers fallback country (e.g., Colombia `CO: 57`) when formatting local numbers.
5. Redact phone, OTP, and token values in stdout and reports.

## Required final evidence

For every attempted order, record a redacted state: `no-order`, `purchased`, `cancelled`, or `finished`. Inspect the exact current run's screenshots, not directory-wide historical files. A success result requires:

- fresh pre/post-submit screenshots,
- final order state with no unintended active order,
- OmniRoute `/api/oauth/codex/poll-callback` response with a non-empty connection id,
- confirmed GPM stop from `finally`.

`pending`, missing connection id, missing fresh screenshot, or unknown order state is `BLOCKED`/`UNPROVEN`.

## Runtime-crash remediation

Only a confirmed selector/target runtime exception authorizes remediation: make one minimal patch to the same script, run `python -m py_compile <script>`, then rerun once. Do not patch or rerun for a clean logical DOM-gate failure; report the gate evidence and stop.
