# Cross-follow audit: committed actions, releases, and budget

## Evidence hierarchy

1. **Per-machine `follow_result.json`** is the authority for committed cross-follows: count `followed` / verified `followed_count` only when the result is successful and `follow_failed` is false.
2. `session_account_actions` and `daily_account_actions` are telemetry/attempt ledgers unless their producer explicitly documents server confirmation. They can contain stale, duplicate, or pre-verification counts.
3. Web snapshots are the resulting truth: `post.following - baseline.following`.

Always keep these separate:

```text
attempted  = aggregate/session telemetry
committed  = verified per-machine follow_result count
web_delta  = post snapshot following - baseline snapshot following
```

Reconcile `web_delta` against `committed`, never against attempted telemetry.

## Date-bounded audit workflow

- Restrict inspection to the known dated run directories and machine artifact paths; do not scan an entire drive.
- For every scheduled machine, classify it as:
  - success: verified `followed` list and no `FOLLOW_FAILED`;
  - released/failed: `FOLLOW_FAILED` or `follow_failed=true`, normally fail-closed with zero committed follows;
  - skipped: no committed follow for a documented rest, eligibility, empty-pool, or other skip reason.
- Produce a machine/account table with session counts, committed count, failure/release evidence, and budget comparison.
- “No release evidence found in inspected artifacts/history” is safer than claiming an account was never released. Monotonic Following snapshots alone cannot prove lifetime cleanliness because a failed attempt may leave no Web delta.

## Budget check

Check budget at both levels:

- **Per session:** committed `follow_result` count <= that session's configured cap.
- **Per account/day:** sum committed counts across that account's sessions and compare with the daily ceiling.

If Dashboard, `session_action_stats`, `daily_account_actions`, and machine artifacts disagree, report the discrepancy and the evidence sources. Never declare budget compliance solely from the Dashboard aggregate.

## Reporting template

```text
Date/window: ...
Successful machines/accounts: ... committed ...
FOLLOW_FAILED/released: ... committed 0 / evidence ...
Skipped: ... reason ...
Attempted telemetry: ...
Committed verified: ...
Web Following delta: ...
Budget: per-session ...; per-account/day ...
Discrepancies/limits: ...
```
