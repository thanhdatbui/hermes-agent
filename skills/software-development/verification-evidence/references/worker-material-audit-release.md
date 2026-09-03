# Worker-to-Release Verification Recipe

Use this reference when a delegated worker edits a protected repository and the change must pass an independent audit/release gate.

## Evidence sequence

1. Re-read the live implementation and tests in the parent workspace after the worker reports completion.
2. Check live hashes, `git status --short`, scoped diff, and active worker/process state. Treat transport errors and completion metadata as unverified.
3. Add regression tests for each confirmed fail-open behavior, run them before the fix, and record the genuine RED output.
4. Apply the smallest production/test patch. Run the exact targeted module, full suite, external-temp `py_compile`, EOL/BOM checks, AST test inventory, and `git diff --check`.
5. Audit the exact current uncommitted diff with a read-only auditor. If the verdict is `MINOR_FIXES` or `REJECT`, fix, rerun all required verification, and audit again. Never reuse approval for a later diff.
6. Stage explicit authorized paths only. Confirm protected untracked files remain untracked, commit, push, and verify local `HEAD` equals the remote branch SHA. Run the requested post-push focused smoke.

## Useful acceptance checks for fail-closed UI flows

- Re-bind the exact UID from a fresh dump immediately before side effects and verification; zero or duplicate matches are manual review.
- Prove structural context, not just a shared resource ID: require the correct semantic header, selected tab, and container; valid empty lists need structural proof.
- Require controls to be actionable (`clickable`/enabled) and semantically bound to the intended row.
- Treat state read/write exceptions, scroll failure, and unproven scroll-cap exhaustion as non-success outcomes.
- Keep delay assertions tied to actual later actions; skipped/deduplicated rows must not consume action delay.

## Common false positives

- A worker's isolated worktree or reported hash does not prove the parent checkout contains the patch.
- A green suite does not prove a fail-open invariant is fixed; direct seam probes and an independent diff audit are still required.
- A stale fixture can pass through a structural failure instead of the intended branch. Make fixtures prove the same semantic context that production now requires.
