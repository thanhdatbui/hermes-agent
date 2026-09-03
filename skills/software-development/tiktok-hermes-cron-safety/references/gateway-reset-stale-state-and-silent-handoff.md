# Gateway reset recovery: scheduler, lease, bridge, and farm liveness

## Incident pattern

A Hermes Gateway restart or host reset can leave several layers disagreeing:

- Hermes reports a no-agent cron tick as `ok`/silent.
- The scheduler may repeatedly emit `already running — skipping` because an old invocation is still registered.
- A runner lease may point at a dead PID.
- A new runner tick may create a lease but its detached PowerShell child can exit before creating any artifact.
- A watcher may replay historical `HANDOFF` records and publish them to Telegram when `deliver: origin`.

These are different conditions and must be diagnosed independently.

## Safe recovery checklist

1. `hermes cron list`: record `enabled`, `state`, `last_run_at`, `last_status`, and `next_run_at` for runner, watcher, and watchdog.
2. Read the latest per-job output. For `no_agent`, empty stdout means silent; it does not mean feed dispatch.
3. Search scheduler logs for `already running — skipping`; distinguish the scheduler's in-memory guard from `runner-live-lease` and from device locks.
4. Read the logical-day lease. Verify every recorded PID against the OS process table and command line. Remove only a lease for which every recorded PID is dead. Never broad-kill PowerShell/Python, restart Gateway, or touch unrelated device locks as a shortcut.
5. Compare hashes of the repo wrapper and deployed copy under `%LOCALAPPDATA%\\hermes\\scripts\\`; sync only the intended wrapper when they differ.
6. Before any live retry, run the exact `run-feed-session.ps1` command **without `-Run`**. Use the full assignment manifest referenced by `ACTIVE.json`, not the pointer file itself. This checks parameter binding, assignment identity, workbook path, and child argv without ADB/TikTok.
7. Compare runner-emitted switches with the PS1 `param(...)` block and the `run_tiktok.py` parser. Missing `-CohortArtifact` in PS1 produces `ParameterNotFound` and exits before Python. Passing `ACTIVE.json` as `-AssignmentManifest` fails the assignment schema gate; resolve its `manifest_path` first.
8. Only after preflight passes, kick one runner tick. Confirm a fresh lease, a live PowerShell/Python child command line, a new timestamped live artifact directory, and matching cohort/assignment identity.
9. If the detached child exits before artifacts, do not retry blindly. Foreground the same command without `-Run`, capture stderr, fix the first concrete bridge error, and repeat the preflight.

## Watcher output contract

`HANDOFF`, `DEFERRED_LOCKED`, and `RECOVERY_IN_FLIGHT` are non-terminal/deferred states. Failure-recovery mode must not print a list containing only those statuses to a job with `deliver: origin`; replaying historical records otherwise creates repeated Telegram spam. Print only actionable states. Explicit cohort-reconcile output remains reportable.

## Evidence labels for final reports

Report these separately:

- `scheduler_alive`: recent cron tick returned successfully;
- `runner_dispatch_proven`: fresh lease and child command line exist;
- `farm_progress_proven`: fresh per-machine artifacts/publications exist.

Do not claim the farm is healthy from scheduler status alone.
