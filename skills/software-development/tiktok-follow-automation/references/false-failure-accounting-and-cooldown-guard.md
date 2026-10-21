# False-Failure Accounting and Cooldown Guard

## Trigger
Use this reference when reviewing TikTok follow state, `fail_streak`, account cooldowns, proxy/IP breakers, Path-B verification, anchor-follow logic, or any report that a nick was punished without a confirmed follow drop.

## Ground truth contract
A follow failure is confirmed only when all of these are true:

1. A real follow tap was actually delivered and recorded.
2. A fresh post-tap or post-reload observation was captured.
3. The observed profile identity is bound to the expected UID/handle.
4. The action state is freshly classified as `not_followed`.
5. The navigation/reload/restore steps needed for that observation completed successfully.

Anything else is `MANUAL_REVIEW` / unknown. In particular, do not call `set_follow_failed()` for:
- failed reload or refresh;
- no Follow button found or tap exception;
- wrong screen, stale XML, OCR-only evidence without identity binding;
- target not found, no-video, or external priority target resolution failure;
- an anchor tap whose result cannot be bound to the anchor identity.

## State-mutation rules
- Put the active `cooldown_until_at` guard before every other mutation. A duplicate callback during active cooldown must be a byte-level no-op: no save, timestamp update, streak change, ceiling change, or breaker call.
- Account-level `set_follow_failed()` must not trip or consult a machine/IP circuit breaker. IP risk is an independent aggregate signal and must be evaluated by monitor/audit logic, not by one account mutator.
- Preserve the distinction between a clean business outcome (`FOLLOW_FAILED` with account cooldown) and a dirty technical failure (`MANUAL_REVIEW`, reload failure, identity mismatch, persistence failure). The latter must remain fail-closed and must not silently punish the account.
- Only a fresh, identity-bound `not_followed` result after a real tap/reload may increment failure state.

## Review procedure
1. Trace every `set_follow_failed()` caller and classify its evidence contract.
2. Check whether a reload return value is ignored or whether a loop `break` falls through to failure mutation.
3. Check whether OCR/classification can run on a wrong screen before identity verification.
4. Check whether `follow_tap_done` is actually read before post-tap waiting/reload.
5. Verify the active-cooldown guard precedes legacy migration, graduation, ceiling, timestamp, and `_save()` operations.
6. Verify no account state mutation imports or invokes IP-breaker code.
7. Add focused mocked regressions for each false-positive path; do not run the full farm suite during debugging.

## Regression matrix
- State: second `set_follow_failed()` while cooldown active leaves state file bytes unchanged.
- State: graduated and non-graduated failures never invoke `trip_ip_breaker`.
- Verify: reload returns false -> `VerifyResult("manual")`, zero failure callbacks.
- Mode 2: missing Follow tap or unbound identity -> manual outcome, zero failure callbacks.
- Mode 2: identity-bound fresh `not_followed` -> the only path that may produce `FOLLOW_FAILED`.

## Evidence/reporting
Separate `tap_attempted`, `runner_verified`, and later web/snapshot reconciliation. Never infer a dead external priority target from HTTP 200 or an anti-bot placeholder. If the account is absent from the tracking DB, report that as “not present in tracker”; do not delete or disable the configured target without direct profile evidence and user authorization.
