# Closeout Scope and Review Reference

## Closeout decision tree

1. Read the latest user message as the active command.
2. If it says `chốt phiên`/`đóng phiên`, locate the already-requested change; do not resume an older remediation plan.
3. Freeze the exact candidate: commit range, approved files/hunks, tests, review route, and required delivery action.
4. Inspect `git diff` and `git diff --cached` before any staging. Preserve unrelated dirty and staged work.
5. Review only the frozen candidate. A review finding outside the frozen candidate is not permission to expand scope.
6. After acceptance passes, stop. Do not keep auditing for additional hardening opportunities.

## When the user explicitly says “fix until review passes”

Use the exact candidate that was just reviewed. Each loop is:

- record the reviewer route/model and verdict;
- fix only actionable findings in the original allowlist;
- run focused tests and syntax/diff checks;
- re-stage only the allowlist;
- verify staged paths and bytes;
- send the exact staged payload to the same required review route.

Do not substitute an implementation worker or a different model as the review gate. Do not send a broader repository snapshot than the user requested.

## Shared-worktree safety

Multiple agents writing the same checkout invalidate provenance. If a worker, test process, or concurrent commit changes the same file/hunk during the loop:

- stop source edits in the overlapping region;
- preserve the current worktree and index;
- report `SCOPE_CONFLICT` or `VERIFIED_CURRENT_TREE` as appropriate;
- do not reset, clean, stash, normalize line endings, or delete artifacts to make the tree look clean;
- use a separate worktree only after freezing bytes, and do not silently copy the result back into the original checkout.

A passing test on bytes that changed concurrently is evidence about the current tree only, not proof that the requested patch was safely authored or attributable.

## Review payload minimum

The review prompt must state:

- exact file list (and, when relevant, exact commit range/hunks);
- required behavior and acceptance criteria;
- explicit exclusions such as unrelated dirty files, later commits, and adjacent subsystems;
- the required first-line verdict format;
- that the reviewer must judge only the supplied exact bytes.

Record the staged tree hash and staged blob hashes before the call. If any scoped blob changes after staging or review, discard that verdict as stale and re-freeze.

## Style correction learned

For an irritated user asking why work is taking long, answer briefly with the concrete cause and current gate. Do not narrate every wait, worker poll, or speculative next step. State whether the task is `APPROVED`, `REJECTED`, or blocked, and what exact scope was reviewed.
