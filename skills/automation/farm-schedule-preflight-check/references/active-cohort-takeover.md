# Active-cohort takeover evidence recipe

Use this reference when a single-machine live task must take over a device currently listed in a multi-machine feed run.

## Required evidence before any mutation

Capture, for both aliases, without printing secrets:

- `machine_<N>.lock.json`
- `serial_<SERIAL>.lock.json`
- SHA-256, status, PID, host, project, run ID, `owner_active`, and timestamps

Then verify process identity and command line using read-only process inspection. Do not rely on a stale artifact's PID or run ID: a newer runner may have acquired the same lock.

## Decision table

| Observed state | Permitted action |
|---|---|
| `running` / `queued_v2` and owner process is alive | No takeover. Require an official per-machine relinquish/exclusion API; otherwise `FINAL_BLOCKED / DEVICE_LOCK_CONFLICT_ACTIVE_OWNER`. |
| `handoff` / `blocked`, owner inactive, official takeover flag and proof available | Guarded takeover through the official lock API only. |
| PID from an old artifact is dead but current lock points to another live owner | Treat current live owner as authoritative; do not reclaim based on the old PID. |
| Lock aliases disagree or cannot be read | Fail closed; do not guess or launch. |

`--full-scope-takeover` must be inspected in source and runtime behavior; its name alone is not proof of per-machine exclusion. A guarded inactive-lock reclaim is not equivalent to removing one machine from an active cohort.

## Stop-preserving artifact

When blocked, write only to the task's designated runtime artifact root. Record:

- `final_status: FINAL_BLOCKED`
- exact blocker code
- redacted target identifiers
- fresh lock snapshots and hashes
- current owner process evidence
- `runner_started: false`
- `takeover_attempted: false`
- `release_or_delete_attempted: false`
- proof that unrelated lock aliases and the feed parent were not modified

Never kill/taskkill a shared parent, pause the whole scheduler, delete or manually edit lock files, or substitute an ad-hoc runner.

## Revalidation checkpoint

Re-check the target immediately before launching the replacement runner. If the owner PID, status, or run ID changed at any checkpoint, discard the earlier decision and repeat the matrix against the latest bytes.

This reference is intentionally scoped to evidence and fail-closed decisions; it does not authorize any live action by itself.
