# Antigravity pool account addition

Use this when a Google Antigravity account is already authenticated in OmniRoute but a Gemini combo does not yet include it.

## Safe sequence

1. Read the live management state from `/api/providers` and `/api/combos`; identify the exact connection ID by account name and verify `provider=antigravity`, `isActive=true`, and `testStatus=active`.
2. Inspect account tier from `providerSpecificData`:
   - **Google AI Pro / Business / Antigravity (Restricted)**: `maxConcurrent: 8`, `rateLimitProtection: true`. Placed in active priority slots (`pool-1` .. `pool-N`). Note: Google OAuth returns `subscriptionTier: 'Antigravity (Restricted)'` / `plan: 'Business'` for workspace/non-One accounts with Antigravity grant.
   - **Starter Quota (Free)**: `maxConcurrent: 3`, `rateLimitProtection: true`. Placed at the end of combo target list as Deep Standby (`pool-N (starter-quota)`).
3. Align connection settings via management API:
   - Concurrency: `PATCH /api/providers/<id>` with `{"maxConcurrent": 8}` (or 3 for Starter).
   - Rate limit protection: `POST /api/rate-limits` with `{"connectionId": "<id>", "enabled": true}` (direct provider PATCH rejects this field).
4. Update the existing combo via `PUT /api/combos/<id>`: preserve current `strategy`, `config`, and existing model targets. Append new targets using `antigravity/gemini-3.7-flash-high`, the new connection IDs, and pool labels (`pool-14`, etc.).
5. Read back provider and combo state. Confirm all targets are present, active, and have the intended concurrency and rate-limit settings.
6. Send one fresh, minimal non-cached generation through `POST /v1/chat/completions` with `model: "combo/ag-gemini-pool-3"`. Accept the change only if the request returns HTTP 200 with valid completion output.

## Evidence to report

- New connection: sanitized account label, active/test status, `maxConcurrent`, rate-limit protection.
- Combo: name, strategy, preserved runtime config, target count, new pool label, model family.
- Canary: exact live listener, HTTP status, resolved model if exposed, completion text, usage fields.
- Mutations not performed: OAuth reset, account disable/delete, proxy changes, blind restart.

## Pitfalls

- A newly added provider connection can be active yet absent from every combo.
- A 429/quota event on existing targets does not automatically mean a newly added account is in the routing pool.
- `connection-test=200` and visible quota prove connectivity/control-plane health, not generation authorization or combo membership.
- Do not use an ad-hoc `/v1/chat/completions` probe as a substitute for the required management/API path when the task is to modify routing; use it only as the final single canary after readback.
- Do not report success from the write response alone; verify with fresh GETs and one canary.
