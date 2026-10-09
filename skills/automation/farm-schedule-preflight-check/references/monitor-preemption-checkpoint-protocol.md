# Bounded Monitor/Preemption Checkpoint

Use this reference when an operator requests a monitor/preemption phase for one named machine and forbids waiting on the lock, canary execution while held, kill/delete, and force-preemption.

## Required evidence

1. Read both canonical aliases: `machine_<M>.lock.json` and `serial_<SERIAL>.lock.json`.
2. Record both raw paths, existence, hashes, status, machine/serial identity, PID, parent PID when available, project/command, `run_id`, `pinned`, `user_authorized`, protocol version, and `last_heartbeat`.
3. Verify owner liveness from the operating system (`psutil.pid_exists(pid)` plus process identity/command line). A dead PID is only evidence about a former owner; it is not authorization to take over.
4. Read the target machine's current manifest/assignment entries and next scheduled slot. Do not infer safety from missing locks alone.
5. Inspect only the target runtime paths for a real cooperative protocol: `drain_requested`, reservation/handoff API, safe-point yield, `EXIT_YIELD`, and `RESUME_TICKET`.

## Decision gate

- Live owner + active/pinned lock: preserve lock and do not acquire, delete, overwrite, kill, or run canary.
- Supported cooperative API: issue only the documented reversible drain/reservation request, record the exact command actually issued, then launch a detached status monitor only if the API contract supports it.
- No supported cooperative API: issue nothing. Return `LOCK_HELD` with `drain_reservation.exact_command: null`, `result: NOT_ISSUED`, and an external-supervisor `next_action`.
- Lock-file disappearance is not `LOCK_ACQUIRED`; acquisition requires a fresh canonical lease artifact or official runner acknowledgement.
- A monitor child that acquires a lease must not run the canary; hand off to the official live-runner.

## Structured checkpoint

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
  exact_command: null
  result: NOT_ISSUED
  reservation_state: HELD_BY_ACTIVE_OWNER
canary_executed: false
next_action: ...
```

Keep observations separate from hypotheses. Use `NOT_FOUND`, `NOT_ISSUED`, or `UNPROVEN` rather than inventing a command or claiming a handoff.
