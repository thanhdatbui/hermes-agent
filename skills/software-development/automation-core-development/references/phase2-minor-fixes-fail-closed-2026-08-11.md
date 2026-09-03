# Phase 2 MINOR_FIXES F1-F7 — fail-closed hardening (2026-08-11)

Worktree `D:\Taadaa\automation-core-failed-locked-wt`, branch
`codex/failed-locked-phase1` (HEAD `6d83f8c`). Seven MINOR findings from the
Phase 2 re-audit, fixed WITHOUT committing (awaiting re-audit APPROVED).
Files touched: `src/automation_core/recovery_runner.py`,
`src/automation_core/escalation.py`, `tests/test_recovery_contract.py`,
`tests/test_mandatory_recovery_contract.py`, `tests/test_package_metadata.py`.

## Per-finding map (final file:line)

| # | Location | Fix |
|---|----------|-----|
| F1 | `recovery_runner.py` generic `except Exception` tail (~:307) | record None / state outside `_FAILED_LOCKED_SOURCE_STATES` → `_lock_failed` (durable FAILED_LOCKED + `_failed_locked_hold`), NEVER HARD_STOP; error stays in `reason=f"UNEXPECTED_RECOVERY_ERROR:{type}"` + evidence |
| F2 | `recovery_runner.py` `except RecoveryContractError` tail (~:278) | same for non-budget/non-non-retryable contract errors pre-record; trigger `NON_RETRYABLE`/`CONTRACT`; `reason=str(exc) or f"RECOVERY_CONTRACT_ERROR:{type}"` |
| F3 | `recovery_runner.py` `_fail_closed` mark_escalation_required (~:344) | only `"unknown recovery target"` passes; other errors → `_lock_failed` with `escalation_required_error` in evidence (no silent swallow) |
| F4 | `recovery_runner.py` `_append_ai_event` (~:397) | returns error string for any non-"no record" failure; `_fail_closed` collects into `event_errors` → evidence; never raises (raising would abandon the lock) |
| F5 | `escalation.py` `EscalationRegistry.call` (~:154) | dead `for` loop removed; consults ONLY `self._hooks[0]`; no unreachable `return None`; class+method docstrings updated |
| F6 | `recovery_runner.py` `_escalation_pending` (~:413) | lock passed in and held via `_failed_locked_hold` → status `failed_locked` on the ESCALATION_REQUIRED intermediate path (no GC/`__del__` abandonment); lock None → no-op |
| F7 | `tests/test_package_metadata.py` (`wheel_metadata_tools` fixture) | global import-time `sys.modules["tools"]` pin removed; context-safe fixture: `types.ModuleType("tools")` + `__path__=[repo tools]` + `monkeypatch.setitem(sys.modules, "tools", repo_tools)`, import inside fixture, restored after test |

## Key mechanics

- `_lock_failed` (upgraded finalizer, ~:431): record None →
  `queue.reserve(signature or "UNKNOWN_SIGNATURE", root_cause=reason)` →
  DETECTED → `mark_escalation_required` (mints strict-mode reservation
  token+owner) → `transition(CLASSIFIED)` → `finalize_failed_locked(token,
  owner)`. Finalize failure caught (`except Exception`) → result-level
  FAILED_LOCKED + lock held + `finalize_error` in evidence. Non-finalizable
  state (RETRYING) → result-level FAILED_LOCKED (legacy FINAL_BLOCKED
  contract untouched — R1.8).
- Strict-mode token flow: after `mark_escalation_required`, in-memory
  `record.reservation_token` is plain hex; after a `queue.get()` reload it is
  the `sha256:` digest; `_token_digest` is idempotent for `sha256:`-prefixed
  values, so passing `record.reservation_token` as the token works in both
  forms — same pattern as the pre-existing source-state finalize path.
- DETECTED→CLASSIFIED is legal via `_allowed()`; CLASSIFIED is a
  `_FAILED_LOCKED_SOURCE_STATES` member, so `finalize_failed_locked` accepts
  it (strict gate: terminal requires completion gate — `finalize_failed_locked`
  IS the sanctioned path).
- `_fail_closed` NON_RETRYABLE short-circuits straight to `_lock_failed`
  (no mark, no STARTED event, no hook) — unchanged contract (R2.11).

## Test changes

- `test_mandatory_recovery_contract.py`: `test_unexpected_worker_exception_moves_lock_to_handoff`
  (HARD_STOP + `["handoff"]`) → `test_unexpected_worker_exception_fails_closed_to_failed_locked`
  (FAILED_LOCKED, `RuntimeError` in reason, durable queue state, lock
  `["failed_locked"]`, released False, strict queue).
- `test_recovery_contract.py` (4 new):
  - `test_contract_error_before_record_fails_closed_to_failed_locked` (F2 — classifier raises)
  - `test_mark_escalation_required_error_is_not_swallowed` (F3 — instance-shadows `mark_escalation_required`)
  - `test_ai_event_append_error_is_not_swallowed` (F4 — instance-shadows `append_event`)
  - `test_escalation_pending_holds_lock_explicitly` (F6)

## Verification protocol used (user's gate)

- `PYTHONPATH=src python -m pytest <7 files> -q` → 161 passed
  (baseline 156 + 4 new; F1 test replaced in place).
- `PYTHONPATH=src python -m pytest -q` → 554 passed, 1 failed —
  `test_startup.py::test_android_startup_orders_unlock_rotation_then_recents`
  is PRE-EXISTING (baseline 550+1); no new failures.
- `python -m py_compile` on all 5 edited files; `git diff --check` clean;
  `git status` shows exactly the 5 Phase 2 files; NO commit.
- Ad-hoc `hermes-verify-` script under `%TEMP%` (tempfile path) asserting
  F1-F7 behaviors directly (27-28 checks, all PASS), deleted after run;
  reported as ad-hoc verification, not suite green.

## CRLF patch-tool incident (this session)

The `patch` tool's fuzzy matcher re-indented whole multi-line blocks TWICE on
CRLF files (recovery_runner.py `_fail_closed.._lock_failed` got +4 indent;
escalation.py `call` body got +8), each producing IndentationError. The fuzzy
matcher misbehaves when the new_string's first line has LESS leading
indentation than the matched old_string line (it adds the difference to every
subsequent line). Recovery: rebuild the exact line range with a small python
repair script (prefix/suffix slices + correct block + write) or rewrite the
whole file with write_file — do NOT stack more patches. Always `py_compile`
afterwards. (CRLF recipe details: `code-review-response` §8.)
