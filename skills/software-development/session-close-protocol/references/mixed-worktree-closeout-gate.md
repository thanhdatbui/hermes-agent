# Mixed-worktree closeout gate

## Trigger
Use this when the requested fix is focused but the repository contains many unrelated dirty files, runtime-state edits, prior worker changes, or a commit whose diff is broader than the user’s task.

## Procedure
1. Freeze the allowlist: exact production file(s), tests, and runtime artifacts relevant to the request.
2. Inspect the candidate boundary before reviewer execution. A focused pytest pass is evidence for the focused code only; it is not evidence that the whole repository is closeable.
3. Preserve unrelated work. Do not use `git reset`, `git clean`, checkout, or destructive cleanup to hide or remove another worker/user’s changes.
4. If the closeout gate is run by policy, use the exact required command and record the raw reviewer output. Do not substitute a lower bar or self-score.
5. Interpret outcomes separately:
   - focused tests passed: implementation evidence;
   - runtime copy/hash matched: deployment evidence;
   - reviewer APPROVED with score >=85 and exit 0: closeout approval.
6. If reviewer output is REJECTED, score <85, or a timeout yields no verdict, stop: do not push and do not claim the session is closed.
7. Do not retry an unchanged broad diff. Create a genuinely isolated reviewable change set/clean worktree or ask the user to choose how unrelated changes should be handled. Reviewer complaints about unrelated production files are scope evidence, not authorization to fix all of them during closeout.

## Reporting template
- Focused verification: command and result.
- Runtime verification: paths and hash/result.
- Closeout reviewer: verdict, score, exit code or timeout.
- Final state: approved / blocked / rejected; whether push was deliberately withheld.
