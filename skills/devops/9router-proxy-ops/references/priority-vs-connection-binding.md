# Priority routing is not account load balancing

## Trigger

Use this reference when a multi-account OmniRoute/Antigravity combo appears to send a burst mostly or entirely to the first account, despite showing multiple combo targets or configured `maxConcurrent` values.

## Observed failure pattern

A live combo can report:

```text
priority with nested resolution: 4 total targets
Trying model 1/4: antigravity/gemini-3.7-flash-high
```

while the completed request records still resolve to one connection. In the reproduced case, recent successful `call_logs` grouped as follows:

```text
pool-1 / connection daa143cd...: 631
pool-2: 0
pool-3: 0
pool-4: 0
```

Runtime `AUTH` lines repeatedly selected the same account even though the candidate scan listed multiple eligible accounts:

```text
active=6, eligible=6
quota-aware: 5 with quota, skipping 1 exhausted
selected account=daa143cd...
```

The exact counts and IDs are session evidence only; do not copy them as current state.

## Root-cause model

Treat routing as two potentially independent selectors:

1. **Combo selector** resolves ordered targets (`priority`, weighted, round-robin, etc.).
2. **Provider executor selector** may choose an Antigravity account again based on provider/model eligibility, quota, affinity, or forced-connection handling.

If the executor does not enforce the combo target's `connectionId`, several targets with the same provider/model can collapse onto the provider's highest-priority account. This is distinct from ordinary priority semantics.

## Evidence procedure

1. Read live state from `/api/combos`, `/api/providers`, and `/api/rate-limits`; do not trust a repository template or screenshot alone.
2. Confirm combo strategy/config and enumerate every target's label, model, provider, and `connectionId`.
3. Confirm each candidate connection's `isActive`, `testStatus`, `maxConcurrent`, `rateLimitProtection`, cooldown, and quota state.
4. Query a bounded recent window from read-only `call_logs`, grouping successful rows by `connection_id` and account. Use the final persisted connection, not `combo_step_id`, as the distribution metric.
5. Correlate with runtime `AUTH` lines: `Using antigravity account`, `selected account`, `forcedConnectionId`, `session_key`, `eligible`, and `quota-aware`.
6. Inspect the combo dispatch path and the provider executor/account-selection path. Trace whether `connectionId` survives from resolved target into the actual upstream call.
7. Run one bounded live canary only after the read-only diagnosis. Do not create a retry loop or restart blindly.

## Interpretation rules

- `priority` means earlier targets are preferred; it is not even distribution.
- `maxConcurrent` limits simultaneous in-flight work. It does not rotate requests and should not be used as proof of load balancing.
- `rateLimitProtection` spaces/queues/pauses a connection after rate-limit signals. It does not balance healthy accounts.
- A `combo_step_id` naming `model-2` is not proof that account 2 served the request; check the final `connection_id`/account and any selected-connection response header.
- `active=N` and `eligible=N` in an AUTH scan prove candidate visibility only, not dispatch.
- `session_key ... has no available affinity target` may indicate affinity lookup state, but it is not by itself proof that a request was pinned or unpinned.
- One connection's quota/cooldown state can cause legitimate skew. Rule this out before calling it a binding bug.
- **Semaphore Timeout / Stalled Concurrency Skew**: If an upstream connection experiences unreleased concurrency slots or hanging requests, OmniRoute logs `Semaphore timeout after 30000ms for antigravity:<id>`. Each attempt hangs for 30s before throwing 429 semaphore timeout, forcing combo failover to skip this account entirely and dump all subsequent load onto the next healthy downstream account.
- **Starter Quota Premature Exhaustion under Cascading Spillover**: A Free/Starter account placed at the very end of a priority combo (e.g. slot 13) can exhaust its quota (429) earlier than an active Pro account (slot 12). When slots 1–11 are exhausted, in 403 validation, or timing out on semaphores, concurrent burst requests spill over simultaneously into both slot 12 and slot 13. The Free/Starter tier caps out quickly (~50 requests) and enters quota lockout, while the high-capacity Pro account at slot 12 continues absorbing hundreds of requests until its larger quota limit is reached.

## Safe remediation boundary

Do not change strategy, disable accounts, clear OAuth, clear model locks, or restart the service solely from a screenshot or combo summary. First establish whether the intended product behavior is priority failover or actual distribution. If even distribution is required, the implementation must bind each resolved combo target to the executor-level connection selection, or use a tested account-aware round-robin mechanism. Validate with a fresh bounded request batch and persisted per-connection evidence.

## Reporting template

- **Mục đích:** determine whether pool routing distributes requests.
- **Kết quả:** strategy/config; successful request counts by final connection; executor account-selection evidence.
- **Confirmed:** what the live evidence proves.
- **Excluded:** quota/cooldown/capacity causes ruled out.
- **Unproven/blocker:** missing selected-connection header, incomplete logs, or no bounded reproduction.
- **Không làm:** OAuth reset, account disable/delete, blind restart, unrelated proxy changes.
