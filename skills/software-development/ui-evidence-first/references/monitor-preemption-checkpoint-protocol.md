# Monitor/Preemption Checkpoint Protocol

Use this reference when an operator asks for a monitor/preemption phase for a named device and explicitly forbids re-running code/tests, waiting for a long interval, or running the canary in the monitor child.

## Required evidence sequence

1. Read both device-lock aliases for the target: `machine_<N>.lock.json` and `serial_<SERIAL>.lock.json`. Check both the canonical lock root and the legacy compatibility root when policy requires it.
2. Snapshot the exact UTC time, raw existence state, status, owner PID, parent PID, run ID, project, `user_authorized`, `pinned`, heartbeat, and serial/machine identity.
3. Verify owner liveness from the OS, not from the lock JSON alone. A dead PID is evidence of a dead former owner, not permission to force-preempt an unknown replacement.
4. Resolve the current assignment/manifest entry for the target and record the next scheduled slot. Do not infer that a missing lock means the device is safe for arbitrary work without checking the manifest.
5. Inspect the canonical runtime for a supported cooperative protocol. Look specifically for `drain_requested`, a handoff request/reservation API, `RESUME_TICKET`, and a distinct yield status/exit code such as `EXIT_YIELD`.

## Decision rules

- If both lock aliases are present and the owner is live, request only the supported cooperative drain/reservation. Never delete, overwrite, or force-preempt a pinned/user-authorized live lock from the monitor child.
- If no supported drain/reservation command exists, report `NOT_ISSUED` rather than inventing a command or calling a destructive `force_preempt` API.
- If both aliases are absent and the former owner is dead, report `LOCK_ACQUIRED` only when the monitor itself has actually acquired the canonical lease. Absence alone is `LOCK_FREE`/`READY_FOR_ACQUIRE`, not proof that this child acquired it.
- If the monitor child acquires the lease, it must not run the canary. It must hand off to the live-runner, which rechecks both aliases and acquires/uses its own official runner lease according to the project contract.
- Never equate a dead historical PID or an old run ID with the current owner. Re-read aliases immediately before any side effect.
- Do not wait for a fixed 15-minute interval when the request requires a bounded checkpoint. Use the requested deadline and report the observed state at the checkpoint.

## Structured report contract

Return a machine-readable checkpoint with exactly these top-level concepts:

```yaml
status: CHECKPOINT
checkpoint: LOCK_HELD | LOCK_ACQUIRED
observed_at_utc: ...
target: {machine: ..., serial: ...}
H1: {result: ..., evidence: ...}
H2: {result: ..., evidence: ...}
H3: {result: ..., evidence: ...}
H4: {result: ..., evidence: ...}
H5: {result: ..., evidence: ...}
drain_reservation:
  exact_command: ...
  result: ...
  reservation_state: ...
next_action: ...
```

The `drain_reservation.exact_command` field must contain the literal command actually issued, or `null` plus `NOT_ISSUED` and the reason when no supported command exists. Do not substitute a hypothetical command. Include whether a canary ran; for `LOCK_ACQUIRED` from a monitor child it must be `false`.

## H1-H5 hypothesis set

Use stable labels so downstream automation can parse the checkpoint:

- **H1** — owner/lock identity and alias consistency.
- **H2** — owner liveness and pinned/user-authorized protection.
- **H3** — supported drain/reservation protocol and exact command result.
- **H4** — safe-point/yield/resume evidence, including `EXIT_YIELD` or `RESUME_TICKET` when implemented.
- **H5** — post-check ownership handoff, live-runner readiness, and absence of monitor-child canary execution.

Each result must be one of `CONFIRMED`, `NOT_FOUND`, `NOT_OBSERVED`, `UNPROVEN`, `BLOCKED`, or another explicitly explained terminal state. Separate observations from hypotheses; a missing artifact is not proof of a successful handoff.

## Common pitfalls

- Do not claim `LOCK_ACQUIRED` solely because lock files disappeared; acquisition requires a fresh canonical lease artifact or runner acknowledgment.
- Do not report a made-up drain command merely because the architecture document describes one. Architecture text is not an installed runtime interface.
- Do not re-do code/test work during a monitor-only request.
- Do not launch the canary from the monitor child after an acquisition; hand off to live-runner.
- Do not perform `taskkill`, ADB force-stop, lock overwrite, `pm clear`, or stale-lock deletion unless a separate, explicit fenced-recovery contract authorizes it and its evidence gates are satisfied.
- **Concurrent supervisor upgrade handoff:** If an incident supervisor is undergoing concurrent upgrade by another worker and still has a toy/stub schema (e.g., single-letter phases `A`–`Z`), do NOT edit it ad-hoc or inject incompatible state. Return a precise handoff state (`supervisor_upgraded: false`, exact PID, `run_id`, log path, checkpoint).
- **No in-agent polling without supported detached monitor:** Launch only an existing supported detached read-only monitor. If none exists for the target, do NOT spin an in-agent sleep loop or poll in child sessions; emit `next_action=monitor <target>` and exit within budget.
- **Strict sequential gate discipline:** When following a sequential gate (e.g. M11 before M40/M66), do not inspect downstream targets until the current lock/checkpoint gate resolves.
