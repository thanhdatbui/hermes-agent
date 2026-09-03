# Antigravity/Gemini cooldown and anti-spam routing

Use this reference when an Antigravity/Gemini account receives `429`, quota exhaustion, or a provider reset hint and the operator needs to know whether OmniRoute will keep retrying it.

## Runtime behavior

OmniRoute has several distinct protections; do not conflate them:

1. **Persisted connection cooldown** — the account's `rate_limited_until` is written to the live SQLite state. Combo pre-dispatch checks skip the connection while the timestamp is in the future, including across later requests.
2. **Per-model lockout** — an exact provider/account/model tuple can be temporarily locked by resilience logic. This is separate from the connection cooldown and is provider/model scoped.
3. **Combo failover** — the combo can move to the next target after a transient error. `failoverBeforeRetry: true` prefers the sibling target before retrying the same target when explicitly enabled for that combo.
4. **Rate-limit limiter** — when `rateLimitProtection` is enabled, a Bottleneck limiter queues and spaces requests, learns `Retry-After`/rate-limit headers, and pauses the limiter on a `429`.

## Gemini-specific interpretation

- A plain `429` can be transient RPM/TPM throttling; do not automatically call it a daily quota exhaustion.
- A response body or header with an explicit long reset is authoritative and should be honored rather than replaced with a short synthetic retry window.
- Antigravity is treated as a per-model-quota provider, so a model/account tuple can be cooled without poisoning unrelated models/accounts.
- A quota-aware preflight budget check is a separate opt-in feature (`OMNIROUTE_QUOTA_AWARE_ROUTING=1`); do not assume it is enabled merely because cooldown routing is active.

## Current settings to inspect

Read the live management state, not a repository template:

- `GET /api/settings` or `GET /api/resilience` for `connectionCooldown`, `waitForCooldown`, `comboCooldownWait`, and request-queue values.
- `GET /api/rate-limits` for per-connection protection, queue counts, and active limiter status.
- `GET /api/combos` for the exact combo `strategy`, `maxRetries`, `maxSetRetries`, `failoverBeforeRetry`, and `queueTimeoutMs`.
- `GET /api/providers` for `rateLimitedUntil`, `testStatus`, `isActive`, `maxConcurrent`, and `rateLimitProtection`.

## Safe diagnosis

1. Correlate the upstream status/body, target connection, and `rate_limited_until`.
2. Check whether the target was skipped before dispatch on the next request; a skip is evidence of anti-spam behavior.
3. Distinguish `maxConcurrent` (simultaneous in-flight ceiling) from rate-limit protection (spacing/queue/cooldown reaction).
4. Do not reset OAuth, clear model locks, disable accounts, or restart the service solely because of a `429`.
5. If testing after a routing change, send one fresh minimal canary only; do not retry-loop.

## Pitfalls

- `Model Lockout` may be disabled by default while persisted connection cooldown and combo exhaustion handling still prevent repeated calls.
- `Rate Limit Protection` is not the only anti-spam layer; turning it off does not necessarily remove combo/account cooldown state.
- `maxRetries=0` and `maxSetRetries=0` reduce retry amplification but do not themselves prove that a cooldown was persisted.
- A connection test or quota probe is not a generation test.
- Do not infer that all four accounts are exhausted from one account's `429`; inspect per-connection state and the combo decision trace.
