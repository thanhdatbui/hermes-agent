# Business stop vs technical failure

Lessons from the FOLLOW_FAILED cleanup/result-contract debugging session.

## Contract

- `FOLLOW_FAILED` is a deliberate terminal business state: Path B proved TikTok released the follow. Stop the current run, attempt app cleanup, record the daily cooldown/state, and suppress the normal technical alert/retained handoff. Do not classify it as `MANUAL_REVIEW` merely because the status contains `FAILED`.
- Cleanup failure is different: a missing cleanup method or exception while closing the app is `CLEANUP_FAILED`, must fail closed, preserve evidence, alert under policy, and return a non-zero exit code. Never swallow it.
- If cleanup can mutate status/reason/failed, assign the helper's return value back before serializing `FOLLOW_RESULT` and computing the exit code. Ignoring the return loses `CLEANUP_FAILED`.

## Debugging and verification

1. In a dirty/shared worktree, inspect `git status --porcelain=v2`, `git diff`, and `git diff --cached` separately. Treat staged and unstaged hunks as distinct candidate bytes.
2. If another writer changes the overlapping file/region, stop source edits there. Do not reset, unstage, replay, or overwrite; only perform read-only verification against the current tree.
3. After each patch to a large Python module, run `py_compile`/AST parsing before interpreting pytest output. A partial patch or indentation error is a structural failure, not a reason to weaken assertions.
4. Focused regression coverage should include: clean `FOLLOW_FAILED` cleanup and exit semantics; cleanup exception/missing callable promotion; `MANUAL_REVIEW` preservation; and CLI result serialization.

## Common pitfall

A test double that lacks an optional cleanup method can conceal the real production contract. Either model the adapter seam explicitly in the fixture or make the production contract unambiguous; do not silently turn missing required cleanup into success unless the interface explicitly defines cleanup as optional.

## CLI result-contract checklist

- Keep three concerns separate: business status (`OK` / `FOLLOW_FAILED`), technical failure (`CLEANUP_FAILED` / `MANUAL_REVIEW`), and process exit code. A business stop may have a non-empty reason and still return exit code 0; technical cleanup failures must remain non-zero.
- For a bounded post-progress navigation stop, classify the evidence envelope before alerting: `MANUAL_REVIEW` with `followed_count > 0`, empty `failed_ids`, and a valid `FOLLOW_RESULT` is a handled business-flow review and must not call the red farm alert. Zero-progress/manual, failed IDs, malformed/missing result, timeout, cleanup failure, or identity/security ambiguity remain fail-closed and alertable.
- `returncode != 0` alone is not sufficient evidence for a red alert; subprocess exit, result status, verified progress, and failure IDs must be evaluated together.
- If a cleanup helper can promote a result, always serialize and compute the exit code from the returned object, not the pre-cleanup object.
- When a focused test fails in a shared dirty tree, first identify whether the failure is from current unstaged bytes, pre-existing staged bytes, or an overlap. Never “fix” it by resetting or staging the whole tree.
- Run the smallest regression set first, then syntax/diff checks. A transient `IndentationError` after a partial write is evidence of an incomplete edit; repair/verify structure before interpreting behavioral test failures.
- Preserve negative coverage: cleanup must not run for `MANUAL_REVIEW` or unrelated technical failures, while real cleanup exceptions must produce `CLEANUP_FAILED` rather than being swallowed.

## Reporting discipline

For incident fixes, report only: purpose, confirmed root cause, changed scope, exact verification counts/status, and blocker. Do not claim a live canary or farm-wide fix from offline tests; label live evidence separately and stop when the scoped acceptance checks pass.