# Closeout dirty-scope state machine

## Non-terminal rejection
A reviewer `REJECT` or score below threshold is an active remediation state, not a user-facing session end. Continue `TRIAGE → worker fix → focused verification → exact-scope review → closeout gate`. Use `BLOCKED` only for a genuine external blocker, missing authority/credential, or an irreversible business decision.

## Dirty-tree preflight
Before final review, classify `git status --short` into target, unrelated, generated, and unknown paths. Never submit `git diff HEAD` from a polluted tree. Preserve unrelated work: do not reset, clean, checkout, or revert it. Use a clean worktree, selective stash of explicitly unrelated paths, or an exact target-file diff. Reviewer input must contain the target diff and fresh verification evidence only.

## Required final gate
DONE is allowed only when `closeout_gate.py` exits 0, the verdict is `APPROVED`, and score is at least 85. Keep the default locked Sol High review lane (`model: review` or approved Sol High route); never substitute Pro/Instant shortcuts.

## Worker contract
Give the worker an enumerated file list, exact findings, focused test command, and a no-scope-expansion rule. Require changed-file list, exact test output, and known risks in its return. A low score caused by polluted scope is a remediation signal, never permission to stop.
