---
name: hermes-cron-skill-sync
description: "Use when cron exports Hermes skills to Git."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, cron, skills, git, sync, fail-closed]
    category: software-development
---
# Hermes Cron Skill Sync

Use this skill to maintain a scheduled, auditable pipeline that exports profile-local Hermes skills into a repository and pushes only reviewed skill changes.

## Core workflow

1. **Discover scope**: identify the exact skill(s) intended for publication. Prefer an explicit manifest or an isolated worktree. Do not treat every file currently under the runtime skill directory as requested scope.
2. **Export**: copy local skill content into the repository while excluding curator metadata, caches, locks, manifests, credentials, and secrets. Preserve repository-only skills; never use a destructive mirror.
3. **Preflight**: inspect `git status --short`, review the exact path-scoped diff, run `git diff --check`, and scan the candidate for credentials before staging.
4. **Commit**: stage only the reviewed skill paths. Never stage unrelated dirty worktree changes. Use a clear skill-sync commit message.
5. **Push**: let repository hooks run normally. Do not bypass hooks or fabricate approval/audit records. If the remote rejects a secret, remove it from the unpushed commit history, not merely from the current working file.
6. **Verify**: require successful exit codes from the script, commit, and push; compare local and remote commit SHAs. A scheduler `last_status=ok` or printed `SYNCED` string is not evidence by itself.

## Cron wrapper contract

A no-agent wrapper must return non-zero when any child process fails. Capturing stderr and printing `SYNC_ERROR` is not enough if the wrapper exits zero. Avoid unconditional early `exit 0` statements before the commit/push path. Emit silence only for a genuine no-change result.

The scheduled task should distinguish these outcomes:

- `UNCHANGED`: no intended skill diff; exit 0 and remain silent.
- `SYNCED`: commit and push both succeeded; include the resulting SHA in diagnostics.
- `BLOCKED`: hook, secret scan, dirty-scope conflict, or remote protection rejected the operation; exit non-zero and preserve the evidence.

## Scope and safety rules

- Do not use broad `git add skills/` when the runtime tree has accumulated unrelated changes. Use an allowlist, manifest, or clean isolated worktree.
- Do not commit profile-local runtime state, `.env`, auth files, token-bearing references, curator state, cache files, lock files, or generated operational data.
- Do not weaken a pre-push gate merely to make cron green. Fix the candidate scope or the evidence that legitimately belongs to the gate.
- Treat GitHub push protection as a required safety boundary. A detected token must be revoked/rotated in the provider and removed from every unpushed commit that contains it.
- Do not report a push as complete until a remote ref/SSH/HTTPS readback confirms the pushed commit SHA.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
