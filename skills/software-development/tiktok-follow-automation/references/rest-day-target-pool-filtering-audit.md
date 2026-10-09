# Rest-day / cooldown filtering in cross-follow target pools

## Durable lesson

Auditing only the *current account's* organic-rest gate is insufficient. The feed repo assigns organic rest independently per `(date, machine, row)` using a deterministic ~1/3 hash and skips that account's follow hook. However, the follow repo's `follow_uids()` and `anchor_uids()` may still build a target/anchor pool from workbook UIDs without excluding targets that are themselves in an active rest or follow-release/cooldown state.

## Required audit sequence

1. Verify the feed-side gate: rest assignment, `_follow_rate=0`, and follow-hook skip reason.
2. Trace the follow-side pool constructors (`follow_uids()`, `anchor_uids()`, and any priority injection).
3. Distinguish **source-account gating** from **target-account eligibility**. The former does not prove the latter.
4. For the intended policy, define one authoritative eligibility predicate for target UIDs and apply it before anchor prioritization, `priority_targets.txt` injection, and Mode 1 fallback.
5. Exclude active follow-release/cooldown targets fail-closed; do not infer eligibility from stale workbook labels alone. Preserve audit reasons/counts for excluded targets.
6. Add focused mocked tests proving that a rest/cooldown target is absent from both anchor and general target pools while an eligible target remains selectable.

## Common false conclusion

“About one-third of accounts skip the follow hook, therefore the remaining follow list is already filtered.” This only proves per-runner source-account gating. It does **not** prove that a target UID assigned to rest/cooldown is absent from another account's cross-follow list.

## Evidence vocabulary

Use separate terms in reports:
- `organic-rest-day-pure-feed`: source account is resting and its hook was skipped.
- `follow-released-daily-cooldown`: source account is blocked by its own release cooldown.
- `target_pool_filtered`: target-side eligibility was actually applied.
- `target_pool_unfiltered`: only source-side gating was observed; target exclusion is unproven.
