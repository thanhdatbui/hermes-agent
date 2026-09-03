# Lock-aware target selection

Use this reference for every multi-machine scheduler/launcher that must skip user- or worker-locked devices without stealing ownership.

## Required order

1. Read authoritative candidates and resolve both machine ID and serial.
2. Probe lock aliases read-only: `machine_<N>.lock.json` and `serial_<SERIAL>.lock.json`.
3. Treat any existing alias as unavailable when its status is `queued`/`queued_v2`, `running`, `recovery`, `handoff`, `blocked`, `temporarily_skipped`, or `failed_locked`.
4. Treat malformed, partial, unreadable, or permission-blocked lock data as unavailable (`probe unavailable`), never as free.
5. Record `{machine, reason, owner_status}` in the selection audit and remove the target from the candidate list.
6. Only then apply cooldown, random ordering, quota/`maxMachines`, assignment validation, and launch-plan creation.
7. Immediately before launch, make an atomic queued reservation for the survivors. This closes the probe-to-launch race; a reservation conflict is a skip, not permission to delete or reclaim the foreign lock.

## Why both gates are needed

A reservation-only design is insufficient: a locked target can consume a quota slot and cause an actually free target to be omitted. A probe-only design has a race window. Therefore use **preselection probe + atomic reservation**.

## Safety and reporting

- Never use takeover/full-scope flags in normal scheduled runs.
- Never remove or overwrite a foreign lock, even if its owner appears stale; retained/recovery locks require the explicit guarded recovery path.
- Keep preselection skips separate from worker failures. A skipped locked target must not be counted as a worker failure or as a successful run.
- Persist a redacted selection-rejection artifact so the operator can see why a machine did not consume a quota slot.

## Minimal verification

- Fixture with one queued lock and one free target: the free target remains selectable when quota is one.
- Fixture with malformed lock JSON: target is skipped fail-closed.
- Assert source order: lock probe < cooldown/random/cap/assignment < atomic reservation < worker creation.
- Run focused tests, syntax/PowerShell parse, diff check, and a read-only detector. Do not run live registration as a selection test.
