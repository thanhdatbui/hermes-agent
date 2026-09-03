# Target resolution and active-run conflict handling

When a user has already named an incident target (for example, `M41`), treat that explicit machine number as authoritative input for the next target-resolution step. Do not discard it merely because the latest screenshot text or a new search result does not repeat the number.

1. Resolve the canonical row and serial for the named machine using the repository's real workbook/device-map resolver. Keep account identity and serial masked in reports.
2. If the resolver returns multiple valid rows, use the row tied to the incident evidence; if the incident evidence identifies the account but the current workbook has changed, report the mismatch instead of silently selecting a different account.
3. Before launching a targeted canary, inspect live processes and the target's current artifact directory. If an existing cron/batch already includes the target, do not launch a duplicate invocation or run a second canary over it.
4. Read the target's own summary/log and distinguish these states: skipped by an existing lock, actually exercised, successful, failed, and blocked before UI. A `needs-user-decision` lock result is not a canary pass.
5. If the target is held by a stale blocked lock, use only the repository's documented operator/reaper path. Never delete or overwrite the lock file by hand. If an unrelated batch is still alive, wait or stop at Gate 0; do not kill it blindly.
6. Only claim live recovery evidence when the target's own artifact proves `final_status: success` and `stop_reason: ""` (or the exact canonical success contract for that runner).

This prevents a known target such as M41 from being replaced by an unrelated historical canary, and prevents duplicate farm runners from competing for the same device.
