# Index Scope and Verdict Failures

## Reusable failure pattern

A closeout run can reject before review when `--files` does not exactly equal the staged set. Repeatedly staging/unstaging through a helper probe is unsafe in a shared worktree: it can alter another workstream's index and still fail to resolve the underlying scope mismatch.

## Safe procedure

1. Capture `git status --short` and the staged path list.
2. Treat staged paths and working-tree paths as separate evidence; do not infer ownership from filenames alone.
3. If the staged set is mixed, preserve it and report the mismatch. Ask the owner/operator to choose a scope or provide an isolated worktree.
4. Only run a targeted closeout when the staged set exactly matches the target list and the tested tree has no unstaged edits for those targets.
5. Distinguish outcomes:
   - focused pytest pass = test evidence only;
   - reviewer score below 85 or `REJECTED` = closeout failure;
   - `APPROVED` with exit code 0 = closeout success.

## Evidence wording

Report exact score, verdict, exit code, and command. Do not call a junction migration, unit-test pass, or worker self-report “done” when the independent reviewer has rejected the candidate.
