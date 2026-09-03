# Commit-Scoped Phase Acceptance

Use this reference when a user asks for an independent, read-only verdict on one commit against an approved implementation-plan phase.

## Evidence table

| Gate | Probe | Evidence to record |
|---|---|---|
| Commit scope | `git diff-tree --no-commit-id --name-status -r <commit>` | Exact path/status list; compare with phase file list |
| Committed source | `git show <commit>:<path>` | Function/constant/test locators from the committed blob, not a dirty worktree guess |
| Current-state residuals | Read callers/tests outside the commit | Distinguish pre-existing/deferred code from commit-introduced defects |
| Boundary behavior | Disposable Python probe | One newly-valid and one newly-invalid boundary through both model and operational caller |
| Test matrix | AST/count probe + exact pytest command | Parameter count, reserved cases, special marker count, fresh pass output |
| Static gates | Exact `py_compile` and `git diff --check` commands | Exit status and warnings |
| Workspace hygiene | `git status --short`, `git diff --name-only` | Confirm audit did not modify protected worktree content |

## Boundary-mismatch pattern

A green suite can preserve an obsolete hard-coded guard. For a window migration, probe both sides:

```python
# Example shape; adapt imports and fixtures to the repository.
model_accepts_new_boundary = is_in_logical_window("<newly-valid>", day)
model_rejects_after_end = is_in_logical_window("<newly-invalid>", day)
caller_result_at_new_boundary = call_runner_or_watcher("<newly-valid>")
caller_result_after_end = call_runner_or_watcher("<newly-invalid>")
```

Report the pair, not just a grep hit. A mismatch such as `model=True` but `runner=ACTIVE_MANIFEST_CONFLICT` proves an operational invariant gap even when all existing tests pass.

## Deferred-phase discipline

If the plan explicitly schedules the caller fix in a later phase, cite both locators:

- current residual: `path/to/caller.py:<line>` or `path/to/test.py:<line>`
- deferred plan step: `.hermes/plans/<plan>.md:<line>`

Do not attribute the residual to the audited commit if it predates the commit. However, if the user requires the invariant globally at the current gate, do not return `APPROVED`; use `MINOR_FIXES` or `REJECT` and state whether Phase 2 should be blocked.

## Read-only safety

- Never patch the repository during this audit.
- `git show` and commit-object inspection are the source of truth for commit scope.
- Treat untracked files as having no Git baseline; report them separately and leave them untouched.
- Run the final status check after every disposable probe or compile command.

## Adversarial-test branch-reachability probe (committed tests vs plan tests)

A Phase commit's adversarial tests can be fully green while exercising a different branch than their docstrings claim. Worked case (Phase-7 fleet account-block audit, commit 6a49d51, 2026-08): `test_no_session_outside_assigned_block` claims to exercise the cross-block pair-gap loop, but its mutation moves a foreign session's `slot_time`/`slot_end` without rehashing dependent ids, so validation rejects earlier at the entry_id formula check in `_validate_entry` (`entry_id_for` hashes slot_time; mismatch → `MANIFEST_IDENTITY_MISMATCH`). Both a `sys.settrace` line probe and a monkeypatch wrapper proved `_validate_block_structure` never ran. Because the earlier gate still enforces the same invariant (a moved session is a different entry), this is a documented NIT, not a gate-masking REJECT.

Recipe:

1. **Monkeypatch-wrap the suspected branch** — more robust than `sys.settrace` line-tracking (survives refactors, no per-line instrumentation):
```python
called = []
original = manifest._validate_block_structure
def wrapped(*args, **kwargs):
    called.append(True)
    return original(*args, **kwargs)
manifest._validate_block_structure = wrapped
try:
    manifest.validate_manifest(payload, source)
finally:
    manifest._validate_block_structure = original
print("intended branch reached:", bool(called))
```
2. **Slot-time mutations silently redirect to the entry_id gate.** `slot_time`/`slot_end` participate in `entry_id_for(manifest_id, account, machine, serial, account_row, slot_time, action_type, seed, block_id, session_index)`. To reach block-structure branches (pair-gap loop, inter-block gap, entry_ids order), a mutation that moves slots MUST also rehash the entry's `entry_id` + `idempotency_key` (and the block's `entry_ids`) — otherwise the test is GREEN while asserting a different branch.
3. **Classification rule:** an earlier-gate rejection is a NIT when that gate genuinely enforces the invariant the test names (canonical binding of the mutated field). It is gate-masking only when the earlier gate fires for an unrelated structural reason (topology/shape/required-set) and the intended invariant would go unenforced. Asserting the exact expected `ReasonCode` (not a bare `pytest.raises`) is what lets you make this call.
4. **Assertion softening vs plan:** when the committed test relaxes a plan assertion (worked case: `set(skipped) == {"acct-7","acct-8","acct-9"}` → `>=`), re-derive real semantics by probing the picker directly with a disposable script before flagging a deviation. The 9-account fixture skips EVERY out-of-lane account (rows 4–9 are all outside lane A) → 6 `CAPACITY_EXCEEDED` entries, so the committed `>=` matches reality and the plan's exact-set expectation was itself wrong.
5. **Conditional docs steps ("Nếu X tồn tại thì update"):** verify the named doc targets exist AND contain the named section before reporting a missing doc update as MINOR. Worked case: root `README.md` absent, `AGENTS.md` has no P1-harness section, `python_runner/README.md` has no scheduler section ⇒ the docs skip is correct per the plan's own condition, not a finding.
