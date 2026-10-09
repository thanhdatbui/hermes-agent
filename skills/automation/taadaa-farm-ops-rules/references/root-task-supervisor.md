# Root-task supervisor and A-Z continuation

## Core lesson
`delegate_task` is a bounded child, not a durable workflow engine. When the user asks for A-Z execution, a child ending or timing out is an event; it must not end the root task. Maintain a ledger/state machine and dispatch the next phase automatically.

## Lifecycle
`RESUME/INSPECT → PATCH → FOCUSED_TEST → MONITOR → COOPERATIVE_PREEMPT → CANARY → ROLLOUT → FLEET_REOPEN → CLOSEOUT`.

Before resuming, seed the ledger with completed phases, tree hash/test evidence, target mapping, lock snapshot, `resume_token`, and `next_action`. Skip completed phases when hashes/evidence still match.

Every worker report must be one of `DONE`, `CHECKPOINT`, `FAILED_RETRYABLE`, `FAILED_FINAL`, or `NEEDS_DECISION`. Any non-DONE result requires an executable `next_action` and `resume_token`. A timeout requires a successor with the checkpoint, not a fresh re-triage. `PARTIAL` is only for genuine external waiting or a hard cap; it is not permission to stop while an automatic next phase exists.

## Role separation
- **code-surgery:** edit code/fixtures and run focused tests; never wait on device locks.
- **monitor/preemption:** inspect lock/process/heartbeat and issue only supported drain/reservation; return `LOCK_HELD` promptly.
- **live-runner:** run a canary only after acquiring the lease; collect exit code, screenshot, UI XML, OCR when emitted, log, and artifact paths.
- **deterministic supervisor/job runner:** own polling, detached execution, resume, and state transitions; wake the coordinator on `LOCK_ACQUIRED`, `CANARY_PASS/FAIL`, `RUNNER_DEAD`, and `ALL_PASS`.

No LLM child may wait more than 60 seconds per call or 120 seconds total for a lock. Do not force-kill, delete locks, reboot, `pm clear`, manual-ADB tap, or overlap a fleet run. Use official lease/preemption mechanisms only.

## Anti-excuse and closeout
Ordinary scope, stale fixtures, dirty unrelated files, and a held lock are routing events, not reasons to ask the user or end the root task. Ask only for missing credentials, unresolvable identity mismatch, destructive action, killing a healthy fleet run, or business decisions.

`DONE` requires real evidence for every mandatory phase: focused tests, target mapping, inspect-machine output, canary final status, screenshot/UI XML/OCR/log/artifacts, and fleet reopen/post-reopen smoke when applicable. `BLOCKED` requires command, exit code, path/error, and exact next action. Never stop with only “evidence is missing” while offline work or another role remains executable.
