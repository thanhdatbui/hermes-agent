# ChatGPT Web OAuth checkpoint triage

Use this when a pool watchdog reports a generic `Timeout bắt OAuth code` or equivalent OAuth timeout.

## Evidence-first workflow

1. Treat the reported timeout as a wrapper category, not the root cause. Inspect the per-account browser screenshot captured at the timeout and run OCR on it when visual review is unavailable.
2. Classify the actual Google/browser state before retrying:
   - **PHONE_CHECKPOINT**: asks for a phone number/SMS. Do not auto-fill or retry blindly.
   - **TOO_MANY_ATTEMPTS**: says verification is unavailable or to try again later. Stop retries and allow cooldown.
   - **CAPTCHA_CHALLENGE**: reCAPTCHA or "verify it's you" screen. Record it separately; do not label it as a clean OAuth timeout.
   - **ACCOUNT_CHOOSER / SESSION_STUCK**: still at account chooser or sign-in flow without callback. Inspect profile/session and GPM mapping before retrying.
   - **SUCCESS**: callback URL contains `code=`; only then proceed to token exchange.
3. Preserve the raw URL/screenshot and the normalized category in telemetry. The user-facing report should show the actionable category, while retaining the original error string for audit.
4. Deduplicate failures by normalized email for reporting and counts. A single account can produce multiple failure records in one run (for example, an initial timeout plus a later profile/mapping result); do not inflate the account count.
5. Separate **AMBIGUOUS_GPM_PROFILE** (mapping/data problem) from OAuth/browser failures. It needs deterministic profile disambiguation, not another OAuth attempt.

## Implementation guidance

The OAuth loop must return a specific checkpoint result when it breaks on a phone checkpoint or another known Google challenge. Do not fall through to a generic `Timeout bắt OAuth code` return. Keep category detection pure/testable where possible, and verify it with mocked page text/URL or fixture screenshots; do not use a live farm device for the focused regression test.

## Known evidence pattern

Screenshots containing phrases such as `Enter a phone number`, `Unavailable because of too many failed attempts`, or `Get a verification code ... unavailable` prove that the failure is a Google security checkpoint/cooldown, not an OmniRoute callback listener failure. A screenshot at reCAPTCHA proves a CAPTCHA branch. These states should be reported as blocked/retry-later conditions rather than repeatedly re-run.
