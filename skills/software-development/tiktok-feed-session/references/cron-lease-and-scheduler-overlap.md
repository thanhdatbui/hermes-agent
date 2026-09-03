# Cron lease and scheduler overlap

## Why a scheduled job can appear not to run

For Hermes no-agent cron jobs, these are different facts:

- The scheduler tick fired.
- The script exited successfully.
- The script emitted no output (`silent`).
- The runner spawned a new live batch.
- The runner skipped spawning because an older job/lease/process is still active.

Never use `last_status=ok` or an empty cron-output markdown file as proof that a new batch was launched.

## Verification sequence

1. Read the cron job metadata: `schedule`, `enabled`, `last_run_at`, `last_status`, `next_run_at`.
2. Read Hermes agent logs for the exact job name and time window. Search for:
   - `already running — skipping`
   - script exception/timeout
   - successful tick with no-op output.
3. Read the runner's live lease under the configured state root, not a guessed `hermes-cron` directory. For this project the relevant path is:
   `D:/Taadaa/runtime/kibe/cron-state/runner-live-lease/<logical-day>.json`
4. Inspect the lease PID with `psutil`: process name, creation time, status, command line, children, and lease expiry.
5. Inspect the exact live artifact root and newest `row-...` directory. A missing/unchanged artifact means no new batch was spawned.
6. Compare the runner source's guard with the observed state. In this flow `_lease_alive()` prevents another spawn while the earlier lease is alive; the scheduler's own single-flight guard can independently skip overlapping invocations.

## Safe interpretation

- An old process or valid lease is evidence of overlap protection, not proof that the old batch is healthy or progressing.
- Do not kill the process, delete the lease, or force-reclaim devices just to make the next tick launch. Keep locks and preserve the live scene until an authorized recovery path has target-scoped evidence.
- Report `confirmed`, `excluded`, and `unproven`: scheduler fired/was skipped, PID alive/dead, lease valid/expired, artifact advanced/stalled, and whether a new batch actually spawned.

## Minimal operator report

Use concise Vietnamese facts:

- `Cron:` schedule + last tick/status.
- `Skip:` exact scheduler/lease reason.
- `Batch cũ:` PID, start time, expiry, artifact path/status.
- `Batch mới:` spawned or not.
- `Blocker:` exact evidence and next safe action.

Do not call a silent cron output a successful farm run.
