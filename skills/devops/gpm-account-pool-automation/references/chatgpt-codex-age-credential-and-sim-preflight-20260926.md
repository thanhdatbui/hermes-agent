# ChatGPT/GPM → Codex OAuth preflight (2026-09-26)

## State classification
- `ALREADY_LOGGED_IN` means an existing ChatGPT session, not a new registration.
- `FAIL_PASSWORD_NOT_FOUND` after email submit means the flow did not reach OTP; it is neither registration proof nor ban proof.
- A provider `createdAt` is useful age evidence for the session/provider, but is not an absolute account-creation timestamp. Require an independently evidenced ChatGPT session older than 48h before Codex phone verification.

## OmniRoute reconciliation
Before OAuth, verify exact GPM profile ↔ email mapping, exclude emails with an existing Codex connection, and exclude `chatgpt-web` providers marked `banned`.

## 5SIM/paid phone gate
Use the integrated 5SIM API `GET /v1/guest/prices?product=openai` to obtain live cost, `rate24`, `rate72`, and inventory; do not rely on public “from” prices. Rank cost together with delivery rate and inventory. Vietnam may beat a cheaper country as a first canary when its rate and geolocation fit are stronger.

Keep purchases single-flight and bounded. Do not buy until OAuth visibly reaches the phone-verification screen. On provider rejection or OTP timeout, cancel/refund immediately and cap fallback attempts. Capture pre-submit, post-submit, OTP, and final authorization screenshots. Success requires a real OmniRoute connection/id plus fresh final UI evidence.

## Browser password saving
A surviving cookie/session does not prove password persistence. Chrome/GPM saves a password only when its Save Password prompt is rendered and accepted. Use a shared UI-only helper for Gmail and ChatGPT; fail closed for absent prompt, wrong origin, or an existing-session flow that never submitted a password. Never write Chrome `Login Data`/DPAPI directly as an ad-hoc fallback. Require a focused mocked test and a real canary confirmation before claiming saved credentials.

## Observed provider facts
- SMSPool account `taadaa195` had `$0.00` balance and zero verifications; do not purchase there until funded.
- SMS-Activate public page states the service is closed; treat lookalike sites as untrusted.
- 5SIM API was authenticated and returned live OpenAI pools; a Vietnam pool can have a higher success rate than the cheapest Argentina/Colombia pool.
