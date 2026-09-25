# OmniRoute nested-tier spillover

Use this reference when a parent combo must exhaust a Pro child pool before falling to Free.

## Three independent controls

1. `queueDepth`: combo pre-cascade queue; controls waiting before trying a target/tier.
2. `maxGlobalAttempts`: child traversal budget; if lower than target count, the child can return early and parent may fall to the next tier.
3. `accountSemaphore.acquire`: per-connection queue; omitted `timeoutMs` can invoke the 30s default even when combo/API config reports 1s.

Required path:

```text
full Pro target -> bounded semaphore wait -> next eligible Pro target -> Pro child exhausted -> Free child
```

## Debug checklist

- Read back SQLite and live API config.
- Confirm child attempt budget is greater than target count but bounded.
- Inspect `nestedComboMode="execute"` and timeout context reaching chat core.
- If logs still say `Semaphore timeout after 30000ms`, inspect the actual `accountSemaphore.acquire` call; config-only changes are insufficient.
- Preserve Pro cache/session affinity. Do not switch Pro to P2C with affinity disabled just to solve saturation; P2C is suitable for large Free pools.
- Verify recent logs distinguish semaphore timeout from upstream 429/403 and proxy failures.
- Add a focused test proving the timeout argument reaches acquisition.

Coordinator must not directly probe Google/OpenAI; use local runtime evidence or a worker contract.
