---
name: concurrent-workspace-safety
description: "Operate safely in workspaces where multiple agents/workers edit files concurrently — baseline snapshots, collision detection, no-clobber pivot to independent verification, and collision reporting."
version: 1.0.2
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, concurrency, scope-safety, verification, orchestration]
    related_skills: [test-driven-development, code-audit, code-review-response, systematic-debugging]
---
# Concurrent Workspace Safety

## Runtime path vs Git path drift

When a task edits a live runtime file but the user expects a Git-tracked change, treat the paths as separate evidence domains. Record and verify all three independently: `implemented_path` (bytes actually changed), `tracked_path` (Git file/commit that should carry the change), and `runtime_loading_path` (the path Hermes imports/loads). A green compile/test on `implemented_path` does not prove `tracked_path` changed, and a clean Git diff does not prove the runtime is using the tracked copy.

For a single-controller Windows host, prefer one canonical Git-managed runtime path over a Git template plus an AppData copy. But a junction/symlink or copy migration is a state-changing architecture change, not a harmless cleanup: before implementing, capture exact preimages and hashes, prove the current loader path, verify junction target/loop safety and Windows permissions, define rollback, and test both Git tracking and runtime loading. Do not delete or overwrite an existing live plugin merely because a template directory looks incomplete. If the runtime and template diverge, report `SOURCE_OF_TRUTH_DRIFT` and reconcile with an explicit allowlist.

The reusable evidence checklist is in `references/runtime-git-path-drift.md`.

 (e.g. this user's AGENTS.md + HERMES_SUBAGENT_RULES orchestration), a parallel worker can write to YOUR exact scope while you work. The task brief may even flag it ("đang bị worker khác sửa live"). Blindly implementing anyway clobbers the other worker's in-flight work; blindly reverting destroys their checkpoint. The safe path: detect early, never clobber, pivot to independent verification, report the collision.

**Core principle: before writing, compare the requested hunk with existing dirty hunks and active ownership. A same-file dirty state is not itself a blocker; proceed when the hunks are distinct and no active owner holds the requested hunk.**

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
