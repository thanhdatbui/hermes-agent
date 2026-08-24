# Cross-session closeout reconciliation

Use this checklist whenever a review, canary, commit, or push spans more than one Hermes session, worktree, or background process.

## Before reporting a blocker or completion

1. Resolve the exact target path. Run from that path:
   - `git rev-parse --show-toplevel`
   - `git status --porcelain=v2 --branch`
   - `git rev-parse HEAD`
   - `git log -1 --decorate --oneline`
   - `git rev-parse --abbrev-ref --symbolic-full-name @{upstream}` (when configured)
   - `git show --stat --format=fuller HEAD`
2. Compare `HEAD` with the tracked remote branch. A clean tree with `HEAD == origin/<branch>` means the target may already be landed even if this session still has an older dirty candidate narrative.
3. Inspect the current commit's actual diff (`git show <current-commit> -- <allowlist>`) before relying on an older candidate or review artifact.

## Stale candidate rule

- A temporary clone/worktree and its review are evidence only for its exact bytes.
- If another session advances the coordinator target, mark older candidate reviews stale. Do not apply candidate findings to the new commit and do not patch the old candidate into the live target.
- Rebuild the review prompt from the current commit or current dirty diff and obtain a verdict for those exact bytes.
- Preserve a landed commit; never reset, stash, clean, or overwrite it merely to reconcile session state.

## Process and reviewer classification

- Wrapper path errors, missing binaries, interrupted waits, missing child-process environment, HTTP auth/route/timeout failures, and empty/unparseable output are transport/setup states, not code verdicts.
- A reviewer gate is consumed only by a parseable `APPROVED`, `MINOR_FIXES`, or `REJECT` for the exact current bytes.
- If a reviewer process is silent, inspect the beginning of its output and artifacts before terminating it. If it is demonstrably stuck, classify the result as `AUDIT_TRANSPORT_*`, stop that route, and use the configured fallback—not a guessed verdict.

## Final evidence tuple

Record together:

- target absolute path, branch, current HEAD, and remote SHA;
- exact commit/diff reviewed and reviewer model/route;
- canary artifact and final status;
- focused/full test result, including unrelated pre-existing failures;
- working-tree status and push verification.

A previous session's self-report is a hint only; the current target and exact artifacts are authoritative.
