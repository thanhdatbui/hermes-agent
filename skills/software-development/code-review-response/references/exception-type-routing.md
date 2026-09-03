# Exception-Type Routing: replacing `str(exc) == "LITERAL"` matching

Session: automation-core-failed-locked worktree audit fix (finding F-3), Aug 2026. Branch `codex/failed-locked-phase1`, uncommitted Phase 1 diff, 11 allowed files, no consumer/live/credential changes, no commit.

## The finding

`except RecoveryContractError as exc:` contained `... and str(exc) == "MEANINGFUL_ATTEMPT_BUDGET_EXHAUSTED"` to route a budget-exhausted error into a FAILED_LOCKED fallback (fail closed, hold device lock). Fragile: any future message change silently falls through to HARD_STOP — exactly the failure the finding predicts.

## The fix shape (backward-compatible)

1. Add a subclass beside the base error in the same module:

   ```python
   class RecoveryBudgetExhaustedError(RecoveryContractError):
       """Raised when the meaningful-attempt budget is exhausted."""
   ```

2. Switch EVERY raise site to the subclass but KEEP THE MESSAGE STRING IDENTICAL:
   `raise RecoveryBudgetExhaustedError("MEANINGFUL_ATTEMPT_BUDGET_EXHAUSTED")`.
   `str(exc)` is unchanged → any `except BaseError` still catches it, any `pytest.raises(BaseError, match="...")` still matches. Grep the whole tree for other string-matchers on the literal BEFORE changing (`grep -rn "LITERAL" --include="*.py" .`) — this session only recovery_runner.py matched it; tests used the string only as a reason payload, never as a matcher.

3. Route the handler with `isinstance(exc, RecoveryBudgetExhaustedError)` — never `type(exc) == ...` (subclass instances must still route).

4. Add the new name to `__all__` if the module exports one.

5. Same-pass sibling finding (F-2): add an explicit guard at the top of the release helper:
   `if result.status == FinalResultStatus.FAILED_LOCKED: return result` — makes the fail-closed invariant visible and future-proof even when the status set below doesn't include it today.

## Reachability trace before declaring a branch dead

The audit hint said the except-branch might be dead (the main-loop budget check already calls `finalize_failed_locked` directly). Trace EVERY raise site through the state machine:

- Default policy `max_meaningful_attempts=8`: the loop's `record.attempts >= max` check fires BEFORE the loop-back to `reserve_handler`, so `reserve_handler`'s budget raise is unreachable → the except-branch LOOKS dead in the default config.
- `max_meaningful_attempts=1`: `reserve()` sets `attempts=1` → `reserve_handler` raises budget at CLASSIFIED → the except-branch IS alive.

Conclusion: keep the branch, make it precise (isinstance), add the reachable-config test. Document the edge: a budget raise from `reserve_handler` happens BEFORE any reservation token exists, so `finalize_failed_locked(reservation_token="")` would fail in a strict queue — acceptable, note it rather than engineering around it.

## Regression tests (both proved the fix)

1. **End-to-end reachable path**: queue with `RecoveryPolicy(max_meaningful_attempts=1)`, registry with a registered handler, failing `detect` → runner returns `FAILED_LOCKED`; queue record durably `FAILED_LOCKED`; fake lock `statuses == ["failed_locked"]` and not released.
2. **Message-independence** (the real proof): handler raises `RecoveryBudgetExhaustedError("budget cap reached before recapture")` — a NON-literal message — → runner still returns FAILED_LOCKED, never HARD_STOP. This test FAILS on the old `str(exc) == literal` code and passes after.

## Verification protocol (per the audit task spec)

- Task-specified pytest command (6 files, `PYTHONPATH=src python -m pytest ... -q`) → 138 passed (136 baseline + 2 new).
- `py_compile` on every touched file; `git diff --check` clean (0 whitespace errors, 0 "No newline at end of file" markers); `git status --short` == exactly the allowed file set (11 files), nothing committed.
- Trailing-newline finding (F-4): probe `tail -c 3 file | od -An -tx1` for the missing `0a`; append `\r\n` (repo is CRLF, `core.autocrlf=true`) via binary write; verify all touched files are byte-pure CRLF (`n_crlf == count("\n")`).
- Full-suite extras: pre-existing unrelated failures must be attributed, not hidden — `test_startup.py` ordering test (startup module not in the allowed set, no recovery imports) and a `tools.verify_wheel_metadata` collection error are environment/base issues; report them as such and never claim suite green when it isn't.
