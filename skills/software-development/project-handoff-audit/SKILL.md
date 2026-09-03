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

**Report exceptions honestly:** a fleet trim is not "all done" when an active repo was intentionally skipped, a file has no safely separable history block, or a repository cannot be committed/pushed. State exactly what changed, what was skipped, and why.

**Active-repo safety:** if a repository is known to be under active work, do not edit its HANDOFF even when it exceeds the threshold; inventory it and defer it explicitly. Do not use a stale line-range plan against a file that may have changed—re-read, remap headings, and rebuild the keep plan. **If the user later clarifies the repo is NOT actually active (e.g. corrects an earlier "skip" note with "sửa hết / đang k làm / đm sửa hết"), re-trim it in the same pass—do not permanently defer on a stale assumption.**

**Do the full fleet when the user says "làm đi / xử lý luôn / sửa hết":** execute every repo in scope autonomously (trim + commit + push), then report a consolidated table. Do not stop after one repo and ask "what's next?".

Fleet-wide trim procedure covers `HANDOFF.md`/`handoff.md`, `AGENTS.md`, and `PROJECT_RULES.md` across repos (EOL-preserving, backup-first, keep-ranges plan, pitfalls:
sequential-trim double-trim restore, git case mismatch, `.git` pointer files, hidden
`.git/FETCH_HEAD`, identical dual-file `HANDOFF.md`+`handoff.md` trim, lost-original
recovery, and active-repo skip/re-verify): see `references/handoff-fleet-trim.md`.

### Context-load / repository-bloat scan

When the user asks what makes a repository or model context heavy, separate three classes instead of treating every large file equally:

1. **Startup-loaded policy** — root and repo `AGENTS.md`, `CLAUDE.md`, `PROJECT_RULES.md`, and current `HANDOFF.md`. Rank these first by bytes/lines because they are the most likely to be injected automatically.
2. **Task-gated source/docs** — large Python/Markdown/JSON files that should be read only for a directly relevant task. Flag oversized files, but do not cut source mechanically.
3. **Runtime/generated/vendor/data** — logs, JSONL ledgers, screenshots, decrypted workflows, build outputs, package metadata, lockfiles, binaries, and backups. These may dominate disk size but are not automatically context bloat; check tracked/ignored status and whether any startup rule tells agents to read them.

For each candidate record path, bytes/lines, tracked vs ignored/untracked, and the rule or loader that could read it. Do not delete or rewrite merely because a file is large. Prefer a narrow policy change (startup pointer, archive/reference split, bounded/filtered log reads, or ignore rule) and verify no active workflow depends on the path. Details and a reusable table are in `references/context-bloat-scan.md`.

## HANDOFF Trim Rule — đã thành rule bắt buộc trong PROJECT_RULES.md các repo (2026-08-11)

- HANDOFF > ~250 dòng → task kế phải TRIM giữ current-state; append entry mới kèm trim entry cũ.
- Chi tiết rule text + thủ tục: `references/handoff-fleet-trim.md`.

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

## Configuration / Runtime Impact Audit

When a user asks whether an agent, script, or log changed configuration and could affect sibling automation repositories, perform a read-only scope audit before making any edit or restart. Distinguish these layers explicitly:

1. **Persistent OS/user configuration** — inspect the actual Windows user/machine environment store (for example HKCU/HKLM via `winreg` or an equivalent read-only query), not only the current shell environment.
2. **Current process/runtime state** — inspect the live process command line and executable path, especially daemon flags such as ADB server socket/port.
3. **Repository-local configuration** — inspect untracked and dirty files as well as committed files; a newly added local helper may affect only one runner even when its report is stored at workspace level.
4. **Child-process propagation** — trace whether a runner calls `os.environ.update(...)`, passes `env=...` to `Popen`/`subprocess`, or pins an executable path. Separate process-local overrides from persistent OS changes.
5. **Cross-repository reach** — search each relevant consumer and shared core for the exact variable names, resolver/helper imports, executable selection, and environment propagation. Do not infer impact from a report's claim of compatibility.

Use evidence in this order: persistent-store values -> live daemon executable/command line -> exact repository references/diff/status -> focused tests/config validation -> read-only runtime smoke checks. Report `global impact`, `repo-local impact`, `shared-core impact`, and `live runtime status` separately. A report/log is evidence of intent or recommendation, not proof that a configuration was applied. Do not restart daemons, touch devices, or mutate config during a read-only impact audit.

A reusable checklist and redacted probe pattern are in `references/config-runtime-impact-audit.md`.

## Sensitive Data Discipline

Do not quote raw credentials, tokens, OTPs, proxy strings, session data, workbook rows, or account lists. Redact sensitive values as `[REDACTED]`. Summarize account/device/workbook-heavy reports by category and state instead of reproducing them.

## Pitfalls

- Do not treat helper/runtime folders inside a project as independent projects when the parent handoff/runbook says they are part of the project runtime.
- Do not let old `Next Task` sections override newer handoff entries; reconcile contradictions and call out stale task pointers.
- Do not convert a read-only audit into a live validation run.
- If a folder has only scaffold docs and no entrypoint, say it is scaffold-only and list what must be identified next.
- For high-risk automation projects, separate docs cleanup prompts from code/live-run prompts.
