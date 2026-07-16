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

## Procedure

1. Create the root task with the research question, acceptance criteria, repository path, and a read-only constraint.
2. Run the classifier/scoper. Define the claims to verify, search boundaries, likely files, and evidence quality rules. Split independent claims into parallel workers.
3. Create workers with abstract steps such as `researcher:structure`, `researcher:runtime`, `researcher:tests`, or `researcher:history`. Do not hard-code provider or model names in the workflow.
4. Each worker should inspect source, tests, configuration, and history as appropriate. Record exact `file:line` citations, commands run, observed behavior, assumptions, uncertainty, and artifact paths with `kanban_comment`.
5. Complete a worker only when its result distinguishes verified facts from hypotheses. Block it instead of guessing when evidence is unavailable.
6. Create a reviewer after the evidence workers finish. The reviewer checks citation accuracy, contradictory findings, scope coverage, and read-only compliance; it requests targeted follow-up tasks when needed.
7. Create a synthesizer/final auditor after review. Combine the accepted evidence into the workflow report, state residual uncertainty, and answer the original question without exposing raw run metadata or credentials.
8. Complete the root task with the report summary and the report reference. Preserve all handoffs and artifacts in the Kanban subtree.

## Pitfalls

- Do not use `assignee` as a substitute for role identity; `current_step_key` is the per-attempt role/phase snapshot.
- Do not create a second research database, workflow engine, or model-routing tool.
- Do not claim a bug from a grep hit alone. Trace the runtime path and verify intent in tests or history.
- Do not modify the repository during research, including formatting, generated files, or lockfiles.
- Do not hide uncertainty behind a confident synthesis; mark unverified claims and explain what would resolve them.

## Verification

- Confirm every cited `file:line` exists and supports the claim.
- Confirm each task has a durable role step, parent/dependency links, and a terminal status.
- Confirm worker comments include commands, evidence, uncertainty, and artifact references where applicable.
- Confirm reviewer/auditor coverage includes contradictions and unresolved gaps.
- Confirm the final response matches the workflow report and contains no credentials or raw provider metadata.
