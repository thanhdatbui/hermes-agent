# Shared Gemini Flash/Pro Quota Routing

## Scope
Use this reference when Gemini Flash and Gemini Pro intentionally share one Google/Antigravity quota bucket, but OmniRoute displays a Pro-facing label or requests fail despite visible quota.

## Findings
- A label such as `Gemini 3.1 Pro High` can be the upstream display name for a shared Gemini family bucket. It is not proof of a Pro-only bucket.
- Do not fabricate a separate Flash quota when Google exposes one shared bucket. Report it as `Gemini shared family quota (Flash + Pro)`.
- `Semaphore timeout after 30000ms` means internal account concurrency saturation. It is not proof of Google quota exhaustion or account death.
- Upstream `RESOURCE_EXHAUSTED`/rate-limit 429 is a provider response, but still does not by itself prove OAuth death. Check a fresh canary and token/test status.

## Diagnosis order
1. Compare the exact request route/model (`antigravity/gemini-3.8-flash-tiered`) with the UI quota bucket label. Shared family quota may have a different upstream name.
2. Classify the fresh log: internal semaphore timeout versus upstream 429. Keep these error classes separate.
3. Verify account health independently: `isActive`, token expiry, live test status, and a fresh HTTP 200 canary. A later 200 from the same account supports temporary throttling/cooldown, not death.
4. Inspect the multi-account pool config. Set a short queue timeout (about 1 second), fail over before retry, and prevent a full account from falling into the semaphore's 30-second default.
5. Keep exhaustion scoped to the Gemini family/model bucket. Claude exhaustion must not poison Gemini eligibility; an internal semaphore timeout must not trigger a one-hour quota cooldown.

## Verifying Pool Quota Availability ("Gemini có quota lại chưa?")
- **Avoid false-negative raw chat endpoints:** Do not probe quota via `POST :20128/v1/chat/completions` without an API key (returns 401) or `POST :20129/v1/chat/completions` with un-prefixed models (defaults to OpenRouter, returning 402 Insufficient credits).
- **Inspect live provider inventory:** Query `GET http://127.0.0.1:20129/api/providers`, filter `provider == 'antigravity'`, and compute `testStatus` counts (`active` vs `expired`).
- **Target connection verification:** Check `isActive: true`, `testStatus: active`, `providerSpecificData.tier == 'g1-pro-tier'`, and `expiresIn` (seconds remaining; auto-refreshed).
- **Active probe trigger:** Execute `POST http://127.0.0.1:20129/api/providers/{id}/test` (returns HTTP 200 with `valid: true`) or `/sync-models` to verify live upstream connection rather than guessing.

## UI/telemetry contract
If Flash/Pro share one upstream window, improve the label and telemetry instead of splitting the data. Prefer:

```json
{
  "quotaScope": "family",
  "quotaFamily": "gemini",
  "displayName": "Gemini Shared — Flash + Pro",
  "rawModelBucket": "<upstream bucket>"
}
```

## UI Quota Visibility & Multi-Window Operations
- **Hide non-relevant model rows:** In OmniRoute Provider Limits dashboard, click the `visibility_off` (eye with slash) icon on unwanted rows (e.g., Claude Opus/Sonnet on Antigravity cards) to hide them. State is persisted server-side in `settings.quotaVisibility[provider].hidden` via `PATCH /api/settings`.
- **5h vs Weekly Window Tracking:**
  - 5h rolling window is fetched per-model via `retrieveUserQuota` (`% left` on model row).
  - Weekly quota is reported upstream per model family via `v1internal:retrieveUserQuotaSummary` under `Gemini Models` (shared for Flash and Pro). When weekly quota hits low/zero, countdown shifts to `Resets in Xd Yh`.
  - **Edit Cutoffs:** Use the `Edit cutoffs` button on the account card to set minimum remaining quota thresholds (`QuotaCutoffModal`), routing traffic to healthy sibling accounts before total exhaustion.

## Proactive Token Healthcheck Deactivation & Prevention
- **Root cause of unexpected deactivation (`toggle_off` + `Token expired`):** OmniRoute runs a background sweep every 60s (`src/lib/tokenHealthCheck.ts`). When Google OAuth refresh fails with unrecoverable errors (e.g. `invalid_grant` from revoked session, dead proxy, or IP block), `isUnrecoverableRefreshError()` automatically sets `isActive: false` and `testStatus: "expired"` to protect upstream routing.
- **Prevent automated deactivation:**
  - Skip proactive health check sweeps for Antigravity: set `OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS=antigravity,agy` in `.env`. Tokens will then only be refreshed reactively when real requests arrive.
  - Or disable background token health check globally: `OMNIROUTE_DISABLE_TOKEN_HEALTHCHECK=1`.
- **Restoration workflow:** Verify proxy liveness, re-authenticate or refresh token, then toggle the card switch back to active (`toggle_on`).

## Reporting style
Be concise and evidence-led. State account health, distinguish internal from upstream failure, and name the exact routing/config issue. Never treat a stale quota card as proof of exhaustion or account death.
