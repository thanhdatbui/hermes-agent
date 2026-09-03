# Scheduler-vs-runner stale-state triage

Use this reference when a scheduled TikTok feed session appears not to start.

## Evidence layers

Keep these three states separate:

1. **Hermes job invocation state** — `cron/jobs.json`, `cron/output/<job-id>/`, and `agent.log`. The log line `Job '<name>' already running — skipping` is the scheduler's in-memory/job-level guard. It means a prior invocation has not returned from Hermes' perspective.
2. **Runner child state** — `runner-live-lease/<logical-day>.json`, the recorded PID list, exact `tiktok_runner.py` / `run-feed-session.ps1` process tree, and per-device artifact directories. A dead recorded PID proves the child is gone, but does not by itself prove the Hermes parent invocation has released its guard.
3. **Device lock state** — `~/.codex/device-locks/*.lock.json`. Device locks may affect which machines the consumer handles, but they do not create Hermes' job-level `already running` message.

## Minimal triage sequence

1. Record current HCM time and run `cronjob(action='list')`; capture `enabled`, `state`, `last_run_at`, `last_status`, and `next_run_at` for runner, picker, and watcher.
2. Read the runner's cron output files and `agent.log` around the missed schedule. Distinguish a real invocation with empty/silent output from a scheduler-level skip.
3. Read the logical-day runner lease. For every PID in `rows[]`, verify process identity and command line; do not infer liveness from `expires_at` alone.
4. Inspect the exact launcher descendants and artifact tree. A new cohort artifact and child command are the proof of dispatch; empty stdout is normal for a `no_agent` job and is not proof of success.
5. Inspect device locks separately and classify by project, status, `owner_active`, host, and PID. Do not delete another project's active lock.

## Recovery rules

- If a live launcher or child exists, do not kill it merely because Telegram has no message; inspect its artifacts and allow it to finish unless the user authorizes stopping that exact target.
- If all recorded runner PIDs are dead and the lease is stale, clear only the matching runner lease/claim according to the runner's canonical recovery path, then trigger one controlled runner tick and verify a new artifact/process.
- If the job still logs `already running` after the child/lease is cleared, the stale state is in Hermes' scheduler process (often an in-memory running-job set). Do not claim the lease fix solved it; use a controlled Gateway restart only when authorized and verify the scheduler reloaded the job.
- Never pause unrelated cron jobs to work around a runner guard. Watchdogs and dead-owner monitors must remain enabled.
- For a user who says “fix”, continue through repair and fresh verification; a diagnosis, plan, or stale-tree blocker is not a completed fix.

## Reporting format

Report in Vietnamese, concise and direct:

- **Mục đích**
- **Kết quả** — exact timestamps, job names, and evidence layer
- **Blocker** — only if repair or verification could not complete; state the next safe action

Do not expose credentials, tokens, cookies, passwords, or unnecessary serials in the report.