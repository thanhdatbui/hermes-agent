# Account-pool concurrency and combo verification

Use this reference when several client machines share one OmniRoute provider pool and the operator wants quota-driven account rotation without request-by-request round-robin.

## Verified distinction

- Account selection happens before the ordinary per-account semaphore on the direct-model path.
- `maxConcurrent` is read from the selected connection and then passed to the account semaphore.
- `maxConcurrent: 1` serializes requests for that selected account; it does not re-run direct-model selection or spill a queued direct request to another account.
- The default account strategy is `fill-first` unless `settings.providerStrategies[provider].fallbackStrategy` overrides it.
- `round-robin` rotates on selection by design; it is not the same as busy-aware spillover.
- Quota/cooldown/error failover excludes an unhealthy account and selects another candidate on a later attempt.
- OmniRoute v3.8.50 has a combo-specific capacity skip: concrete combo targets pinned to different `connectionId` values are checked with `isAccountSemaphoreFull(...)` before dispatch; a full target records `concurrency_cap` and the combo advances to the next target. This does not make direct model routing busy-aware.
- The chat route's process-wide heavy/structural admission runs before account/combo dispatch. `chat_admission_busy` with `reason=structure_limit` therefore proves the request was rejected before the pool could use another account; it is not evidence that a per-account cap of 2 is unsafe.

## Combo wizard boundary

The combo schema can expose useful but different controls:

- model step `connectionId` pins a step to one account;
- `queueDepth` is a pre-cascade queue control associated with round-robin behavior;
- `queueTimeoutMs` bounds combo queue waiting;
- `failoverBeforeRetry` changes failover/retry ordering;
- `concurrencyPerModel` limits combo target concurrency.

None of these fields alone means “skip a busy account and select another account” globally. OmniRoute v3.8.50 has an important combo-specific exception: before dispatching a concrete target, the combo path checks the pinned target connection with `isAccountSemaphoreFull(...)`; if it is full, it records a `concurrency_cap` skip and advances to the next ordered combo target. This requires multiple real connection-pinned targets and a request sent through the combo name; it does not change direct model routing or make normal `fill-first` globally busy-aware.

If all combo targets are at capacity, the combo has no free target and cannot assign a third request magically. The request needs an outer queue/retry policy or another available target; do not describe the combo as unlimited queueing.

## Safe verification sequence

1. Read `/api/providers` and record only sanitized fields: provider, active state, health/error state, `maxConcurrent`, and count.
2. Read `/api/resilience` and record queue concurrency and `maxWaitMs`.
3. Inspect `src/sse/services/auth.ts` around `providerOverride`, `strategy`, and account selection.
4. Inspect `open-sse/handlers/chatCore.ts` around `acquireAccountSemaphore`.
5. If two real connections exist, run two concurrent requests and correlate the selected connection IDs in sanitized Omni logs. A second request using B while A is busy is evidence of busy-aware spill; merely seeing both requests eventually succeed is not.
6. Do not create a test combo with only one live connection and call it validated. If using the wizard, keep the combo inactive/not default and verify the saved payload before any live route test.

## Preferred operator policy

For Google/Antigravity OAuth pools where the operator wants stable account usage:

- keep `fill-first`/priority behavior;
- set each account's concurrency cap conservatively, commonly `1`;
- allow quota/cooldown/error failover to move traffic after a real account-specific signal;
- do not enable round-robin or random solely to solve contention;
- if immediate spillover on busy is required, treat it as a source-level feature request requiring implementation, focused tests, rebuild, restart, and a two-account live verification.

Never edit OmniRoute SQLite runtime state directly for this change.