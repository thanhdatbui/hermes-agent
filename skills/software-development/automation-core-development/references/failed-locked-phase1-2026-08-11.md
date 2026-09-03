# FAILED_LOCKED Phase 1 — design record & test map (2026-08-11)

Plan: `.hermes/plans/2026-08-11_ai-escalation-failed-locked.md` Phase 1 §7
(R1.1–R1.8). Branch `codex/failed-locked-phase1`, worktree
`D:\Taadaa\automation-core-failed-locked-wt`.

## Design decisions (audit-relevant)

1. **Exactly 5 source edges** → FAILED_LOCKED: CLASSIFIED, RECOVERY_RESERVED,
   RECOVERING, RECAPTURED, GUIDED_RECOVERY_REQUIRED — in BOTH
   `results._TRANSITIONS` and `recovery._allowed`. RETRYING is deliberately
   NOT a source: it keeps the legacy FINAL_BLOCKED contract (attempts≥2,
   artifact, release) so old transitions/tests stay intact. Consequences:
   - Runner post-observation budget check (state RETRYING) still
     `finalize_blocked` + release (old behavior preserved).
   - Runner pre-start budget check (state RECOVERY_RESERVED) →
     `finalize_failed_locked` + hold.
2. **`finalize_failed_locked` is its own method**, not a wrapper over
   `finalize_blocked`: no attempts≥2 / artifact requirement; requires
   non-empty reason; refuses states outside the 5 sources with
   `FAILED_LOCKED_REQUIRES_FAILED_IN_PROGRESS_STATE:<state>`; strict queues
   still require a reservation (`_require_reservation`); evidence minimal +
   redacted (reason, signature, attempts, artifact_paths only if present);
   durable event `FAILED_LOCKED` appended to the queue record.
3. **Completion gate**: strict `transition()` gates direct FAILED_LOCKED via
   `TERMINAL_REQUIS_COMPLETION_GATE` (added to the VERIFIED_SUCCESS /
   FINAL_BLOCKED set). `RecoveryCompletionGate.verify` accepts FAILED_LOCKED
   with reason + evidence but NO artifacts — missing artifact stays
   FAILED_LOCKED, never success.
4. **device_lock**: `failed_locked` added to `_DEVICE_LOCK_STATUSES`
   (`owner_active=False`, `handoff_at` set, verifiable via
   `verify_device_lock_lease`). Phase 1 refuses ALL programmatic reclaim —
   normal acquire AND explicit takeover (`_takeover_payload` guard next to
   `temporarily_skipped`) — because the user-explicit inspect/open path is
   Phase 3. A LIVE failed_locked owner must not be reclaimable even with
   FULL_SCOPE_TAKEOVER + authorization (test asserts DeviceLockUnavailable).
5. **global_recovery (`RecoveryWorkerLease`)**: `mark_terminal` accepts
   FAILED_LOCKED; `watchdog_action` terminal set includes it → returns
   `TERMINAL` even 3600s stale (never REQUEST_CHECKPOINT/REPLACE_WORKER);
   `acquire` raises `WORKER_LEASE_FAILED_LOCKED` — a FAILED_LOCKED lease file
   can never be overwritten (even for a different target id).
6. **scheduler/base**: `_device_lock_available` returns False when owner
   status == `failed_locked` (re-fire/new trigger skips, never reacquires);
   `_terminal_result_proven(FAILED_LOCKED)` = True with reason+evidence (no
   artifact requirement); `run_consumer` FAILED_LOCKED branch marks the
   scheduler lease `failed_locked`, sets state `failed-locked`, never
   releases.
7. **events**: schema additive by design — no change to events.py/ledger.py.
   FAILED_LOCKED flows as `operation="FAILED_LOCKED"` envelope (published +
   EventLedger ingest) and as the durable queue record event (redacted at
   `_save`). Evidence: reason, signature, attempts, artifact paths if any.
8. **Verification trap**: venv has a STATIC installed automation_core copy ⇨
   all pytest runs need `PYTHONPATH=src` pointing at the WORKTREE src, else
   tests run the installed copy.

## Test map (tests/ files, R-requirements)

- `test_recovery_contract.py`: R1.7 5-source parametrized finalize (fresh
  queue file per iteration!), R1.8 edges/terminal/strict gate/no-artifact
  gate, R1.4 durable redacted event across restart, R1.2 runner restart skip
  (zero detect/lock), R1.1 `_failed_locked_hold` never releases + sets
  `failed_locked`.
- `test_device_lock.py`: retained status + verify lease; not implicitly
  reclaimable; not live-takeover-reclaimable.
- `test_global_recovery.py`: R1.6 mark_terminal/watchdog TERMINAL/acquire
  refusal; stale lease never checkpoint/replace; fresh lease file needed for
  invalid-status check (FAILED_LOCKED lease file cannot be reused).
- `test_scheduler_base.py`: R1.3 `_device_lock_available` blocked,
  `_terminal_result_proven` proven, run_consumer retain-no-release.
- `test_events.py`: envelope operation FAILED_LOCKED + redact_value
  transform round-trip; EventLedger reopen durability.

## Numbers (this build)

RED: 21 failed / 97 passed. GREEN: 118 (5 focused suites) + 18
(mandatory contract) + 50 (preflight/event_processing/core); sweep
excluding the collection blocker: 522 passed, 1 failed
(`test_startup.py::test_android_startup_orders_unlock_rotation_then_recents`
— proven pre-existing on pristine master via `git stash`).

## Pitfalls hit

- patch-tool fuzzy matcher mangled CRLF-file indentation 3× (results.py,
  device_lock.py, global_recovery.py) → repaired each with a python
  exact-replace script (`assert old in text`); full-file write_file for the
  worst case.
- write_file emits LF → normalize to CRLF (`\r\n`→`\n` then `\n`→`\r\n`)
  to keep `git diff --stat` minimal.
- First RED test run silently skipped the new scheduler tests: the append
  loop wrote `tests/test_scheduler.py` (wrong filename) instead of
  `tests/test_scheduler_base.py` — verify the target filename after any
  looped `cat >>`.
- Test bugs vs code bugs: parametrized loop reused one queue file →
  iteration 2+ "target is not reservable"; acquiring after FAILED_LOCKED on
  the same worker-lease file legitimately raises (fix = fresh file, not code
  change); strict-mode finalize needs a reservation token (drive through
  `reserve_handler` in tests).