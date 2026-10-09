# Admin-cluster visibility and cross-session follow reporting

## Durable lessons

1. **A missing cluster block is not proof that the cluster completed.** The watchdog must distinguish:
   - `completed`: artifact/run exists and completion gate passes;
   - `skipped`: runner explicitly skipped the window, with the reason and workbook path;
   - `not-started/no-artifact`: no run directory exists for that cluster/window;
   - `blocked/failed`: artifact exists but has a failure or preflight block.
   Never silently `continue` when `session_runs` is empty. Emit a Farm Admin block such as `Không chạy/không có artifact` with evidence.

2. **Validate the runner path before blaming the reporter.** For every cluster and window, check in this order:
   - cluster state file (`runner_simple_state.json`);
   - safe-workbook valid-account count for the selected row;
   - expected artifact directory `runtime/<cluster>/live/<date>/row-<row>-<HHMMSS>`;
   - run `summary.txt` and `run_manifest.json` status.
   A runner log saying `Row ... 0 account hop le ... skipping window` is a real skip, not a completed empty report.

3. **Do not conflate feed execution with cross-follow execution.** A machine can still appear in the next feed session after its prior cross-follow was released. The report's natural-follow subtraction is a reconciliation rule: if `FOLLOW_FAILED`/released and cross-follow count is zero, natural follows from that same machine are excluded from that session's valid natural-follow total. It is not evidence that the machine was released again in the later session.

4. **Report the source of each count.** Keep raw natural follows, released/drop-adjusted natural follows, and cross-follow results separate. Include the machine IDs and session/window for every subtraction. Do not report a farm-wide success summary until all configured clusters have an explicit terminal status.

## Minimal evidence recipe

For a disputed session, capture only bounded paths:

```text
D:/Taadaa/runtime/<cluster>/live/<date>/row-<row>-<time>/
D:/Taadaa/runtime/<cluster>/cron-state/runner_simple_state.json
C:/Users/Kibe/AppData/Local/hermes/cron/output/<runner-job-id>/<timestamp>.md
```

Then compare Kibe and Admin for the same `date + row + window`. If Admin has no matching row directory, the watchdog must say Admin was not run/was skipped; it must not omit the cluster.
