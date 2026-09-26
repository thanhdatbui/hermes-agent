# Session-close diff and timeout lessons

## Exact-scope closeout

When the user issues an explicit session-close command (`chốt phiên`, `chốt`, `đóng phiên`, `xong phiên`, `kết thúc phiên`, `done`, `wrap up`), do not review `HEAD~1` blindly. Snapshot and inventory staged, unstaged, and untracked paths, then classify each hunk as `OWNED`, `RELATED`, `RELATED_UNADOPTABLE`, `UNRELATED`, `EXCLUDED`, or `CONFLICT`. Adopt `RELATED` only with task/incident ownership evidence; filename similarity, proximity, mtime, or matching topic is not enough. Preserve unrelated dirt byte-for-byte and give the reviewer an isolated candidate patch/temporary index so unrelated work cannot be scored.

Review and close each independent group separately. A blocked related group must not veto an independently verified owned group; report `DONE_WITH_BLOCKED_RELATED`. A blocked owned group blocks that group. Bind approval to the candidate patch SHA, recompute immediately before commit, rehash the committed diff after commit, and verify the configured upstream remote SHA. Never hardcode `master`, force push, or require a clean worktree when unrelated dirt is preserved.

## Worker timeout/quota discipline

Separate policy/docs, code, tests, and long-running canary/batch lanes. Give each worker a narrow exact patch contract and a timeout appropriate to the lane. After a timeout, inspect the live diff before redispatching: partial work may already be complete. Treat timeout/network/rate-limit failures as transient; retry at most twice with backoff, then narrow the contract. Do not repeat a broad prompt that caused quota waste. Do not dispatch a worker to a wrong repository or broad workspace; include the absolute repo path and allowlisted files in every contract.

## Evidence loop

Run focused tests before review. For policy-only changes, static assertions alone may score poorly; add a compact offline behavioral harness where useful (temporary git repo, candidate SHA drift, foreign-dirt preservation, per-group outcomes, and event ledger). Do not pretend a mock proves production integration. The closeout reviewer must receive the exact candidate diff plus focused evidence, not a fallback diff from unrelated dirty files.
