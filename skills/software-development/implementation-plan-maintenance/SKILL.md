---
name: implementation-plan-maintenance
description: "Author AND maintain implementation-plan markdown docs (.hermes/plans/*.md). Authoring: PLAN-ONLY multi-repo/phase plans for Taadaa (governance reads, safe-boundary grounding, FACT/NEEDS_PROOF classification, pilot-first phases, hash+git verification report). Maintenance: apply audit/review findings — fill test skeletons, patch code blocks, verify plan code against the real repo, report changes by locator. Trigger: 'lập implementation plan PLAN-ONLY ... chỉ tạo đúng file .hermes/plans/...', 'sửa plan theo audit / NIT / MINOR / MAJOR', 'fill ... trong plan', 'theo locator', or any plan-only work with 'KHÔNG sửa code repo'."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [planning, plan-document, audit, tdd, documentation]
    related_skills: [plan, test-driven-development, code-review-response, tiktok-farm-hermes-cron-migration]
---
# Implementation Plan Maintenance

Editing an EXISTING implementation plan, or authoring a NEW one PLAN-ONLY for a Taadaa multi-repo migration. Generic one-off plan authoring (non-Taadaa) remains the bundled `plan` skill; this skill owns the Taadaa PLAN-ONLY protocol (safe-boundary grounding + verification report) that the generic skill does not carry. Typical maintenance jobs: applying residual audit rounds (NIT/MINOR/MAJOR findings) to phase/step sections, completing test skeletons that still contain `...`, and making plan code blocks copy-paste-correct against the repo they target — without touching repo code.

## Trigger conditions
- User references an audit on a plan doc: "residual audit vòng 2", "sửa plan theo NIT/MINOR/MAJOR", "trả danh sách thay đổi theo locator".
- Plan contains test skeletons with `...` bodies that must become concrete arrange/act/assert.
- User asks to verify/ground plan code blocks against the real source repo (plan-only edits allowed).
- User asks to AUTHOR a new plan PLAN-ONLY: "lập implementation plan PLAN-ONLY thật trong repo X", "chỉ tạo đúng file `.hermes/plans/<YYYY-MM-DD>_<slug>.md`", multi-repo migration/rollout plans ("nối N consumer vào core đã ship", "migrate X sang Y"). When the task names an EXACT filename, use it verbatim — do not substitute the generic timestamp convention.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
