# Terra exact-byte review and shared-worktree conflict gate

## Trigger
Use for multi-file code review, review-gated closeout, or “fix until approved” work in this user's Taadaa repositories.

## Correct reviewer route
- Normal review/audit: direct 9Router HTTP `POST /v1/chat/completions` with model `gpt-5.6-terra`.
- Read-only request: `tools: []`, `tool_choice: "none"`, `stream: false`.
- Require the first response line to be exactly `VERDICT: APPROVED` or `VERDICT: REJECT`.
- Do not substitute AG Claude, Flash, or the implementation worker because a stale wrapper or old note names them. Escalate to the configured Terra/Sol route only when risk requires it.
- Review the exact staged payload, not a prose summary or a broader repository snapshot.

## Exact-byte procedure
1. Record HEAD, allowlist, staged/working-tree path sets, staged blob hashes, and the staged diff hash.
2. Run focused tests, compile/type/lint checks, and scoped `git diff --check` after the final edit.
3. Stage only the allowlist without `git add -A`; preserve unrelated staged and dirty paths.
4. Recompute hashes immediately before review and again after it. A changed scoped blob invalidates the verdict.
5. If Terra returns REJECT, fix only actionable findings in the original allowlist, rerun focused evidence, and re-review. Never commit/push before APPROVED.

## Shared-worktree stop conditions
- A same-file allowlisted file changes during the ownership/review window: `SCOPE_CONFLICT`.
- Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) appear: `DIRTY-ALLOWLIST-CONFLICT`.
- Do not resolve, reset, unstage, stash, normalize line endings, or overwrite the conflict to force green tests.
- A green test run on different bytes is only `VERIFIED_CURRENT_TREE`, not proof for the reviewed candidate.
- Preserve the current index/worktree and report the exact blocker; commit/push is forbidden.

## Provenance lesson
A review route failure and a review verdict are different states. HTTP/provider/setup failures produce no approval and must not be reported as REJECT or APPROVED. A reviewer verdict is valid only for the exact bytes supplied.
