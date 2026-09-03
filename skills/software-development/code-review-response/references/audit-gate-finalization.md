# Audit gate finalization

Use this after an independent audit produces a formal verdict that controls whether a risky or shared-core change may be staged, committed, pushed, merged, or released.

## 1. Capture a usable verdict

- Retain/read the **complete** auditor artifact or stdout before acting. A process exit code, tool completion notice, timeout wrapper result, or a truncated tail is transport evidence only.
- `exit 0` means the auditor process ended normally; it does **not** mean `APPROVED`.
- If the audit prompt defines an exact framing rule (for example first and last nonempty lines must be `APPROVED`, `MINOR_FIXES`, or `REJECT`), validate that framing literally. Missing, truncated, conflicting, or unparsable framing is **no usable approval**.
- Classify a usable non-approval (`MINOR_FIXES` or `REJECT`) as a new implementation gate, not as a reason to infer success from passing tests.

## 2. Admit findings before changing code

Treat an auditor item as `CONFIRMED_P0/P1` only when it supplies all of:

1. a stable locator (`file:line`, symbol, state transition, or schema key);
2. a runnable production input/branch/state;
3. a concrete production impact; and
4. an executed red reproduction or artifact-backed trace.

Items missing executable evidence are `NEEDS_PROOF`; gather exactly the missing evidence first rather than broad speculative edits. Notes/style observations do not block a release unless the owner explicitly promotes them.

## 3. Fix by invariant, not by finding count

- Group related confirmed findings around one invariant (for example: canonical event identity, replay equivalence, crash recovery, logical-day binding).
- Give one exclusive worker the exact file/component allowlist. Preserve unrelated dirty files and do not broaden scope just because the worktree is dirty.
- Add a focused negative regression for each exploit/forged/crash boundary **before** production changes when practical; the test must exercise the real append/replay/CLI/recovery path, not merely validate a helper or test name.
- A material code or test change invalidates any prior audit verdict. Re-run the audit after the new evidence is produced. If the user requires model continuity, keep the same auditor/model through `REJECT -> fix -> re-audit`.

## 4. Verification evidence is necessary but not approval

After the worker handoff, independently run/inspect:

- the focused regression cases and canonical suite;
- imports/compile or type checks for changed modules;
- `git diff --check` (and formatter/linter when applicable);
- current `git status`, untracked allowlist, and current diff/scope.

Record fresh command output. Earlier green test counts cannot prove a later revision. Tests prove behavior covered by tests; the auditor verdict proves the release gate.

## 5. Release sequence

1. Obtain an explicit final `APPROVED` from the required independent audit.
2. Re-check that the audited diff/scope has not changed since approval. If it has, re-audit.
3. Stage **only** the reviewed allowlisted files; preserve unrelated dirty/untracked work.
4. Inspect staged diff and branch/remote target.
5. Commit/push/merge only when user authorization and repository policy allow it.

Never stage, commit, push, merge, or report ready-to-release based solely on an audit process exit code, a worker self-report, or a test pass.
