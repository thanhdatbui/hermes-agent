# Workspace identity preflight

Use this before editing a consumer repository when the session cwd or user-provided path may not be the real checkout.

## Procedure

1. Resolve the root from inside the candidate with `git rev-parse --show-toplevel`.
2. Confirm the expected entrypoint and test files exist under that root.
3. Read `AGENTS.md`, then task-relevant `HANDOFF.md` and `PROJECT_RULES.md` before mutation.
4. Record `git status --short --branch` and the scoped `git diff --` as the baseline.
5. If several copies exist, compare exact path, Git metadata, and file presence. Reject installed packages, caches, backups, and temp artifacts as edit targets.
6. Preserve all baseline dirty files. The final diff must be attributable only to the requested scope.

## Windows notes

- Prefer Windows-form forward-slash paths for `git -C`, for example `git -C 'D:/Taadaa/project' status`, when MSYS `/d/...` path conversion is unreliable.
- A shell `cd` succeeding is not proof that a path is the intended checkout; verify with Git and the expected files.
- If the requested path and the verified repository root differ, report the discrepancy explicitly and do not silently claim the requested path was edited.

## Completion evidence

Report the verified root, branch, baseline dirty files, changed files, focused test command/output, compile or diff checks, and whether commit/push occurred. If tool limits or a policy gate prevent edits, report that as incomplete work rather than implying a fix landed.
