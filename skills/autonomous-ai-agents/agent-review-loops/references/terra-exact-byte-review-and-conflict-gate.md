# Terra exact-byte review and shared-worktree conflict gate

## Trigger
Use for multi-file code review, review-gated closeout, or “fix until approved” work in this user's Taadaa repositories.

## Correct reviewer route
- Normal review/audit (UI, popup, video gate, feature 1 repo, helper): Gọi combo `plan-review` (gpt-5.6-terra -> ag/claude-opus-4-6-thinking -> cmc/deepseek/deepseek-v4-pro) hoặc `gpt-5.6-terra` trực tiếp qua 9Router HTTP `POST /v1/chat/completions`.
- Hard review/audit (Architecture, Scheduler, Lock, Recovery, Multi-repo): Gọi combo `plan-review-hard` hoặc `gpt-5.6-sol`.
- Tool chuẩn hoá: `python D:/Taadaa/tools/invoke-plan-review.py` (hoặc PowerShell `D:\Taadaa\tools\invoke-ag-audit.ps1`).
- Read-only request: `tools: []`, `tool_choice: "none"`, `stream: false`, `reasoning_effort: "high"` (hoặc `"max"`).
- Require the first response line to be exactly `VERDICT: APPROVED` hoặc `VERDICT: REJECT`.
- TUYỆT ĐỐI CẤM gọi trực tiếp AG Claude (`ag/claude-opus-4-6-thinking`), Flash, hoặc implementation worker. CẤM dùng `delegate_task` để review.
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
