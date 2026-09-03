# Controlled takeover: owner verification and fail-closed handoff

## Purpose

Use this reference when one registration target must take over a machine currently covered by a live feed/farm session. It captures the reusable verification pattern from a blocked live run; it is not permission to bypass the lock protocol.

## Gate sequence

1. **Freeze scope.** Record one machine, one canonical serial, one task/run ID, and the official runner. Do not broaden a single-target request into a farm-wide run.
2. **Bootstrap before side effects.** Read workspace/project rules and case docs; preserve unrelated dirty files; print four gate lines: Git, docs, scope, verdict.
3. **Read both aliases.** Inspect the machine lock and serial lock. Require the same machine, serial, host, PID, lock ID, run ID, status, owner-active flag, protocol version, and compatible timestamps in both files.
4. **Independently verify the owner.** Query PID presence, process creation time, executable/command line, parent chain, and children. Confirm the command belongs to the recorded project and includes the target. Child ADB activity is evidence of active ownership, not stale cleanup.
5. **Recheck after transitions.** If the original PID disappears or the lock changes, reread both aliases and probe the new PID/run ID. A replacement `queued`/`queued_v2` reservation can be live even when the old owner is gone.
6. **Find a real handoff mechanism.** A scheduler stop function only counts if it controls the currently owning process. A disabled scheduled task, a separate scheduler object, or a generic recovery helper is not a handoff for an already-running feed process.
7. **Fail closed when needed.** If the owner is alive, actively issuing device work, or no repo-native per-machine close/handoff exists without forceful termination, write `FINAL_BLOCKED` evidence and stop. Do not use taskkill, Stop-Process, reboot, adb kill-server, manual lock deletion, or a parallel runner.
8. **Only after inactive proof.** Acquire both aliases with the official lock API and explicit takeover authorization. Keep the worker lease through detector/source mutation, replacement selection, runner execution, and verification. On failure retain `FAILED_LOCKED`/handoff; release only after independently verified success or explicit abandonment.

## Evidence/reporting checklist

Report absolute paths for the final artifact and relevant log, current redacted lock state, owner PID/host/project/run ID, and the replacement mailbox in redacted form. State explicitly whether takeover, source mutation, and official runner start occurred. Never include passwords, tokens, or OTPs.

## Common misleading signals

- A previous `FINAL_BLOCKED` artifact does not prove the current lock is unchanged.
- A dead old PID does not prove the target is free; a new reservation may have replaced it.
- A terminal-looking old device log does not prove the current process has stopped.
- `queued` is not automatically inactive when a live parent runner owns the reservation.
- `Stop-SchedulerCurrentSession` is not sufficient when `TikTokScheduler` is disabled or unrelated to the live process.
