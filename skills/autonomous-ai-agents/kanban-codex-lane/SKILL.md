---
name: kanban-codex-lane
description: Run bounded Codex implementation lanes through Kanban.
---
# Kanban Codex Lane

Use Codex CLI only as an isolated, bounded implementation input lane. Hermes
keeps Kanban ownership, reviews every diff, reruns verification, and writes the
final durable handoff.

## When to Use

Use this lane for a scoped coding, documentation, test, or mechanical migration
task with clear acceptance criteria and an available git worktree. Do not use it
for research-only work, secrets, production actions, or a change smaller than a
direct Hermes edit.

## Prerequisites

- Enable `kanban.external_lanes.codex.enabled` and the edge plugin.
- Confirm the task has an isolated worktree and a bounded runtime budget.
- Confirm `shutil.which(executable)` and `codex --version` succeed without
  printing credential files.
- Define allowed files, forbidden files, acceptance criteria, and Hermes-owned
  verification commands before launching the lane.

## How to Run

Call the plugin-provided `kanban_codex_lane` tool from a Kanban worker. Prefer
`mode="exec"`; use `goal` only for a deliberate durable multi-step task. The
tool creates a portable temporary worktree, starts Codex through
`process_registry`, records artifacts, and returns `metadata.codex_lane`.

## Quick Reference

- `kanban_show`: read the task, acceptance criteria, and prior handoffs.
- `kanban_codex_lane`: launch the opt-in edge lane with scope and tests.
- `process_registry`: monitor and kill a lane that exceeds its budget.
- `kanban_comment`: preserve observations that do not close the task.
- `kanban_complete.metadata.codex_lane`: persist accepted lane evidence.
- `kanban_block`: stop on unsafe scope, unavailable Codex, or failed review.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
