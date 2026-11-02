---
name: consumer-recovery-adapter-migration
description: Execute phases of the multi-consumer recovery-adapter migration (discovery + baseline-only, later RED→GREEN implementation) inside isolated worktrees without touching dirty origin repos; produce verdict-gated discovery reports with FACT/ASSUMPTION classification.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [recovery-adapter, migration, worktree, baseline, discovery, verdict, tiktok, taadaa]
    related_skills: [project-handoff-audit, git-worktree-merge-reconciliation, concurrent-workspace-safety, implementation-plan-maintenance]
---
# Consumer Recovery-Adapter Migration Phases

## When to Use

The Taadaa `2026-08-12_consumer-recovery-adapter-migration` plan (`.hermes/plans/...` under `D:\Taadaa\automation-core`) migrates recovery-adapter behavior across multiple consumer repos (P1 `tiktok-luot nuoi acc`, P2 `tiktok-log-in`, ...). Each phase runs as **discovery + baseline-only** (worker scope = report + evidence, NO patches) or **implementation** (RED tests → GREEN → verify → commit/audit gates). Use this skill whenever the user names a phase (P1/P2/P3…) or asks for "discovery + baseline-only" scope on one of these consumers.

Program state (2026-08-12): P1 feed discovery → READY_FOR_P1_IMPLEMENTATION; P2 login discovery → READY_FOR_P2_IMPLEMENTATION. Details: `references/program-state.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
