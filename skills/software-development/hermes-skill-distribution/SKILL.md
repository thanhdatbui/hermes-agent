---
name: hermes-skill-distribution
description: "Synchronize Hermes skills safely across machines."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, skills, sync, git, profiles, multi-machine]
    category: software-development
---
# Hermes Skill Distribution Skill

Use this skill when a Hermes skill is maintained in a repository but loaded from a separate profile-local skills directory. It covers safe propagation across machines and profiles; it does not replace the repository's own change review or silently overwrite customized skills.

## When to Use

- After pulling a repository update that changes bundled skills.
- When one machine has a newer skill than another.
- When `hermes update` or ordinary skill sync reports that a local copy was kept.
- When establishing a repository-as-source-of-truth workflow for multiple Hermes machines.

## Prerequisites

- The Hermes repository and target branch/remote are known.
- The target profile's `$HERMES_HOME` is known.
- Local edits to the profile skill have been identified before replacement.
- Use `terminal` for Git and CLI commands, `skill_view` for runtime-content inspection, and `skill_manage` only when creating or maintaining the reusable distribution skill.

## How to Run

Use the repository as the shared Git boundary, but support changes made in either machine's local Hermes skill directory:

1. Before starting work, fetch/pull the target branch and inspect the working tree. Do not reset or discard unrelated local changes.
2. After creating or editing skills locally, export the local skill tree into the repository with the project's `deploy/sync-skills-to-repo.ps1` helper (or its platform equivalent). The export must exclude runtime metadata, caches, locks, curator state, hub data, and secrets.
3. Review `git status` and `git diff`, resolve any deliberate local/repository overlap, and run `git diff --check`.
4. Commit the reviewed skill changes. Before pushing, fetch/pull again, merge or rebase remote changes, resolve conflicts, rerun `git diff --check`, then push.
5. On the other machine, pull the commit and sync repository skills into its local Hermes home with the forward sync helper. Do not use `hermes skills reset` as the normal cross-machine workflow.
6. Start a new Hermes session or use `/reset` after the filesystem sync so the new content enters a fresh cached context.
7. Verify the active content with `skill_view`; compare hashes only when strict byte-level proof is required.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
