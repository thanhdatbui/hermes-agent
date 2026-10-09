# Staged Candidate Threshold Remediation Checklist

Use for a rejected closeout candidate where a completion/reservation/download threshold is inconsistent.

1. Bind the repository with `git -C <native-root> rev-parse --show-toplevel`.
2. Record `git status --short`, `git diff --cached --name-only`, and `git diff --name-only` before edits. Treat unrelated paths as protected.
3. Inspect both staged and worktree diffs for every allowlisted file; do not normalize or rewrite whole files.
4. Define one authoritative threshold (prefer a named constant where modules share it) and trace every producer/consumer: database query, progress summary, CLI defaults, command builder, validation, reservation/top-up, and completion status.
5. Search only the allowlisted files for stale threshold literals and stale documentation. Distinguish intentional boundary-test values from production behavior.
6. Add focused tests for values immediately below, at, and above the boundary. Assert both outcomes and telemetry. Add a mocked orchestration test across command construction and the downstream decision seam when feasible.
7. Preserve existing useful telemetry; add explicit events for status/threshold mismatches and every reservation/top-up decision.
8. After the final edit, run the exact required pytest modules with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` when third-party plugins are irrelevant, then run scoped `git diff --check` and `git diff --numstat`.
9. Re-check status and the allowlist. Report staged versus unstaged changes separately; do not commit unless explicitly authorized.

## Common closeout failure

Changing the rescan gate alone is insufficient if the downloader's `--min-videos`, launcher default, or reservation fallback still uses another value. A passing happy-path test can hide this; boundary tests at every requested value are the acceptance evidence.
