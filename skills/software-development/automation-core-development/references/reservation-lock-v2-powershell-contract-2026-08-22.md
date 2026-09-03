# Reservation-lock Protocol v2 (PowerShell ↔ automation-core) — 2026-08-22

## The contract

`automation_core.device_lock` (the Python lease guard, canonical home of
device locks) only recognizes queued **reservations** that carry the wire
format below. A legacy payload missing the protocol field makes the guard raise
`DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE` and blocks the night-chain reservation
handoff (the symptom reported: a worker could not claim a batch-reserved lock).

Wire format the guard expects (see `device_lock.py`):
- `_LOCK_PROTOCOL_VERSION = 2`
- `_WIRE_QUEUED_STATUS = "queued_v2"`  (normalizes from logical `"queued"`)
- `owner_active = True` for an active queued reservation

So a reservation payload MUST contain, verbatim:
```json
{
  "status": "queued_v2",
  "lock_protocol_version": 2,
  "owner_active": true
}
```
NOT `status = "queued"` without `lock_protocol_version`. The guard's
`verify_device_lock_lease` checks
`(protocol, owner.get("lock_protocol_version") == _LOCK_PROTOCOL_VERSION)`
and status `(status, ... == _wire_status(normalized_status))` — a `queued`
literal (no `_v2`) and absent `lock_protocol_version` both fail closed.

## Where the PS1 reservation lives

`D:\Taadaa\register gmail\run_parallel.ps1` (internal legacy runner, invoked
only by `run_all.ps1` which sets `GMAIL_CANONICAL_LAUNCHER=run_all.ps1`) defines
the reservation helpers inline:
- `Try-ReserveQueuedLock -Machine <n> -Serial <s>` writes the lock JSON via
  `FileMode.CreateNew` (atomic; race-safe). Returns a reservation object with
  `.paths` + `.lock_id`, or `$null` on conflict.
- `Remove-OwnedQueuedLock -Path ... -ExpectedHost ... -ExpectedPid ...
  -ExpectedLockId ... -ExpectedRunId ... -ExpectedStatus "queued_v2"` → only
  deletes a lock whose status matches `ExpectedStatus` AND owner identity.
- `Release-QueuedReservations` loops `$reservedLocks`, calls
  `Remove-OwnedQueuedLock` with `-ExpectedStatus "queued_v2"`.
- `Get-ReadOnlyDeviceLockProbe` already normalizes a read `queued_v2` → `queued`
  for display; do not "fix" that normalization away.

Fix applied this session: `Try-ReserveQueuedLock` now writes
`status = "queued_v2"` + `lock_protocol_version = 2` (was `status = "queued"`),
and `Release-QueuedReservations` targets `-ExpectedStatus "queued_v2"` (was
`"queued"`), so cleanup only removes the v2 reservation and matches what the
Python guard wrote.

## How to unit-test the embedded PS1 functions in isolation

`run_parallel.ps1` refuses direct dot-source: it has a guard
(`if ($env:GMAIL_CANONICAL_LAUNCHER -ne 'run_all.ps1') { exit 2 }`) BEFORE the
function definitions, and its body executes a heavy inventory read on load. So
you cannot just `. ./run_parallel.ps1` and call `Try-ReserveQueuedLock`.

Isolation recipe (verified):
1. The reservation helpers + their dependencies (`Get-SafeLockName`,
   `Get-LockPaths`, `Test-OwnerAlive`, `Remove-OwnedQueuedLock`,
   `Try-ReserveQueuedLock`, `Release-QueuedReservations`) are a CONTIGUOUS
   function-definition block at lines **88–251** of `run_parallel.ps1` (no
   body-level statements interleaved). Extract that slice.
2. Write the slice to a temp `helpers.ps1` and dot-source only that.
3. Set the vars the helpers read before calling: `$lockRoot` (a temp dir),
   `$runId`, `$fullScopeTakeover = $false`, `$reservedLocks = @()`.
4. Call the functions; assert the JSON payload fields.

Canonical test: `D:\Taadaa\register gmail\tests\test_reservation_lock_protocol_ps1.py`
(pytest → subprocess `powershell`). Uses this exact slice extraction.

## PITFALL — ad-hoc verification lock-dir reuse

`Try-ReserveQueuedLock` uses `FileMode.CreateNew` → it THROWS `IOException` if
the lock file already exists and returns `$null` (the function's `catch` returns
`$null`). If an ad-hoc verification script reuses ONE lock dir across two
scenarios, scenario B's `Try-ReserveQueuedLock` collides with scenario A's
leftover lock → returns `$null` → `Release-QueuedReservations` has nothing to
release → a FALSE `FAIL` ("lock not released").

Rule: EVERY scenario/assertion gets its OWN fresh temp lock dir. Same class of
bug as `tempfile.mkdtemp()`-per-iteration in the core TDD notes — never reuse a
stateful path across asserts. (Confirmed: a standalone isolated run with a fresh
lock dir produced `RELEASED`, RC 0; the earlier false FAIL was purely harness
state reuse.)

## Evidence shape for handoff

- `pytest tests/test_reservation_lock_protocol_ps1.py -v` → 3 passed (v2 payload
  written; release removes v2 lock; legacy `queued` v1 lock preserved by v2
  cleanup path).
- `run_parallel.ps1` parse check:
  `powershell -NoProfile -ExecutionPolicy Bypass -Command "[ScriptBlock]::Create((Get-Content -Raw 'D:\Taadaa\register gmail\run_parallel.ps1')) | Out-Null; Write-Output 'PARSE_OK'"`
