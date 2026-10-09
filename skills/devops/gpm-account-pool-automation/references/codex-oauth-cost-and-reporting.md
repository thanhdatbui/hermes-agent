# Codex OAuth cost and reporting

## Cost ceiling

When the user sets a `$0.12` maximum for 5SIM, implement a strict lower ceiling of `<= $0.11` in every relevant location: pool discovery default, caller override, and final live-price guard. Changing only the default is insufficient. Invalidate the cached pool after the change so stale candidates above the new cap are not reused.

## Report semantics

Keep these metrics separate:

- ChatGPT registration success.
- Codex OAuth completion, backed by `codex_oauth_at` or an equivalent successful OAuth result.
- Soak/wait stages such as `WAIT_24_48H` and `WAIT_7D`.

The 6-hour report should show both `Codex OAuth completed / ChatGPT-registered` and `Codex OAuth completed / total queue`, plus pending `WAIT_24_48H`. Do not infer success solely from `WAIT_7D`; reconcile state fields with `last_result` and flag inconsistent legacy records.

## Freshness verification

Run the report locally against the same runtime state and compare it with the delivered cron response. If the cron response lacks the OAuth line, it is stale or the scheduler is using another deployed copy. Verify runtime, deploy, and sync copies after edits. A local run alone does not prove the scheduled job uses that copy. Before claiming the new metric was reported, require a fresh cron execution whose output visibly contains it.

## Pitfalls

- Old totals may be from an earlier state snapshot; compare state mtime and execution time.
- A `WAIT_7D` profile may have a successful `last_result` but no explicit `codex_oauth_at`; treat this as a data-quality discrepancy.
- Split code surgery from report/deploy synchronization into separate one-file contracts when dispatching workers.
