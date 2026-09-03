# Antigravity/Gemini provider A/B diagnosis

## Trigger

Use this when a Google account works directly in Antigravity but the same account/model fails through 9Router or another local router. The key question is whether the failure is global account validation or a proxy/adapter/request-path mismatch.

## Evidence tuple

Record, with secrets redacted:

- requested model and alias;
- Hermes provider label;
- router endpoint and port;
- router upstream provider/model mapping;
- selected account/connection identifier (email may be partially redacted);
- HTTP status and exact upstream reason;
- timestamp and whether another model on the same account succeeded.

Do not infer from a generic 403 alone. `VALIDATION_REQUIRED` / `Verify your account to continue` from `cloudcode-pa.googleapis.com` is an upstream denial observed through the router. It can be model-, adapter-, connection-, entitlement-, or request-shape-specific.

## Safe A/B sequence

1. Keep the first pass read-only. Do not restart 9Router, change Hermes config, delete credentials, or mutate quota/model locks.
2. Check the 9Router server log around the failure and compare a known-successful Antigravity request. Same account + successful different Gemini request argues against a total account block, but does not prove the failing model route is healthy.
3. Find the alternative router's actual installation, shortcut, and listening port. Do not assume the port. On the Windows setup observed in this session, OmniRoute was installed at `C:\Users\Kibe\OmniRoute`, its Start Menu shortcut launched `npm run dev` with `PORT=20129`, and 9Router used `20128`. Verify current processes and ports before using those values.
4. Ensure the alternative router is isolated from 9Router; do not bind both to the same port.
5. The user performs the interactive password/OAuth login. The agent must never type passwords, OAuth codes, API keys, refresh tokens, or cookies.
6. Add the same Antigravity account through the alternative router, then send the smallest controlled Gemini request with the same model family. Record status, upstream mapping, account selection, and exact error.
7. Interpret results:
   - direct Antigravity succeeds + OmniRoute succeeds + 9Router fails: isolate 9Router adapter/mapping/request-shape/connection handling;
   - direct Antigravity succeeds + both routers fail: investigate upstream account/session/entitlement or model availability;
   - alternative router succeeds only with a different model/account: compare model mapping and account affinity before changing production;
   - all routes succeed after re-authentication: record re-auth as the fix, not “retry solved it.”

## Common pitfalls

- Do not say “the Google account is invalid” solely because a router returned `403 VALIDATION_REQUIRED`.
- Do not misroute the investigation into cron leases, farm runners, or device state when the user explicitly identifies a model/provider failure.
- OAuth token refresh success does not guarantee that Google will accept the account on every Cloud Code/Antigravity request path.
- Do not use a production model switch as the diagnostic test; use an isolated alternative router and a minimal request first.
- Do not expose validation URLs, emails, tokens, or request dumps in reports; redact them.
