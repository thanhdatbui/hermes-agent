# OmniRoute nested-tier spillover

## Trigger
Use when a parent combo contains child combo references (e.g. Pro pool -> Free pool) and requests fall to the next tier while eligible targets remain in the preferred child.

## Critical distinction
- `queueDepth` is pre-cascade combo admission; it is not the account semaphore queue.
- `tryAcquire` is non-queueing admission for a selected target; it does not by itself guarantee that a nested child exhausts all targets before the parent advances.
- `accountSemaphore.acquire()` can still wait up to its configured timeout when a path bypasses or follows the wrong admission seam.
- Parent fallback and child target iteration are separate control flows.

## Evidence checklist
Before changing config or code, read live parent/child combo JSON and record:
`strategy`, `nestedComboMode`, `maxGlobalAttempts`, target count, `queueDepth`, `queueTimeoutMs`, `failoverBeforeRetry`, `maxRetries`, session stickiness, and prompt-cache affinity.

Trace only the relevant windows in `open-sse/services/combo.ts` and `open-sse/services/combo/dispatchPrelude.ts` around:
- `nestedComboMode` / `resolveComboRuntimeUnits`
- `maxGlobalAttempts`
- `handleRoundRobinCombo`
- `tryAcquireAccountSemaphore`
- `accountSemaphore.acquire`
- parent handling of combo-ref `null`/failure

A child attempt budget smaller than its eligible target count is a strong candidate for premature parent fallback. Do not infer intra-tier exhaustion from `queueDepth=0` alone; require attempt-order/decision telemetry or a focused test.

## User-specific invariant
Preserve Pro `session stickiness` and `prompt-cache affinity`. Do not replace Pro cache-aware routing with P2C merely to mask a spillover bug. Free pools may use P2C. The intended flow is: exhaust/skip unavailable Pro targets within the Pro child, then fall back to Free only after the child is actually exhausted.

## Patch contract
If runtime config cannot express the intended boundary, stop and dispatch a worker with an exact source anchor and focused regression test. Do not mutate `storage.sqlite` speculatively. Keep parent-tier and child-target budgets distinct, and verify that retries cannot reset the child budget or re-enter the first Pro target indefinitely.
