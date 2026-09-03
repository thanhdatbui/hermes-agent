# Antigravity validation and live-generation verification

Use this reference when an Antigravity/Gemini request shows 403, especially when the dashboard says `connected`, quota is visible, or connection-test succeeds.

## Durable decision rule

A connection test, token refresh, quota read, or model catalog response is not proof that generation is authorized. Accept "working" only after one fresh minimal generation request through the exact live OmniRoute/9Router listener returns HTTP 200 and a completion/usage signal. Use a single canary; do not retry-loop.

## If generation returns 403

1. Preserve the raw upstream JSON before it is reduced to `[403]: Antigravity upstream error` or `responseBody: null` in a call log.
2. Classify the response:
   - `reason: VALIDATION_REQUIRED` / `Verify your account to continue`: extract `details[].metadata.validation_url` (or the provider's equivalent validation URL), have the operator open it in the browser signed into the affected Google account, then reconnect/test and run one fresh generation canary.
   - no validation URL: treat it as an unresolved project/auth/upstream 403; inspect the full error body for `PERMISSION_DENIED`, `SERVICE_DISABLED`, stale project, or policy signals before changing account state.
3. Do not infer that quota is exhausted from a 403, and do not ban, disable, delete, reset quota, or clear OAuth state solely from a validation/project 403.

## Port and evidence discipline

- Verify the actual listener before testing. A dashboard URL can contain a stale or neighboring port; distinguish production 9Router (`20128` in the common setup) from an OmniRoute dev/source listener (`20129` in the investigated setup) and from unrelated dashboard ports.
- Record only safe evidence: port, model ID, HTTP status, duration, completion/usage signal, and sanitized error classification. Never print tokens, API keys, or full account identifiers.
- A later successful generation supersedes earlier transient 403 evidence for current usability, but report the earlier failure separately; a later connection-test `200` alone does not.
