# Canonical Binding and Reviewer Remediation

Use this reference when `closeout_gate.py` reviews a dirty or multi-commit candidate.

## Failure patterns

1. **Never silently narrow an unresolved base.** If `base_ref` (especially `origin/main`) cannot resolve, fail closed with an explicit base-resolution error. Do not substitute `HEAD~1..HEAD` or the empty-tree range; that can omit older commits.
2. **One canonical diff identity.** Extraction, binding, pre/post-test rechecks, and reviewer metadata must hash the same canonical Git diff bytes with identical hermetic flags. Do not hash decoded/re-encoded UTF-8 in one path and raw bytes in another; binary diffs then produce false mismatches.
3. **Binding checks verify content, not only scope.** For every mode (`staged`, `worktree`, targeted modes, and committed modes), recompute the current diff SHA and compare it to `binding.diff_sha256`; validate `commit_sha == head_sha == current HEAD`, exact scope, and `scope_hash`.
4. **Staged overlap is fail-closed at every boundary.** Reject both initial extraction and later binding rechecks when a staged path also has unstaged edits.
5. **Targeted mode is scope-local.** `worktree_targeted` and `committed_targeted` may ignore unrelated dirty paths, but must validate exact target scope and the same `base_ref` range used by extraction.
6. **Normalize integrity failures.** If reviewer SHA, final binding, or TOCTOU validation fails after a high reviewer score, force `passed=false`, a rejecting verdict, and persisted score `0`; print the final summary only after all binding checks.

## Verification recipe

- Run the focused integration suite after the last source/test edit.
- Run `py_compile` on both scoped Python files and `git diff --check`.
- Add real temporary-Git tests for missing base with multiple commits (reject), explicit valid base covering multiple commits (accept), staged overlap after extraction (reject), binary diff identity parity, and tampered `diff_sha256` (reject).
- Treat generic full-suite/E2E requests as coverage findings unless the task contract explicitly includes them; do not expand the two-file candidate scope merely to improve a reviewer score.

## Operator communication

Closeout Gate may spend minutes waiting on the independent reviewer. When the user is frustrated by the delay, give a short factual status: focused-test result, reviewer stage, current score/verdict, and the exact remaining defect. Do not repeat long historical logs or imply completion before `APPROVED >=85` and exit code 0.
