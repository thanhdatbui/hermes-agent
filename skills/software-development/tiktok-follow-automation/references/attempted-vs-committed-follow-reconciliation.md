# Attempted vs committed follow reconciliation

## Finding
A follow runner can record an attempted action in an aggregate ledger before TikTok accepts it. Post-action verification may then report `FOLLOW_FAILED` and `bị nhả sau vuốt`; this is zero committed follows. A `skipped`/`đã follow sẵn` result is also zero new follows.

## Evidence precedence
1. Per-machine `follow_result.json` is authoritative for committed count: `followed_count` and `followed`.
2. Aggregate `daily_account_actions` is an attempt/telemetry ledger unless its producer explicitly documents server confirmation.
3. Web Following snapshots verify the resulting delta.

## Correct calculation
- `attempted = aggregate action ledger` (report separately, if useful)
- `committed = sum(follow_result.followed_count)`
- `web_delta = post_snapshot.following - baseline_snapshot.following`
- reconcile `web_delta` against `committed`, never against `attempted`.
- If `committed == web_delta`, report `Khớp`; do not show a false discrepancy.
- Never move uncommitted cross-follow attempts into natural-follow counts.

## 2026-09-26 evidence pattern
Artifacts showed M6 and M29 as `FOLLOW_FAILED` with anchors released after swipe and `followed_count: 0`; M42 was `OK` with `followed_count: 0` and only skipped-existing entries. The report's +1/+2/+1 came from the aggregate action ledger, producing a false `-4` discrepancy against Web +0. Correct output is: attempted 4, committed 0, Web delta 0, reconciliation matched 0=0; identify the ledger attribution/reporting bug.
