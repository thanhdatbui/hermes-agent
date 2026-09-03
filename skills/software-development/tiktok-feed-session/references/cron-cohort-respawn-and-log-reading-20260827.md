# Cron cohort dispatch and log-reading lessons (2026-08-27)

## What the live evidence proved
- A cohort can contain both successful machines and per-machine `needs-user-decision` / `manual-needed` outcomes. A lock on one machine must not stop the other machines.
- The Phiên 3 morning cohort was actually dispatched: machine artifacts showed `session_index=3`, `block_index=1`, and the expected `cohort_id`. The first run had terminal results for machines that completed or were blocked.
- The confusing symptom came from a later cron tick replaying the same cohort after the detached launcher/lease path was no longer trusted. The correct diagnosis is not “one lock stopped the batch”; it is “cohort replay/terminal evidence was not used as a spawn gate.”

## Required dispatch invariants
1. Lock/manual outcomes are terminal **per machine for dispatch purposes**. Record them and continue the cohort.
2. Before spawning after a dead/expired lease, reconcile exact artifacts by `cohort_id`, `assignment_id`, `block_index`, `session_index`, `entry_id`, machine path, run id, and normalized timestamps.
3. Exclude machines that already have terminal publications from a recovery respawn. If every expected machine is terminal, do not spawn the cohort again.
4. Keep the frozen cohort denominator for reporting/accounting; only the dispatch list is reduced.
5. Do not infer session progress from wrapper status alone. Read exact `summary.txt`, `log.jsonl`, `run_manifest.json`, and per-machine artifacts.

## Evidence-reading workflow
- First identify the real session window and cohort metadata; do not use a canary/test run as the farm result.
- Distinguish cron tick time, farm session window, and artifact start/end time.
- Normalize timestamps to HCM before comparing UTC producer timestamps to HCM cohort windows.
- If `run_manifest.json` stores machine identity in its parent directory rather than a `machine` field, accept the directory identity only after validating the exact machine path and cohort/entry identity.
- Report facts first: dispatched, terminal, skipped/locked, still missing, and whether a respawn occurred. Do not answer a log-reading request with a generic flow description.

## Regression coverage
- Cohort/watchdog tests must accept terminal statuses `success`, `degraded`, `failed`, `skipped`, `missed`, `timeout`, `manual-needed`, `needs-user-decision`, and `blocked` for per-machine reconciliation.
- Add a runner test proving a later tick does not respawn a cohort whose exact machine publications are all terminal.
- Add a partial-respawn test proving already-terminal machines are excluded while still-missing machines remain dispatchable.
