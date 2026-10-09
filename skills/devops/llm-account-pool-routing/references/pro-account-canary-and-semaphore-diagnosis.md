# Pro Account Canary: Distinguish Omni Semaphore 429 from Google Entitlement/Quota

## Trigger
When Google AI Pro accounts show quota in Omni but requests fail, do not infer Free-pool or account death. Probe the exact Pro connection and exact requested model.

## Verified diagnostic sequence
1. Read `/api/providers`; select Antigravity connections whose provider metadata says `tier: g1-pro-tier`. Record `id`, `email`, `isActive`, `testStatus`, `backoffLevel`.
2. Read `/api/usage/<connectionId>` for the same accounts. Keep both facts separate:
   - Omni metadata plan/tier (`plan: Pro`, `providerSpecificData.tier`)
   - Google's live `subscriptionInfo.currentTier` and model quota buckets.
   A mismatch such as Omni `Pro` vs Google `free-tier` is a signal to investigate, not proof of a Google ban.
3. Canary the exact model with the exact connection header:
   `x-omniroute-connection: <connectionId>`
   Never use `x-omniroute-connection-id` for this test; it may be ignored and route elsewhere.
4. Capture HTTP status, elapsed time, and raw error body. Interpretation:
   - `Semaphore timeout after 30000ms` (or the configured semaphore timeout), especially after ~30s: Omni internal account semaphore/queue saturation. It is not proof of quota exhaustion, Free-pool failure, or Google banning Pro.
   - Google body containing `RESOURCE_EXHAUSTED`, explicit quota/reset/credits language: upstream quota/rate-limit classification; preserve the raw reason.
   - 401/403 or explicit entitlement/plan denial: investigate OAuth/token/tier entitlement; do not disable or delete the account without direct evidence.
5. Repeat on a small canary set, not the whole pool, and compare after the suspected busy requests drain.

## Reporting rule
Lead with the proven failure layer and exact raw body. Do not broaden scope from Pro to Free accounts when the canary is pinned to Pro. Do not call an account dead or say Google banned Pro based only on a stale/mismatched dashboard label. State uncertainty about the tier mismatch until a direct Google entitlement response or successful/failed exact-model canary proves it.

## Routing fix target
If the raw body is Omni semaphore timeout, fix the routing path so combo `queueTimeoutMs` reaches `acquireAccountSemaphore`. A multi-account combo should spill to the next connection within its configured queue timeout (typically ~1000ms), rather than falling back to a hard 30s default. Add a focused regression test and rebuild/restart the production runtime before declaring the fix live.
