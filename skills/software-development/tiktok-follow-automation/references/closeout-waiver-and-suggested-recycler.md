# Closeout waiver and suggested RecyclerView regression

## Lessons from the Path B incident

- A user-provided incident screenshot identifies a runtime failure, but an explicit later instruction to skip the live canary changes the release path. Record `CANARY_WAIVED_BY_USER`; do not perform device actions, and continue exact-scope offline review, tests, commit, rebase, push, and remote-SHA verification.
- Unrelated dirty files are not blockers. Preserve them. If the scoped file is mixed, use line-level ownership and reconstruct the candidate in a clean temporary worktree or isolated index. Stop only when the requested hunk overlaps a concurrent edit or cannot be attributed.
- In `_path_b_verify`, checking only whether any node has a known follower-list RecyclerView ID is unsafe. A Profile's suggested-account rail can reuse the same ID (for example `id/uo1`). Require the full relation-surface predicate (`_on_follower_list`) before deciding that the tap failed to leave the follower list.
- Keep the safety gates after that distinction: exact target header identity, relationship-action classification, bounded Back, and restored follower-list proof. The fix must remove the false negative without weakening identity or relationship verification.

## Regression recipe

Build a profile fixture containing:

1. the exact target `@handle` in the header;
2. a whitelisted followed relationship action;
3. a suggested-account RecyclerView using a known follower-list ID;
4. a restored follower-list fixture after Back.

Assert that Path B returns `followed`. Keep a paired negative fixture where the target appears only in suggestions or the header identity is different; it must remain `manual`.

## Closeout evidence

For a post-rebase candidate, rerun the focused Path B tests and compile/diff checks, obtain a fresh parseable `plan-review` verdict through 9Router over the post-rebase bytes, then push only the exact candidate paths and verify `git ls-remote` equals local `HEAD`.
