# 6H Lifecycle Report Snapshot Reconciliation

## Why this matters
A 6-hour lifecycle report is a point-in-time snapshot. The supervisor may process more profiles after the report is generated, so a later read of the canonical state can legitimately contain new BLOCKED entries. Do not silently treat the delivered report as current state.

## Reconciliation procedure
1. Record the report/job generation time from the scheduler metadata when available.
2. Read the canonical Kibe and Admin supervisor state files directly; do not infer current counts from the Telegram text alone.
3. Recompute BLOCKED as `status in {BLOCKED, FAILED, ERROR, QUARANTINE}` and split by farm, stage, and status.
4. Compare each newly observed blocked profile's `updated_at` to the report snapshot time. Attribute only entries updated after the snapshot as post-report delta.
5. Inspect `last_result`, history, and available artifacts before assigning a cause. A bare `status=FAILED` is insufficient evidence for claiming Microsoft service error, OTP rate-limit, or missing recovery data.
6. Keep fail-closed behavior: do not bulk reset or retry BLOCKED/QUARANTINE profiles. Reopen only after per-profile cause, cooldown, and required recovery/security data are verified.

## Reporting style
Lead with deltas and actions, not a verbatim restatement of every metric. Explicitly call out report-vs-live-state mismatches and the evidence for any post-report additions. If the error payload is absent, say the cause is unclassified rather than guessing.

## Evidence pattern from the lifecycle farm
A report showing 51 Kibe BLOCKED was followed by a live state showing 53: the canonical state had 52 `CHANGE_INFO` BLOCKED and 1 `HOTMAIL_LOGIN` QUARANTINE, with two profiles' `updated_at` values after the report snapshot. This is the expected way to explain a stale report without rewriting historical telemetry.
