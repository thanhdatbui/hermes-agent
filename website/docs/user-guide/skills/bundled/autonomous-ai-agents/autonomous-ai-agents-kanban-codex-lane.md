---
title: "Kanban Codex Lane - Run bounded Codex implementation lanes through Kanban"
sidebar_label: "Kanban Codex Lane"
description: "Run bounded Codex implementation lanes through Kanban"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Kanban Codex Lane

Run bounded Codex implementation lanes through Kanban.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/autonomous-ai-agents/kanban-codex-lane` |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Hermes loads when this skill is active.
:::

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

1. Read the task and create or resolve its Hermes worktree. Never run Codex in a shared dirty checkout.
2. State the task id, scope, prohibited actions, acceptance criteria, and verification commands in the Codex prompt. Codex must not mutate Kanban.
3. Start the lane with `--yolo`; the worktree remains the isolation boundary.
4. Record `used`, mode, worktree, branch, command, result, commits, and artifacts under `metadata.codex_lane`.
5. Complete or block the Kanban task from Hermes.

## Pitfalls

- Do not let Codex call `kanban_complete`, `kanban_block`, or other board tools.
- Do not pass provider, gateway, GitHub, or dashboard credentials to the child.
- Do not accept Codex-reported tests without rerunning the canonical command.
- Do not retain a temporary worktree without recording it as an artifact.
- Do not turn a provider/CLI failure into a blind model fallback.

## Verification

- Confirm the lane ran in a portable temporary worktree.
- Confirm its timeout and process cleanup work.
- Confirm `metadata.codex_lane` is durable before `kanban_complete`.
- Confirm timed-out lanes are killed and temporary worktrees are removed.
