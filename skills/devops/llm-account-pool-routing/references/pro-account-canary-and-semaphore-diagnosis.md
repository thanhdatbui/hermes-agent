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
   Use minimal token payload: `model: 'antigravity/gemini-3.8-flash-tiered'`, `messages: [{"role": "user", "content": "1"}]`, `max_tokens: 1`.
4. Capture HTTP status, elapsed time, and raw error body. Interpretation:
   - `Semaphore timeout after 30000ms` (or the configured semaphore timeout), especially after ~30s: Omni internal account semaphore/queue saturation. It is not proof of quota exhaustion, Free-pool failure, or Google banning Pro.
   - Google body containing `RESOURCE_EXHAUSTED`, explicit quota/reset/credits language: upstream quota/rate-limit classification; preserve the raw reason.
   - 401/403 or explicit entitlement/plan denial: investigate OAuth/token/tier entitlement; do not disable or delete the account without direct evidence.
5. Batch execution discipline for full-pool audits (Harness Timeout Safety):
   - Inference latency per account is ~3.5s - 6.5s. Probing 20+ accounts sequentially in a single command takes >80s and triggers harness/terminal timeout (exit code 124 at 60s cap).
   - Divide the pool into batches of 4-5 accounts per probe call (`timeout: 35s`).
   - Use `print(..., flush=True)` so results stream in real time and pinpoint hanging accounts immediately.
6. Pool Triage: Distinguish Pro from Disabled Non-Pro Accounts:
   - When inspecting `provider_connections` where `is_active = 0`, verify tier before reporting "locked accounts".
   - Disabled accounts are typically `standard-tier` (`VALIDATION_REQUIRED`) or `free-tier` (`401 / unrecoverable_refresh_error`), NOT `g1-pro-tier`. Pro accounts remain active and isolated from standard-tier identity locks.

## Reporting rule
Lead with the proven failure layer and exact raw body. Do not broaden scope from Pro to Free accounts when the canary is pinned to Pro. Do not call an account dead or say Google banned Pro based only on a stale/mismatched dashboard label. State uncertainty about the tier mismatch until a direct Google entitlement response or successful/failed exact-model canary proves it.

## Quota Dashboard Count Drop Triage (Pro Downgrade vs Account Deletion)
When the user reports a drop in Pro account count on OmniRoute dashboard (e.g. 22 down to 21):
1. **Never infer account deletion or ban**: OmniRoute rarely deletes accounts on its own. Accounts change status or tier.
2. **Fast Diff Identification**:
   - Compare the combo membership (e.g. `ag-gemini-pool-3` models in `/api/combos`) or historical baseline against current active Pro connections (`tier: 'g1-pro-tier'` from `/api/providers`).
   - The missing account will almost always be found under `tier: 'free-tier'` / `plan: 'Antigravity starter quota'` in `provider_connections`.
3. **Inspect Upstream Entitlement**:
   - Query `GET /api/usage/<connectionId>`.
   - Check `subscriptionInfo.paidTier`: if `id: "free-tier"` and message states `"This account is ineligible for higher rate limits through a Google AI plan at this time."`, Google upstream has downgraded the account (subscription expired, card billing failed, or Google One AI plan was cancelled/refunded).
   - The dashboard filter `Pro` excludes it automatically because OmniRoute sync updates the card to `Starter`.
4. **Combo Hygiene & Operational Impact**:
   - OmniRoute does NOT automatically evict downgraded accounts from combo model lists (`combos.data.models`).
   - The downgraded account remains in the pool and can still accept requests (using starter quota), but has no Pro rate limits (1,500 req/day), risking premature 429s for the pool.
   - Action: User must either renew Google One AI on that account or operator must prune its connection ID from the Pro combo to maintain pool quality.

## Routing fix target
If the raw body is Omni semaphore timeout, fix the routing path so combo `queueTimeoutMs` reaches `acquireAccountSemaphore`. A multi-account combo should spill to the next connection within its configured queue timeout (typically ~1000ms), rather than falling back to a hard 30s default. Add a focused regression test and rebuild/restart the production runtime before declaring the fix live.
