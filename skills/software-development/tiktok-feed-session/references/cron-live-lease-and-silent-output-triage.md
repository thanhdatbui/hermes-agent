# Cron Live-Lease and Silent-Output Triage

Use this read-only triage when the user reports that feed cron stopped, appears idle, or repeatedly skips machines.

## Evidence sequence

1. Check the scheduler registry: `enabled`, `state`, `last_run_at`, `last_status`, and `next_run_at` for the runner and watchdog jobs.
2. Read the newest per-run output artifact. `Status: silent (empty output)` proves only that the script emitted no alert; it does not prove that a feed session ran or succeeded.
3. Inspect the runner live-lease file under the configured runtime root. Record `pid`, target rows/machines, `started_at`, `expires_at`, and expected target count.
4. Independently verify the recorded PID is alive. A lease whose PID is gone is a stale/orphaned lease; do not treat its future `expires_at` as proof of a live runner.
5. Compare the latest real run artifact (`summary.txt`, `log.jsonl`, and manifest) with the lease timeline. A successful targeted canary is not evidence that the scheduled fleet run succeeded.
6. Check the runner's actual command/entrypoint and timeout evidence. A prior scheduler timeout can leave an orphaned lease or suppress later work.

## Classification

- `SCHEDULER_DISABLED`: job is not enabled or is paused.
- `RUNNING_CONFIRMED`: job is enabled, lease PID exists, and current run artifacts are advancing.
- `STALE_LEASE`: lease exists but its recorded PID is absent; report the affected row/machines and expiry, without deleting or renewing it during read-only diagnosis.
- `SILENT_UNPROVEN`: watchdog/runner output is silent and no fresh success artifact proves execution.
- `RUNNER_TIMEOUT`: scheduler output explicitly reports a timeout; treat it separately from stale lease and from device/UI errors.

## Safety boundary

Diagnosis must not pause cron, delete leases, release device locks, rerun the batch, or touch devices unless the user explicitly requests that operation. If recovery is later authorized, use the repo's target-scoped recovery/lock procedure rather than a whole-batch rerun.

## Reporting format

Report briefly: `Mục đích`, `Kết quả`, `Bằng chứng` (job/lease/PID/artifact paths and timestamps), `Confirmed / Excluded / Unproven`, and `Blocker`. State explicitly when a successful canary or silent watchdog output cannot prove fleet success.

## Incident pattern retained for regression awareness

A representative failure mode is: an earlier runner invocation times out; a later invocation writes a lease for a fleet cohort; the process disappears while the lease remains until its TTL. Subsequent scheduled invocations can then skip or block the cohort. The durable lesson is to compare lease ownership with live process liveness, not to trust the lease file alone.
