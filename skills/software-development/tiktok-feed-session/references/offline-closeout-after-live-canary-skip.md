# Offline closeout after an explicitly skipped live canary

Use this path only when the user explicitly says to skip the live canary or not to wait for it.

## Procedure

1. Replace the active contract: live canary is cancelled, not pending. Keep the exact repository and file allowlist; do not resume device work.
2. Re-check the current worktree, scoped diff, staged paths, branch, upstream, and active farm processes. Do not stop or duplicate a batch merely to unblock code closeout.
3. Run fresh focused regression tests on the current tree, plus compile/import and `git diff --check`. Report the live canary as intentionally skipped, never as passed.
4. Send the exact current diff to the independent review route and require a parseable `APPROVED` verdict. Re-review after every semantic fix.
5. Before commit, stage exact allowlisted paths only. Existing staged files from another task are a trap: inspect `git diff --cached --name-status`; if they are present, unstage/recover safely before committing. Never use `git add -A`.
6. If an accidental mixed-scope commit happens, verify it is local and unpushed, reset only that commit with a non-destructive mixed reset, confirm unrelated files remain present, then restage exact paths.
7. Verify the commit name-status, run post-commit focused tests, compare local/upstream divergence, push the exact branch, and confirm `git ls-remote` equals local HEAD.
8. Final report format: purpose → offline evidence → commit/push proof → intentional live-canary skip → preserved unrelated dirty paths.

## Pitfalls

- A stale target lock or a live farm batch is not a reason to wait once the user explicitly cancels the canary; it is only a reason not to touch that device surface.
- A green test suite does not prove live-device behavior. Keep `live_canary=SKIPPED_BY_USER` distinct from `tests=PASS`.
- Review approval binds to exact bytes. Any post-review patch requires a fresh review.
- A pre-existing index (staged files) can silently be absorbed by `git commit`; exact-path `git add` alone does not clear the index. Check cached paths before committing.
