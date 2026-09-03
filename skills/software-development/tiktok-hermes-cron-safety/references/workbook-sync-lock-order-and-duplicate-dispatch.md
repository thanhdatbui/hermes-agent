# Workbook sync: lock ordering and duplicate dispatch

## Incident pattern

`taikhoan-run-safe-sync` reported `BLOCKED_TIMEOUT_WORKBOOK_LOCK` and then
`JOURNAL_RECOVERY_FAILED`. The durable journal contained old snapshot paths and dead
PIDs, while the canonical workbook-lock directory could be empty or later show a live
owner. These are separate facts and must not be conflated.

## Root-cause test

The sync path acquired locks for the source workbook and Tik1..Tik4, then called
journal recovery. Recovery called `atomic_workbook_update()` for Tik1/tik3, which tried
to acquire the same JSON lock files again. Although the same thread could re-enter its
Python `RLock`, the lock-file protocol was not owner-reentrant, so the process waited
until timeout. Correct ordering is recovery-before-outer-lock, or an explicit API that
reuses the already-held leases.

## Safe investigation recipe

1. Read the newest cron output and exact `Run Time`.
2. Inspect the journal PID, snapshot paths, and canonical lock root.
3. Recheck each PID immediately before acting. Exclude the diagnostic shell and its
   command line from process matching.
4. Classify the state as: live external owner, stale owner metadata, stale journal, or
   self-deadlock. A stale journal is not proof of a current lock owner.
5. Use temp workbooks, temp lock roots, and fake leases for regression probes. Do not
   run the real sync script while cron may dispatch the same wrapper.
6. If a live invocation is proven hung, identify the wrapper-to-child chain and stop
   only that chain. Never kill Gateway or broad Python/PowerShell processes.
7. After the offline fix is GREEN, run at most one official wrapper invocation and
   verify: exit code, output file, lock cleanup, journal state, and cron output.

## Evidence traps

- A worker report about a live PID can be stale by the time the coordinator acts.
- A later missing PID does not identify ownership without parent/child and creation-time
  evidence.
- `enabled`, `scheduled`, `last_status=ok`, or an empty no-agent stdout is not proof of
  workbook sync or farm-session completion.
- A direct probe can itself create a duplicate writer and make the original failure
  look worse.
- Never delete a lock or journal just to make the next attempt start; use canonical
  owner-dead reaping or the project recovery API.
