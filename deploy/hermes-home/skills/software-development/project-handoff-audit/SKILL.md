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

## Scheduled Run Status Verification

When checking whether a project schedule actually finished, do not query only Hermes cron jobs. First identify the project's own runner/scheduler and inspect its artifact store. Prefer this evidence order:

1. active process check for the project runner;
2. latest run directory by filesystem modification time;
3. root `run_manifest.json`, `summary.txt`, and `log.jsonl` when present;
4. if aggregate files are missing, inspect per-target manifests and the root log;
5. derive completion from the latest target `end_time` and terminal event, but distinguish **run completed** from **all targets successful**.

Report counts by final status (for example `success`, `degraded`, `manual-needed`, `fail`) and state clearly when the aggregate manifest is missing. Never label a batch as fully successful merely because the runner process exited or because some targets succeeded. Convert UTC timestamps to Vietnam time (UTC+7) before presenting them.

When multiple projects are involved, also provide a prioritization order and group by risk level.

## Normalization Guidance

### `HANDOFF.md`

Should be current-state focused:

- project purpose
- current active state
- active blockers / next safe step
- critical safety rules
- pointers to reports/history

Move or reference long historical logs from reports or changelogs rather than keeping every resolved detail in the handoff.

### `TASKS.md`

Should be a compact queue:

- Active
- Blocked / Requires Approval
- Done / Historical references

Call out stale or contradictory `Next Task` entries discovered in old handoff text.

### `RUNBOOK.md`

Should contain:

- entrypoints and helper/runtime folders
- dependency/manifest files
- config and artifact paths
- safe read-only/static checks
- live-operation gates
- validation and stop conditions

Explicitly mark scaffold-only projects as `runtime TBD`; do not invent entrypoints.

## Sensitive Data Discipline

Do not quote raw credentials, tokens, OTPs, proxy strings, session data, workbook rows, or account lists. Redact sensitive values as `[REDACTED]`. Summarize account/device/workbook-heavy reports by category and state instead of reproducing row-level details.

## Pitfalls

- Do not treat helper/runtime folders inside a project as independent projects when the parent handoff/runbook says they are part of the project runtime.
- Do not let old `Next Task` sections override newer handoff entries; reconcile contradictions and call out stale task pointers.
- Do not convert a read-only audit into a live validation run.
- If a folder has only scaffold docs and no entrypoint, say it is scaffold-only and list what must be identified next.
- For high-risk automation projects, separate docs cleanup prompts from code/live-run prompts.
