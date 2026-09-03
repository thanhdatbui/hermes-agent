# AI escalation hook core — Phase 2 design record (2026-08-11)

Plan: `.hermes/plans/2026-08-11_ai-escalation-failed-locked.md` §8. Branch
`codex/failed-locked-phase1`, worktree `automation-core-failed-locked-wt`.
Commits: `9e592af` (task 2.0 baseline fix), `6d83f8c` (hook core).

## Scope guardrails honored

- Core = hook/state/event only: NO agent spawn, NO subprocess/agent-CLI
  import, NO AI-provider call, NO credential read (R2.6 static scan over
  escalation.py / recovery.py / recovery_runner.py / results.py / events.py /
  global_recovery.py).
- No consumer/cli/Phase-1-logic edits; no live/ADB/credential ops; offline
  verification only.
- `test_startup.py::test_android_startup_orders_unlock_rotation_then_recents`
  fails pre-existing (verified in the pre-Phase-2 baseline full run) — never
  "fixed" out of scope.

## escalation.py surface (new module)

- `DEFAULT_ESCALATION_BUDGET = 3` (I8; consumer may tighten, never loosen).
- Event name constants: `ESCALATION_REQUIRED`, `AI_ESCALATION_STARTED`,
  `AI_ESCALATION_SUCCEEDED`, `AI_ESCALATION_FAILED`
  (also mirrored in `events.ESCALATION_EVENT_NAMES`; hash formulas unchanged).
- `EscalationOutcome` (SUCCEEDED/FAILED/TIMEOUT), `EscalationResult` with
  `proof_backed` property = SUCCEEDED AND recapture is not None AND
  verifier.passed AND verifier.proof non-empty. SUCCEEDED alone NEVER
  releases (I4).
- `EscalationRegistry`: register/call/unregister; `call` consults hooks in
  registration order, first result authoritative; evidence + reason redacted
  via `redact_value` BEFORE hooks run; hook exceptions wrapped into
  `EscalationResult(FAILED, note="HOOK_RAISED:<Type>:...")` — fail-closed,
  never propagated.
- Imports only stdlib + `.redaction` + `.results` + `.recovery_artifacts`.

## Trigger routing (runner `_fail_closed`)

| Trigger | Route |
|---|---|
| NO_HANDLER (reserve_handler / registry.require) | emit ESCALATION_REQUIRED → hook → outcome |
| HARD_STOP disposition (pre-reservation) | hook (trigger HARD_STOP) → outcome |
| Generic exception from reserve/start/recapture/verifier | hook (trigger UNKNOWN); error kept in reason/evidence (never swallowed) |
| NON_RETRYABLE (`NonRetryableFailureError` type) | FAILED_LOCKED DIRECTLY — hook NOT consulted |
| Preflight missing handler (per-target) | hook (trigger PREFLIGHT_NO_HANDLER) → blocked or proceed |
| No hook / hook FAILED/TIMEOUT / SUCCEEDED without proof | FAILED_LOCKED + `_failed_locked_hold` (lock kept) |
| Proof-backed SUCCEEDED | `AI_ESCALATION_SUCCEEDED` event + intermediate `FinalResultStatus.ESCALATION_REQUIRED` result (adapter completes via normal pipeline later) |
| Budget exhausted (pre-RETRYING) | Phase 1 path unchanged (FAILED_LOCKED) |

Post-recovery HARD_STOP (record in RETRYING) KEEPS the legacy
`finalize_blocked` → FINAL_BLOCKED path — FAILED_LOCKED is unreachable from
RETRYING by design (R1.8). Pre-reservation generic exceptions (detect raises
before any queue record) stay HARD_STOP + handoff (existing contract test
`test_unexpected_worker_exception_moves_lock_to_handoff`).

## Key design decisions

1. **No new `RecoveryState.ESCALATION_REQUIRED`.** Plan said "(nếu cần)".
   A new pre-RETRYING state would force `_FAILED_LOCKED_SOURCE_STATES` AND
   the R1.7 parametrize helper `_drive_to_state` (tests) to change → breaks
   APPROVED Phase 1 tests. Escalation is signaled by the durable
   `ESCALATION_REQUIRED` event + hook outcome; state machine untouched.
2. **`NonRetryableFailureError(RecoveryContractError)`** — routes NON_RETRYABLE
   by exception TYPE (F-3 pattern: type routing, never message parsing).
3. **Strict-mode finalize from CLASSIFIED (NO_HANDLER)** — no handler was
   ever reserved, so `record.reservation_token`/`owner_id` are empty and
   `_require_reservation` would reject `finalize_failed_locked`.
   `mark_escalation_required` assigns a fresh token + owner (the escalation
   path owns the target); `_lock_failed` finalizes with
   `record.owner_id or self.owner_id`.
4. **Preflight isolation** — `preflight()` now returns `dict[target_id,
   NO_HANDLER message]`; blocked targets get the hook / FAILED_LOCKED and
   NEVER run detect/lock; remaining targets run normally. Batch-level errors
   (DUPLICATE_TARGET_ID, TARGET_VERIFIER_REQUIRED) still raise. Return-value
   change is backward compatible (old callers ignore it).
5. **`events.py` "optional fields"** — escalation events carry optional
   payload fields (trigger/failure_class/signature/evidence...); nothing was
   added to `EventEnvelope.body()` because that would change content_hash of
   OLD stored events (backward-compat break). Payload-only, schema additive.
6. **Runner `run()` defensive path** changed from HARD_STOP to FAILED_LOCKED
   for a worker error escaping `_run_one` (unreachable in practice).

## Test map (all green, PYTHONPATH=src)

- `tests/test_escalation.py` (new, 10): registry contract, budget==3,
  redaction-before-hook, hook-raise → FAILED, proof_backed matrix, R2.6
  no-spawn scan, pure-imports (ast walk of import nodes).
- `tests/test_recovery_contract.py` (+7): R2.1 (NO_HANDLER event, no retry),
  R2.2 (no-hook → FAILED_LOCKED, lock held), R2.5 ×2 (HARD_STOP no-hook +
  hook-trigger), R2.8 (budget → FAILED_LOCKED, cap not reset on re-fire),
  R2.10 (generic recapture exception → FAILED_LOCKED, error in reason),
  R2.11 NON_RETRYABLE.
- `tests/test_mandatory_recovery_contract.py` (+7): R2.9 ×2 (preflight
  isolation no-hook + hook-consulted; B/C unharmed), R2.3 (success without
  proof refused), R2.4 (FAILED/TIMEOUT ×2 + hook-raise), NON_RETRYABLE never
  consults hook.
- `tests/test_events.py` (+1): R2.7 escalation envelope schema-additive +
  redacted payload, hash verifies after re-read.

## Verify evidence (real counts)

- RED: 3 collection errors (`ModuleNotFoundError: automation_core.escalation`)
  + 1 events runtime ImportError (ESCALATION_EVENT_NAMES).
- GREEN focused: 148 passed (recovery_contract + mandatory + device_lock +
  events + escalation); 156 with global_recovery; 44 adjacent regression.
- Full `PYTHONPATH=src python -m pytest -q`: 550 passed, 1 failed
  (pre-existing test_startup).
- Static: py_compile all changed files, `git diff --check` clean, tree clean.
