---
name: kanban-claude-lane
description: Run bounded Claude Code lanes through Kanban.
---
# Kanban Claude Code Lane

Use Claude Code only as an isolated implementation input lane. Hermes owns the
Kanban task, reviews the diff, reruns tests, and records the final handoff.

## When to Use

Use for a bounded coding or review task with acceptance criteria, a git
worktree, and a reason to capture Claude's structured usage and cost output.
Do not use it for secrets, external side effects, deployment, or open-ended
work.

## Prerequisites

- Enable `kanban.external_lanes.claude.enabled` and its edge plugin.
- Define allowed and forbidden files plus Hermes-owned test commands.
- Confirm `claude --version` succeeds without printing credential files.
- Keep the task's worktree isolated and its runtime budget bounded.

## How to Run

From a Kanban worker, call `kanban_claude_lane` with a self-contained prompt,
workspace, tests, and forbidden paths. The edge runs `claude -p` with JSON
output, `--permission-mode default`, a configured narrow allowlist, and a
bounded turn count.

## Quick Reference

- `kanban_show`: read acceptance criteria and durable evidence.
- `kanban_claude_lane`: run the opt-in Claude Code input lane.
- `process_registry`: monitor or kill a running lane.
- `kanban_comment`: retain intermediate evidence and questions.
- `kanban_complete.metadata.claude_lane`: persist accepted usage, cost, tests, and artifacts.
- `kanban_block`: stop unsafe, unavailable, or rejected work.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
