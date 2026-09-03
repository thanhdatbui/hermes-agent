# Recovery watcher verification

Use this for read-only checks that an autonomous TikTok recovery scheduler actually handled an incident.

## Evidence layers

Do not treat a Scheduled Task `Running`, a live PowerShell/Python PID, or a recent watcher heartbeat as recovery success. Reconcile these layers:

1. **Shift state** — `python_runner/runs/scheduler-state.json`: scheduled start, `status`, duration, reason, artifact root, exit code.
2. **Watcher activation / lease** — `python_runner/runs/schedule-recovery-activation.json` and `schedule-recovery-watch-lease.json`: activation baseline, bound parent/child identity, `state`, heartbeat.
3. **Recovery ledger** — `python_runner/runs/schedule-recovery-ledger.jsonl`: `DETECTED`, classification, reservations, handlers, recapture, retry, and final events per `incident_key` / machine.
4. **Watch output** — `runs/schedule-recovery-task.log`: latest polling result; repeated `outcomes: []` means the watcher is alive but not currently producing recoveries.

Normalize `observed_at` (UTC) with task and shift times before reporting a timeline.

## Required conclusion categories

Count only explicit `VERIFIED_SUCCESS` as successful recovery. Report separately:

- `MANUAL_REQUIRED` — sensitive/manual gate; do not call it auto-recovered.
- `FINAL_BLOCKED` — recovery reached a terminal stop; include `reason` and evidence path.
- `DEFERRED_LOCKED` — ownership gate preserved; no recovery work was run.
- non-terminal (`AUTO_RECOVERY_PENDING`, `ADVISOR_RESERVED`, etc.) — unfinished work, even if a later watcher process is healthy.

A `PATCH_ATTEMPT_RESERVED` followed by `REPAIR_NOT_READY` is not a live recovery attempt or a recovery success. If the ladder ends in `repair-ladder-exhausted-without-approved-patch`, state plainly that no approved handler/patch reached target-scoped execution.

## Restart / baseline pitfall

A newly activated watcher may snapshot the already-terminal scheduler shift as its baseline. It can then poll successfully with empty outcomes while an older ledger incident remains non-terminal. Always scan the ledger for the last event of every incident in the affected shift; do not conclude that a restart resumed an `ADVISOR_RESERVED` or `AUTO_RECOVERY_PENDING` item unless there is a later transition.

## Read-only command pattern

- Query the recovery task and health task status plus the scheduler task's last run/result.
- Read the four evidence files above.
- Group ledger events by `incident_key` and machine; show the first/last `observed_at`, latest state, and terminal reason.
- Verify bound lease PIDs with `tasklist.exe` if needed.
- Never trigger a scheduled task, restart a watcher, release a lock, or run device automation during this check unless the user explicitly asks.

## Example: morning shift, 2026-08-09

The 06:00 shift ended failed. Recovery subsequently detected 20 targets. Ten became `MANUAL_REQUIRED` for a sensitive popup; nine ended `FINAL_BLOCKED` after `REPAIR_NOT_READY: structured-patch-decision-required` exhausted the repair ladder; one was still `ADVISOR_RESERVED`. The watcher later restarted, remained alive, and emitted empty polling outcomes. This is **activated but operationally incomplete**, not an auto-recovery success.
