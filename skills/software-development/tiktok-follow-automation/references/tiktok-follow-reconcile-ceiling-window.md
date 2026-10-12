# TikTok Follow Reconcile Ceiling Window & Historical Backfill Invariant

## Problem
In `feed_session_watchdog.py`, `reconcile_cluster_following` calculates web follower/following deltas by diffing:
`delta = latest_row[following] - baseline_row[following]`

When the watchdog runs as a backfill for historical sessions (e.g. 7 days prior), `baseline_row` is correctly bounded to `timestamp <= session_start_iso`.
However, if `latest_row` queries:
```sql
SELECT following, timestamp
FROM snapshots
WHERE LOWER(username) = LOWER(?)
ORDER BY timestamp DESC, id DESC
LIMIT 1
```
without an upper bound, `latest_row` retrieves the **latest snapshot from present day** rather than the snapshot at the conclusion of that session.

### Consequence
The reported following growth reflects cumulative follower/following changes across days/weeks (e.g. +129 web following) compared against a single 2-hour session (script reported 67), creating spurious reporting discrepancies (+62 follow divergence) and misleading alarms.

## Invariant Fix
Always clamp the end boundary when reconciling historical session clusters:
```python
def reconcile_cluster_following(
    cluster_accounts: list[str],
    target_date: str,
    session_start_iso: Optional[str] = None,
    session_end_iso: Optional[str] = None,
) -> dict[str, Any]:
...
    if session_end_iso:
        cur.execute("""
            SELECT following, timestamp
            FROM snapshots
            WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
        """, (u, session_end_iso))
```

In the session runner:
Compute `end_time_str = "23:59:59" if win["end"] in {"24:00", "00:00"} else f"{win['end']}:00"` and supply `session_end_iso=f"{target_date} {end_time_str}"`.
Mirror changes synchronously between `scripts/feed_session_watchdog.py` and `scripts/hermes_cron/feed_session_watchdog.py`.
