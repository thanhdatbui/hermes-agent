# Atomic Review Edits and Iteration-Budget Discipline

Use this reference for tightly scoped review-remediation tasks with a required final command.

## Preserve executable test structure

When inserting regression coverage, do not replace a bare function declaration with the test body. A replacement anchor such as `def test_case():\n` can delete the declaration and leave an indented orphan block. Prefer one of these safe shapes:

- insert a complete new test immediately before a unique existing function header;
- replace a complete, uniquely anchored function block including its `def` line and body;
- after every patch, re-read the changed region and confirm every test body still has its `def` declaration.

Duplicate function names and LSP redeclaration diagnostics are stop signals: repair the test file before making another source edit.

## Budget the remediation loop

For an exact two-file allowlist, reserve the execution window explicitly:

1. Read the complete production/test files and capture the baseline focused result.
2. Add one focused RED regression batch and run it.
3. Apply the minimal production fix and run the focused batch again.
4. Re-read both files, inspect the scoped diff, then run the mandated final pytest, compile, and diff checks.

If the tool/iteration budget is too small to complete the final verification window, stop and report **partial/unverified**. Never infer completion from an earlier baseline pass or from a successful patch call.

## Evidence contract

Tests for scoped binding, fallback routing, and telemetry should call the real production functions against `tmp_path`/local Git or mocked HTTP boundaries. Avoid fake-result-only tests for the behavior under review. Keep the user's existing precedence contract in its own regression tests (for example, `NEED_CONTEXT` remains dominant while a valid rubric score remains authoritative over advisory readiness flags).

Final reports must distinguish:

- baseline evidence (before edits),
- RED evidence (proves the new test was live),
- GREEN/final evidence (after the last edit), and
- incomplete work caused by an exhausted execution budget.
