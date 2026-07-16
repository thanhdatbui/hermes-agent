---
name: kanban-computer-use-lane
description: Run bounded desktop automation tasks through Kanban.
---

# Kanban Computer Use Lane

Use Hermes' existing `computer_use` tool as a task-scoped external lane while
Kanban retains durable ownership, evidence, retries, and completion state.

## When to Use

Use when a Kanban task must operate a native desktop application that browser,
file, and terminal tools cannot reach directly.

## Prerequisites

- Confirm the worker profile includes the `computer_use` toolset.
- Set a finite task runtime and retry budget.
- Put the target application and intended outcome in the task body.

## How to Run

Create a task with `workflow_template_id="computer-use-lane-v1"` and
`current_step_key="worker"`, then force-load this skill. Capture the target app,
act, and record the final application state in Kanban metadata or artifacts.

## Quick Reference

- `kanban_show`: read the task and prior attempts.
- `computer_use`: capture and operate the desktop application.
- `kanban_heartbeat`: keep long UI work from being reclaimed.
- `kanban_comment`: record observations and artifact paths.
- `kanban_complete`: persist the outcome.
- `kanban_block`: stop after the bounded retry/runtime budget is exhausted.

## Procedure

1. Capture the named application and identify the current state.
2. Perform the requested actions directly; the lane adds no action policy beyond the tool's runtime capabilities.
3. Re-capture after important state changes and preserve useful evidence.
4. Retry only when the observed state changed or the next action differs.
5. Complete with the final state and artifacts, or block when the task budget is exhausted.

## Pitfalls

- Do not repeat the same capture/action pair without new evidence.
- Do not let a stale element index consume the retry budget; capture again.
- Do not create a second desktop automation process when `computer_use` already owns one.

## Verification

- Confirm the task used `computer-use-lane-v1` and a finite runtime/retry budget.
- Confirm every retry changed either the hypothesis or action.
- Confirm the final state or blocker is durable in Kanban.
