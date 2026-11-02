---
name: kanban-repository-research
description: Research repositories through durable Kanban roles.
---
# Kanban Repository Research Skill

Use a durable Kanban workflow to investigate a repository and return an evidence-backed report. Keep research lanes read-only and preserve findings, uncertainty, and artifacts in task state so another agent can resume or audit the work.

## When to Use

Use for architecture audits, dependency tracing, bug-premise checks, codebase onboarding, and any repository question that benefits from parallel evidence gathering and a reviewed synthesis.

## Prerequisites

- Confirm the repository path and the research question.
- Confirm that Kanban tools are available and identify the board.
- Treat the repository as read-only: do not edit files, commit, install packages, or run destructive commands.
- Use a temporary output location only for non-source evidence when needed.

## How to Run

Create one root task with `workflow_template_id="repository-research-v1"` and `current_step_key="classifier"`. The classifier records scope and creates evidence workers. Link workers as children of the root; create the reviewer after worker tasks complete, then create a synthesizer/final-auditor task that consumes the workflow report.

## Quick Reference

- `kanban_create`: create root, role, reviewer, and auditor tasks; pass `current_step_key` for role identity and `workflow_template_id` for the workflow.
- `kanban_link`: add parent-to-child dependencies for fan-out and fan-in.
- `kanban_comment`: record findings, commands, uncertainty, and artifact references on the relevant task.
- `kanban_complete`: finish a role only after its evidence is durable.
- `kanban_block`: stop a role when access, scope, or evidence quality prevents a trustworthy result.
- `GET /tasks/{task_id}/report`: use the normalized workflow report for final synthesis when the dashboard API is available.

## Directness and source-fit gate

For concrete repository/provider questions, answer the exact operational question before giving background. Classify every candidate as **direct match**, **related architecture**, or **not a match**. Record whether it uses an official API, browser/UI automation, a reverse-engineered transport, or an unrelated wrapper. Never infer that a model label such as `gemini-veo` is specifically Veo 3/3.1 without documentation or source evidence; mark the mapping unverified when the repository does not establish it. If the user corrects an interpretation, discard the prior speculative path and restate only verified facts from the inspected sources. Keep the final answer concise and lead with the shortlist and recommendation.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
