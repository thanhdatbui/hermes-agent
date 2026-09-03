# Exact candidate review and release recipe

Use this when `chốt phiên` is requested while the working tree contains older or concurrent changes.

## Why this pattern exists

A mixed dirty worktree makes a tree-hash-only review ambiguous. A reviewer may inspect only the last staged fixture hunk, ignore the production delta already committed in a temporary candidate, or reject because it cannot access a temp path. Approval is valid only for the exact bytes that will be released.

## Procedure

1. Record the current remote base (`git ls-remote origin refs/heads/master`) and inspect the main worktree status. Do not reset, clean, or overwrite unrelated dirty files.
2. Clone each affected repository into an OS temp directory from the current remote base. Keep one candidate clone per repository.
3. Apply only the allowlisted implementation, tests, and case documentation to the candidate clone. Do not carry over machine configs, unrelated Mode 1/Mode 2 changes, or old staged work.
4. Run the candidate tests and syntax/diff checks. If a stricter production contract causes old test doubles to fail, update only the relevant doubles: successful-path adapter doubles implement `close_all_recent_apps`; state doubles remain `FollowState`-shaped. Avoid global replacements.
5. Before review, capture:
   - candidate commit/tree ID;
   - exact changed-path allowlist;
   - focused test counts;
   - `py_compile` and `git diff --check` results.
6. Send `plan-review-hard` through the configured 9Router endpoint for cleanup, recovery, persistence, or state-machine work. Include the exact relevant production diff in the prompt, not only a tree hash. Also include short unchanged baseline excerpts when the requested behavior relies on pre-existing detection/state persistence (for example, Path B calls `state.set_follow_failed()`).
7. Require a parseable first line: `VERDICT: APPROVED` or `VERDICT: REJECT`. Record the HTTP status and effective model. A 200 response without a valid verdict is not approval.
8. Any edit, fixture change, amend, rebase, or staged-index rebuild invalidates review and test evidence. Rerun tests and request a fresh review.
9. After approval, commit the exact candidate, run `git diff origin/master..HEAD --stat`, then push. Verify `git ls-remote origin refs/heads/master` equals the pushed local `HEAD`.
10. Report briefly in Vietnamese: `Mục đích → Kết quả → Bằng chứng → Blocker/Remote`. Explicitly say when live canary was not run; offline tests do not prove device recovery.

## Common failure modes

- **Hash-only review:** reviewer cannot inspect a temp tree. Retry with the actual diff pasted.
- **Large mixed prompt:** reviewer misses production/doc hunks. Retry with compact production sections plus baseline context.
- **Review after test fixture edit:** approval is stale. Rerun tests and review the new commit/diff.
- **Wrong fixture type:** mass replacing `object()` can turn `FollowState` into an adapter fake. Patch constructor doubles by context.
- **Dirty main worktree:** do not commit all dirty files merely to make status clean; release from the clean candidate clone.
