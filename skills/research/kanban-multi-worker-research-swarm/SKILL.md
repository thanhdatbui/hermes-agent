---
name: kanban-multi-worker-research-swarm
description: Coordinate parallel researchers into audited synthesis.
---
# Kanban Multi-Worker Research Swarm Skill

Use a bounded Kanban swarm to investigate a broad question through independent evidence lanes and produce one audited synthesis. Preserve each worker's scope, sources, uncertainty, contradictions, and handoffs so parallelism improves coverage instead of multiplying unsupported summaries.

## When to Use

Use for broad market, policy, technical, scientific, competitive, or due-diligence questions where independent research lanes can verify different claims or challenge one another before synthesis.

## Prerequisites

- Confirm the research question, decision audience, deadline, evidence standard, and allowed sources.
- Set a bounded worker count, task budget, and stopping condition before fan-out.
- Define confidentiality and authorization boundaries for external sources or private files.
- Do not contact third parties, purchase data, or perform consequential actions without explicit approval.

## How to Run

Create a root task with `workflow_template_id="multi-worker-research-swarm-v1"` and `current_step_key="classifier"`. The classifier decomposes the question into non-overlapping claims, creates bounded parallel researchers, and reserves reviewer/challenger and synthesizer/final-auditor stages. Use the workflow report as the normalized final evidence projection.

## Quick Reference

- `kanban_create`: create the root, evidence workers, challenger, reviewer, and final auditor with durable role steps.
- `kanban_link`: encode fan-out, cross-check, and fan-in dependencies.
- `kanban_comment`: record source citations, commands, claim status, confidence, uncertainty, and artifact references.
- `kanban_complete`: finish a lane only when its assigned claims have durable evidence or explicit negative findings.
- `kanban_block`: stop a lane when access, scope, budget, or evidence quality prevents a trustworthy conclusion.
- `web_search`, `browser_navigate`, and `read_file`: gather permitted public or local evidence while retaining exact provenance.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
