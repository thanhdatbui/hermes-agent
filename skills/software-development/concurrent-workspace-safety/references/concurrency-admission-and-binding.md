# Concurrency Admission and Hard Account Binding

## Failure pattern

A router can appear to have a per-account `maxConcurrent` check while still concentrating all traffic on the first priority account:

```text
check isFull(account-1) -> false
(dispatch starts later) -> acquire(account-1)
```

Under a burst, every caller can observe the same free slot before any caller increments the semaphore. The later acquire then queues excess work behind account-1 instead of spilling to account-2.

A second, independent failure occurs when the combo target carries `connectionId` but the credential selector or executor re-resolves credentials by provider/model. That silently replaces the selected lower-priority account with the globally preferred account.

## Implementation pattern

1. Keep the configured priority order; do not replace it with round-robin or random selection.
2. After cheap target skip gates pass, perform an atomic, non-queueing reservation for the target connection.
3. If reservation fails, return `null` from that target attempt so the ordered loop tries the next target.
4. Pass the reservation downstream and prevent `chatCore` from acquiring a second slot.
5. Preserve hard `connectionId` binding through combo target -> single-model handler -> credential selection -> chat core -> executor.
6. Keep the normal downstream release lifecycle for both buffered and streaming responses. If the dispatch wrapper can return or throw before downstream claims the reservation, release it there; make release idempotent.

## Required test matrix

- Primitive: cap=2 accepts two reservations, rejects the third without queueing, and accepts a replacement after release.
- Primitive: a rejected reservation leaves `queued=0`.
- Primitive: blocked/cooldown accounts reject new reservations.
- Routing: with four priority accounts and cap=5, the first five concurrent requests use account-1, the next request uses account-2, and so on.
- Reuse: once account-1 releases a slot, the next request prefers account-1 again.
- Binding: a target explicitly bound to account-3 reaches the executor as account-3 even if account-1 has higher priority.
- Lifecycle: exception, timeout, retry, non-stream completion, and stream finalization each release exactly once.
- Negative scope: non-priority strategies retain their existing semantics.

## Verification discipline

A helper test passing is not sufficient evidence. Run, in order:

1. focused regression tests;
2. typecheck/build for the affected project;
3. production routing/integration test with concurrent requests;
4. live canary only if deployment/restart is explicitly authorized.

Report code verification separately from runtime deployment. Never claim a live fix from unit/typecheck output alone.
