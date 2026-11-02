---
name: kanban-orchestrated-coding
description: Use when a coding goal should run through Hermes Kanban with planner, plan-auditor, executor, reviewer, and summarizer tasks. Builds a durable workflow using existing Kanban tools, plan-audit verdicts, budgets, comments, and blocks without adding a new orchestrator.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, orchestration, coding, plan-audit, multi-agent]
    related_skills: [plan, test-driven-development, requesting-code-review]
---
# Kanban Orchestrated Coding

## Overview

Use the existing Hermes Kanban board as the orchestration spine for coding work. Do not invent a second workflow database, dispatcher hook, daemon, or core model tool. The workflow is a small graph of normal Kanban tasks whose workers communicate through task bodies, comments, run summaries, task links, and plan-audit verdict events.

The plan-auditor task is an actuator: it reviews the planner output, records the verdict on the gated executor task, mutates the graph when revision is needed, and then completes itself. The dispatcher remains a claim engine only.

## When to Use

Use this skill when:

- A user asks Hermes to implement a coding change and wants planner/auditor/executor separation.
- The executor should not start until a plan has been approved.
- Rejection should create a durable revision round instead of relying on chat memory.
- A detached worker needs human input and must block through Kanban rather than wait on an interactive prompt.

Do not use for:

- Small one-shot local edits that do not need multi-agent separation.
- Live provider experiments, external CLI lanes, PR creation, commit, push, deploy, or destructive cleanup unless the task explicitly asks for that.
- Adding broad workflow-template infrastructure. This skill uses the Kanban primitives already present.

## Core Invariants

- The executor task carries `plan_audit_required=true`.
- The plan-audit verdict is recorded on the executor task id, not the auditor task id.
- The preferred actuator call is `kanban_apply_plan_audit_actuation(executor_task_id=<executor_task_id>, ...)`; the lower-level verdict primitive is `kanban_record_plan_audit_verdict(task_id=<executor_task_id>, ...)`.
- `metadata.round` is required on every verdict so actuator replay is idempotent.
- Rejected verdicts use `metadata.kind = "revise_plan"` or `"needs_user_decision"`.
- Revision tasks use round-scoped `idempotency_key`s so crash replay cannot duplicate planner/auditor cards.
- Detached human input uses `kanban_comment` plus `kanban_block(kind="needs_input")`; do not wait on interactive approval tools.
- The plan-auditor task calls `kanban_complete` after it records the verdict and applies the graph mutation.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
