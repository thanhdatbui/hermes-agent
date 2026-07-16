---
name: kanban-codex-lane
description: Run bounded Codex implementation lanes through Kanban.
---

# Kanban Codex Lane

Use Codex CLI in an isolated worktree. Hermes keeps Kanban ownership and the
lane stops only when its process budget is exhausted or Codex exits.

## When to Use

Use this lane for a scoped coding, documentation, test, or mechanical migration
task with clear acceptance criteria and an available git worktree. Do not use it
for research-only work, secrets, production actions, or a change smaller than a
direct Hermes edit.

## Prerequisites

- Load the edge plugin and confirm the task has an isolated worktree.
- Confirm `shutil.which(executable)` and `codex --version` succeed.

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

## Procedure

1. Read the task and create or resolve its Hermes worktree. Never run Codex in
   a shared dirty checkout.
2. State the task id and desired outcome in the Codex prompt. Codex must not mutate Kanban.
3. Start the lane with `--yolo`; the worktree remains the isolation boundary.
4. Record `used`, mode, worktree, branch, command, result, commits, and artifacts under `metadata.codex_lane`.
5. Complete or block the Kanban task from Hermes.

## Pitfalls

- Do not let Codex call `kanban_complete`, `kanban_block`, or other board tools.
- Do not exceed the configured lane timeout.
- Do not create unbounded retry loops after a provider or CLI failure.

## Verification

- Confirm the lane ran in a portable temporary worktree.
- Confirm its timeout and process cleanup work.
- Confirm `metadata.codex_lane` is durable before `kanban_complete`.
- Confirm timed-out lanes are killed and temporary worktrees are removed.
