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

## Reporting style
Be concise and evidence-led. State account health, distinguish internal from upstream failure, and name the exact routing/config issue. Never treat a stale quota card as proof of exhaustion or account death.
