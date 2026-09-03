# Follow release vs script error — regression matrix

## Semantic contract

`FOLLOW_FAILED` is a verified TikTok release event, not a generic process failure. It is emitted only after the follow flow has tapped Follow and the fresh post-tap/pull-to-refresh verification sees the exact action button return to `Follow`/`Follow lại`. That event may set the daily `FollowState` block and may appear in the watchdog's `Nhả follow` list.

A non-zero subprocess exit, `MANUAL_REVIEW`, `TIMEOUT`, exception, malformed output, identity/search/navigation failure, or unknown button state is not proof of release. Keep it in `Lỗi`/manual diagnostics. `skipped` is its own bucket.

## Regression matrix

| Input record | Nhả follow | Lỗi script/xác minh | Bỏ qua |
|---|---:|---:|---:|
| `status: FOLLOW_FAILED`, verified release path | yes | no | no |
| `status: MANUAL_REVIEW`, even with `exit_code: 1` | no | yes | no |
| `status: TIMEOUT` | no | yes | no |
| `status: failed`, non-zero exit only | no | yes | no |
| `status: skipped` | no | no | yes |
| `status: OK` with `followed` list | no | no | no; success |
| Feed `summary.txt` failure | no inference | no inference | no inference |

## Producer checks

In the feed-to-follow hook:

```python
result = {
    "status": "failed",
    "exit_code": proc.returncode,
    "failed": 1,
    "follow_failed": False,
}
# parse FOLLOW_RESULT, then:
result["follow_failed"] = normalized_status == "FOLLOW_FAILED"
```

Do not use `proc.returncode != 0` as a release signal. Preserve `exit_code` and `failed` for diagnostics. Log `script_error` for a non-zero exit without explicit `FOLLOW_FAILED`.

## Watchdog checks

For each `follow_result.json`, classify in this order:

1. `status == FOLLOW_FAILED` → `Nhả follow`.
2. `status in {OK, SUCCESS}` and `followed` is non-empty → Follow success.
3. `status == skipped` → Bỏ qua.
4. Anything else → Lỗi script/xác minh.

Do not classify by `follow_failed` alone, loose Vietnamese reason substrings, Feed status, or machine number.

## Artifact reconciliation recipe

1. Resolve the exact report run directory from the watchdog timestamp/session label.
2. Enumerate `machines/machine_*/**/follow_result.json`.
3. Print separate sets for status, `follow_failed`, `exit_code`, reason, and followed count.
4. Confirm row from each result's `row`/`account_row_index`; do not infer row from Feed Fail.
5. For true `FOLLOW_FAILED` records, inspect the row-specific state file and evaluate the daily predicate (`follow_failed_date == today` or `follow_failed == true` plus `budget_date == today`).
6. Never edit historical artifacts/state to repair a bad report. Fix the producer/consumer classification seam and rerun a fixture matrix with `FOLLOW_FAILED`, `MANUAL_REVIEW`, `TIMEOUT`, `OK`, and `skipped`.

The same machine may independently have a Feed failure, a Follow release, a Follow timeout, and a daily cooldown in different artifacts. Keep those dimensions separate.