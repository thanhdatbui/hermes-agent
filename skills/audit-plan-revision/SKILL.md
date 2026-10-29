---
name: audit-plan-revision
description: Revise an existing implementation plan (under .hermes/plans/) for internal consistency and audit readiness — documentation-only, enumeration-scope coherence, static-vs-runtime evidence separation, governance gates. Use when asked to "fix/make consistent/update the plan", add a route/item to an enumerated set, or produce an "audit-revised" plan.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, plan-mode, audit, documentation, consistency, review]
    related_skills: [plan]
---
# Audit Plan Revision

Revise an ALREADY-WRITTEN implementation plan so it is internally consistent and audit-ready. The deliverable is the updated `.md` file only. This is NOT implementation.

> Overlaps with the built-in `plan` skill (which authors plans from scratch). This skill covers the *revision / consistency* pass on an existing plan and the audit-readiness discipline (enumeration scope, static-vs-runtime evidence, governance gates). If `plan` is editable in your environment, prefer folding this content into it; otherwise keep this as the supplementary skill.

## Hard boundary — documentation-only

- Edit ONLY the plan markdown file. Do NOT edit production code, tests, policy/HANDOFF, or any other repo file.
- Do NOT run ADB, live automation, scheduled tasks, process kills, network recovery, commit, push, or deploy.
- Re-read the whole plan at the end and confirm no contradictory statements survive.

## Read source ONLY to ground the plan; cite exact locators

For a discovered route/seam, open the real source file and record `file:symbol/lines`.
- PowerShell: `read_file` the `.ps1`, quote the exact function lines (e.g. `Invoke-HealthCheck` ~L512-534 calling `Write-ResumeRequest` ~L533 then `Start-ScheduledTask` ~L534).
- **Windows path gotcha:** `search_files` mis-translates `D:\...` into MSYS `/d/...` and returns `os error 3` on Windows hosts. Use native Windows paths with `read_file`/`patch`, or fall back to `terminal grep "..." "/d/..."` for bulk scans.

## Enumeration-scope consistency (the #1 source of contradictions)

If the plan enumerates a numbered set (routes R1-R10, steps, tasks), every reference to "all of them" MUST use the same upper bound after you add an item.

- After adding a route/item R11: replace every `R1-R10` / `R5-R10` / `R5–R10` (and any en-dash variants) with `R1-R11` / `R5-R11`. Audit these locations: route table, route verification matrix, scope notes ("may only edit R1-R10"), discovery/acceptance gate, RED/GREEN matrix, Task-N heading ("R5-R10 RED→GREEN"), Task rerun list, acceptance-criteria bullets, and the execution handoff.
- Keep classification distinctions explicit: a classification-only route (e.g. "R9 is scan-only, do NOT disable") must not be silently promoted to a runtime-disabled route; a static-source route must not be conflated with dynamic ones.
- **Prove zero stale references remain:** `grep -nE 'R1-R10|R5-R10' file.md` → expect NONE_FOUND.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
