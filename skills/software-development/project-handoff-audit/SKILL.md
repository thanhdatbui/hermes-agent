---
name: project-handoff-audit
description: "Read-only audit and normalization planning for project handoffs, task queues, runbooks, and coding-agent prompts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [handoff, runbook, project-audit, documentation, read-only]
    related_skills: [codebase-inspection]
---
# Project Handoff Audit

Use this skill when the user asks to inspect project folders, classify candidate projects, prepare dashboard/handoff cleanup, or draft Codex/Claude prompts for repository documentation normalization.

## Core Rule

Honor read-only scope strictly when requested. A handoff audit is an inventory and synthesis task, not a build/test/live-validation task. Do not run project scripts, device automation, account workflows, workbook writers, package entrypoints, or migrations unless the user explicitly authorizes that exact action.

## Candidate Classification

Classify folders into durable buckets instead of one-off labels:

1. **Main project** — has project docs plus repo/manifest/entrypoint markers.
2. **Worktree/task branch** — nested or named as a branch/task workspace; may have handoff/tasks/reports but often lacks full repo metadata.
3. **Backup/archive** — dated backup, dirty backup, copy, export, or historical snapshot.
4. **Shared/context/helper/runtime folder** — supports a parent project; do not treat it as independent when parent docs say it is runtime/helper.
5. **Loose file / non-project** — isolated marker or artifact without project structure.

Strong markers include:

- `HANDOFF.md` / `handoff.md`
- `AGENTS.md`
- `CLAUDE.md`
- `tasks/`
- `reports/`
- `.git` / `.git_repo`
- manifests: `requirements.txt`, `package.json`, `pyproject.toml`
- obvious entrypoints/runners such as top-level `.py`, `.ps1`, `.bat`, CLI scripts

## Read Order Per Project

1. `AGENTS.md`
2. `CLAUDE.md` if present
3. `HANDOFF.md`
4. `tasks/` index and the latest/relevant task files
5. `reports/` index and the latest/relevant reports
6. manifest or entrypoint files — read only enough to identify purpose, command surface, and safety implications

If the user gives a specific file list, follow their list, but still inspect missing expected docs when doing a normalization assessment.

## Output Shape

For each project, return:

- current status
- in-progress or blocked work
- which standard files are present and whether they are healthy
- what should be normalized in `HANDOFF.md`, `TASKS.md`, and `RUNBOOK.md`
- risks before editing or running anything
- a project-specific coding-agent prompt

For run/schedule-status questions, report timestamps in the user's requested local timezone. For this user, default to Vietnam time (UTC+7), and include the timezone label explicitly.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
