# Phase 3 — user-explicit lock open (CLI `lock list/inspect/open`) — 2026-08-11

Plan: `.hermes/plans/2026-08-11_ai-escalation-failed-locked.md` §9 (Phase 3).
Worktree `automation-core-failed-locked-wt`, branch `codex/failed-locked-phase1`.
Commit: `57355ad feat(cli): list/inspect/open FAILED_LOCKED chỉ khi user explicit, redacted, có authorization`
(1 commit, 6 files, +743/−5 — exactly the plan's commit message).

## Surface (public API added)

`src/automation_core/device_lock.py`:
- `DeviceLockOpenAudit` (frozen dataclass): machine, serial, project, reason,
  scope, released_paths, timestamp.
- `list_failed_locked_locks(*, lock_root=None) -> list[dict]` — read-only;
  globs `*.lock.json` (guard/temp files never matched), keeps status
  `failed_locked`, dedupes by `(machine, serial, lock_id)` owner identity
  (one logical lock = machine+serial alias FILES), redacts each payload.
- `inspect_device_lock(machine, serial, *, lock_root) -> dict` — read-only;
  missing/invalid alias → `DeviceLockTransactionError`
  `DEVICE_LOCK_INSPECT_PATH_MISSING` / `_PAYLOAD_INVALID`; consistency via
  `_require_consistent_existing_owner`; redacted owner.
- `open_failed_locked_lock(machine, serial, *, lock_root, project=None,
  takeover_scope=None, takeover_authorized=False, takeover_reason=None)` —
  authorization gate FIRST (any miss → `DeviceLockTakeoverUnauthorized`,
  nothing mutated): `takeover_authorized=True`, non-empty reason, scope in
  {SAME_PROJECT_RECOVERY, FULL_SCOPE_TAKEOVER}. Then per-alias checks:
  protocol==2 (`DEVICE_LOCK_OPEN_PROTOCOL_UNSUPPORTED`), status
  `failed_locked` (`DEVICE_LOCK_OPEN_REQUIRES_FAILED_LOCKED`),
  `owner_active is False` (`DEVICE_LOCK_OPEN_REQUIRES_INACTIVE_OWNER`),
  SAME_PROJECT_RECOVERY ⇒ `owner.project == project`. Deletes aliases under
  `_hold_path_guards` + `_rollback_release_deletions` (same machinery as
  `_release_lease_paths`, no ownership matching — this IS the authorized
  open). Returns `DeviceLockOpenAudit` with released paths.

`src/automation_core/recovery.py`:
- `LOCK_OPENED_BY_USER = "LOCK_OPENED_BY_USER"` (exported in `__all__`).
- `RecoveryQueue.mark_lock_opened_by_user(target_id, *, reason)` — reason
  required (`LOCK_OPENED_BY_USER_REQUIRES_REASON`); record must exist and be
  FAILED_LOCKED (`LOCK_OPENED_BY_USER_REQUIRES_FAILED_LOCKED:<state>`).
  Appends event `{"event": LOCK_OPENED_BY_USER, "reason", "at"}` +
  `evidence["opened_by_user"]`, both redacted, persisted via `_save`.
  Record state REMAINS FAILED_LOCKED — deliberately no transition; the event
  is the durable user-requested-open marker (Phase 1/2 invariants untouched).

`src/automation_core/cli.py`:
- New `lock` area: `list [--lock-dir]`, `inspect TARGET [--lock-dir]
  [--queue] [--target-id]`, `open TARGET --reason TEXT --confirm
  [--scope SAME_PROJECT_RECOVERY|FULL_SCOPE_TAKEOVER] [--project]
  [--lock-dir] [--queue] [--target-id]`.
- `_resolve_lock_identity(target, lock_root)` → (machine, serial): accepts
  `machine:<id>` / `serial:<id>` or raw id; raw matching BOTH aliases →
  "ambiguous", matching none → "no device lock matches" (both ValueError).
- `_run_lock` open flow (order matters, see pitfall below): resolve → if
  `--queue`: fail-fast `RecoveryQueue.get` state==FAILED_LOCKED (no event
  yet) → `open_failed_locked_lock` (the gate) → record
  `mark_lock_opened_by_user` (queue_event.error surfaced in output on
  failure, never swallowed silently, F4 pattern).
- Redaction: output wrapped in `redact_value`; audit emitted with
  `released_path_count` instead of `released_paths` (filenames leak serial);
  `_emit` secret regex extended with `credential`.

## Pitfalls found during development

1. **Gate-before-event ordering.** First draft recorded the queue event
   BEFORE `open_failed_locked_lock` ran → an unauthorized `lock open`
   (missing `--confirm`) with `--queue` would have durably recorded
   LOCK_OPENED_BY_USER even though the open was refused. Rule: the lock-layer
   authorization gate must pass before any audit/event write; pre-gate reads
   (queue state check) are fine.
2. **Alias completeness.** `open`/`inspect` addressed by `serial:<id>` only
   would release/inspect a single alias file and leave the machine alias (and
   vice versa). Fix: `_complete_lock_identity` reads the given alias's owner
   payload and fills the other dimension, so both alias files are covered.
3. **List dedup.** Naive per-file list returned 2 entries for one logical
   machine+serial lock. Fix: dedupe by `(machine, serial, lock_id)`.
4. **`asdict` import.** `cli.py` used `asdict` without importing it
   (`from dataclasses import asdict, dataclass`) — caught by the R3.4 CLI
   test (exit 2 `NameError`), fixed immediately.
5. **search_files on D:\** — tool normalizes `D:/...` → `/d/...`, ripgrep
   errors; use terminal `grep -rn` from the worktree root.

## Test map (RED → GREEN)

RED evidence: collection error `ImportError: cannot import name
'LOCK_OPENED_BY_USER'` in test_cli.py + test_events.py (correct reason:
Phase 3 API did not exist).

- `tests/test_cli.py`: R3.1 list redacted (serial/workbook/credential absent,
  only FAILED_LOCKED listed), R3.2 inspect read-only (lock bytes + queue
  bytes + event count unchanged), R3.3 open refused without confirm/reason
  (exit 2 + `DeviceLockTakeoverUnauthorized`), R3.4 valid open releases both
  aliases + durable LOCK_OPENED_BY_USER + terminal state kept, R3.5 CLI
  surface scan (`recover|retry|auto` absent; `--confirm`/`--reason` only on
  open).
- `tests/test_device_lock.py`: authorization/reason/scope refusals,
  releases only failed_locked (handoff refused), same-project scope
  enforcement, list/inspect read-only + redacted (`command` redacted).
- `tests/test_events.py`: EventEnvelope LOCK_OPENED_BY_USER schema-additive +
  redacted + durable; queue event durable across reopen; reason mandatory;
  non-FAILED_LOCKED refused.

## Counts (real output)

- Baseline: focused (test_cli + test_device_lock + test_events) 86 passed;
  full suite 554 passed, 1 failed pre-existing
  (`test_startup.py::test_android_startup_orders_unlock_rotation_then_recents`).
- After: focused 98 passed (+12); full suite 566 passed, 1 failed — SAME
  pre-existing failure, named, never claimed as new.
- Static gates: `py_compile` on all 6 touched files, `git diff --check`
  clean, `git status` clean after commit.
- Ad-hoc verification: `%TEMP%\hermes-verify-phase3-lock-cli.py` — 41/41
  checks PASS (R3.1–R3.5 end-to-end), deleted after run; reported as ad-hoc,
  not suite green.
