# Lock lifecycle map + always-release direction (2026-08-16)

## Context

User ordered removal of lock mechanisms on the repos (logs kept failing on
stale locks: "cơ chế lock quá nhiều") and is evaluating a mutex-style policy:
**lock while running, ALWAYS release when done — success, fail, or block**.
Design NOT yet finalized (3 open questions at the end) — a future session
continues from here; never implement before the user confirms the scope.

## Where the lock mechanisms live (verified 2026-08-16)

- `src/automation_core/device_lock.py` (1516 lines) — CANONICAL:
  - `DeviceLockLease` (:196): `finish(succeeded=False, failure_status="handoff")`
    → `set_status("handoff")` RETAINS the lock (:249-254);
    `__exit__` with an exception → also `set_status("handoff")` RETAINS
    (:259-271); `release()` / `release_with_audit()` delete the lock files.
  - `acquire_device_lock(user_authorized=...)` (:369): Phase 4 gate — `False`
    ⇒ no-op `_UnlockedDeviceLockLease` (NO lock file) when target free,
    `DeviceLockNeedsUserDecision` when a lock EXISTS (never silent skip).
  - `DeviceLock` compat class (:534) + `finish` (:602) — legacy object-style
    adapter; `__exit__` (:617) skips if status already recovery/handoff/blocked.
  - FAILED_LOCKED terminal + `open_failed_locked_lock` (Phase 3, :748) — the
    ONLY door out of a retained `failed_locked` lock.
  - `_release_lease_paths` (:1163) does the actual delete with guards +
    ownership-claim checks.
- `src/automation_core/locks.py` (301) — COMPAT adapter: `FileLease` (:88) +
  `DeviceLockLease` (:210) + `acquire_device_lock` (:262) which DELEGATES to
  device_lock.py (`from .device_lock import ... canonical_acquire`). Old
  `__exit__` (:247-255) → `update(status="handoff", owner_active=False)`
  retains. Callers catching `LeaseUnavailable` still work (mapped from
  canonical `DeviceLockUnavailable`). Note: classic `_queue_promotion`/
  `_takeover_payload` logic lives only in device_lock.py, NOT locks.py.
- `scheduler/base.py` `run_consumer` (:298-395) — scheduler-level non-overlap
  lock: `DeviceLock(serial, machine, project, status="running")` (no
  `user_authorized` kwarg — always real lock; only created when
  cfg.machine/serial set). Completion policy:
  - terminal FAILED_LOCKED → `lease.set_status("failed_locked")` RETAIN;
  - `_terminal_result_proven` → `lease.release()`;
  - `batch_manages_target_locks and not timed_out and not crashed` →
    `release()` with reason (child owns target locks);
  - else → `set_status("recovery" or "handoff")` +
    `awaiting-verified-terminal-result` RETAIN — the
    `_resume_batch_after_unverified_completion` gate (:405) is the only way
    back to rescheduling.
- `recovery.py` — ~15 `lease.release()` sites; FAILED_LOCKED finalizers
  (`finalize_failed_locked`, `_lock_failed`) deliberately retain by contract.
- `recovery_runner.py:526` — `lock.release()`.
- **Tiktok_Reg has its OWN `device_lock.py` copy** (NOT automation-core):
  `user_authorized=False` DEFAULT (line 117), `DEVICE_LOCK_ENABLED=1` env
  enables compat mode, statuses {"queued","running","recovery","handoff",
  "blocked"}; `_run_all_targets.py` reservations call
  `finish(succeeded=(final_state=="VERIFIED_SUCCESS"), failure_status="blocked")`
  → failure RETAINS as blocked.
- `tiktok-luot nuoi acc`: whole device-lock/prior-evidence mechanism DELETED
  (user 16/08) — see `taadaa-farm-ops-rules` §3 + `tiktok-feed-session` refs.

## Stale-lock root causes (why runs keep getting eaten)

1. `finish(succeeded=False)` → handoff: FAIL = lock retained until manual
   `lock open` (only success releases).
2. Lease `__exit__` on ANY exception → handoff: crash mid-run retains the lock.
3. FAILED_LOCKED terminal retains by design (Phase 3 user-explicit open).
4. Scheduler `else` branch (no terminal proof) → recovery/handoff retain and
   the scheduler gate holds the next run until manual recovery.
5. Two lock layers (scheduler + consumer child) both must release — one
   forgetting leaves a stale file that blocks every later run.

## KEY INSIGHT — single-point change

Every layer (scheduler, recovery_runner, recovery, legacy locks.py, consumer
compat shims) routes terminal decisions through `DeviceLockLease.finish()` /
`release()` / `__exit__` in **device_lock.py**. Changing `finish()` semantics
there (e.g. a `release_always=True` mode) or making `__exit__` always release
propagates to the whole stack without editing each caller. Do NOT patch the
Tiktok_Reg copy the same way unless the user asks — it is a separate repo
with its own tests.

## Proposed design (user direction — chưa chốt)

"Chạy thì lock, xong gỡ — success/fail/block đều gỡ" = mutex thuần
(1 máy 1 script 1 lúc, không giữ trạng thái fail bằng lock).

Draft: new kwarg `release_always: bool = False` on acquire/lease lifecycle;
automation callers pass True → `finish()` / `__exit__` / exception path
ALWAYS release. `user_authorized=True` (explicit operator lock) keeps legacy
retain semantics so the user can still lock a machine by hand when needed.

## Open questions (pending user answer — hỏi lại trước khi làm)

1. FAILED_LOCKED / recovery-contract fate: if always-release, FAILED_LOCKED,
   `finalize_failed_locked`, `lock list/inspect/open` CLI become obsolete —
   large removal scope (Phases 1-3 invariants + their tests).
2. Failure reporting home after release: machine-fail info must live in
   logs/artifacts/state file so cron re-runs are not blocked AND failures
   stay visible (no lock file to point at).
3. Tiktok_Reg legacy manual lock (`DEVICE_LOCK_ENABLED`) — keep, or mutex-only?

Test surface to expect when implementing: `tests/test_device_lock.py`
(1722 lines), `tests/test_user_lock_gate.py` (75), `tests/test_cli.py` (270).