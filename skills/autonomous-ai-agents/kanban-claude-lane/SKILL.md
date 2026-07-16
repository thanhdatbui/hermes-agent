---
name: kanban-claude-lane
description: Run bounded Claude Code lanes through Kanban.
---

# Kanban Claude Code Lane

Use Claude Code in an isolated worktree. Hermes owns the Kanban task and keeps
only the process and turn bounds needed to prevent quota loops.

## When to Use

Use for a bounded coding or review task with acceptance criteria, a git
worktree, and a reason to capture Claude's structured usage and cost output.
Do not use it for secrets, external side effects, deployment, or open-ended
work.

## Prerequisites

- Load its edge plugin and confirm `claude --version` succeeds.
- Keep the task's worktree isolated and its runtime budget bounded.

## How to Run

From a Kanban worker, call `kanban_claude_lane` with a self-contained prompt,
workspace, tests, and forbidden paths. The edge runs `claude -p` with JSON
output, `--dangerously-skip-permissions`, and a bounded turn count.

## Quick Reference

- `kanban_show`: read acceptance criteria and durable evidence.
- `kanban_claude_lane`: run the opt-in Claude Code input lane.
- `process_registry`: monitor or kill a running lane.
- `kanban_comment`: retain intermediate evidence and questions.
- `kanban_complete.metadata.claude_lane`: persist accepted usage, cost, tests, and artifacts.
- `kanban_block`: stop unsafe, unavailable, or rejected work.

## Procedure

1. Resolve an isolated Hermes worktree; never point Claude at a shared dirty checkout.
2. Give Claude the desired outcome. Claude must not mutate Kanban.
3. Launch with permission bypass; keep the configured turn and runtime budget.
4. Hermes parses the JSON result for usage and cost.
5. Record rejected or timed-out lanes instead of retrying blindly.

## Pitfalls

- Do not exceed the configured turn or runtime budget.
- Do not create an unbounded retry loop after Claude fails.

## Verification

- Confirm the lane was isolated and cleaned up.
- Confirm `metadata.claude_lane` contains parsed usage/cost or an explicit parse failure.
- Confirm the turn and timeout budget stopped a stuck lane.
