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

## Procedure

1. Read the task and create or resolve its Hermes worktree. Never run Codex in a shared dirty checkout.
2. State the task id, scope, prohibited actions, acceptance criteria, and verification commands in the Codex prompt. Codex must not mutate Kanban.
3. Start the bounded lane. Do not use `--yolo`, `--full-auto`, edge-plugin auto-commit, auto-push, or deployment commands.
4. Review `git diff`, reject forbidden paths and unrelated changes, then run required tests independently as Hermes.
5. Accept only a reviewed passing diff. Record `used`, mode, worktree, branch, command, result, commits, rejection reason, tests, and artifacts under `metadata.codex_lane`.
6. Complete or block the Kanban task from Hermes. Codex output alone is never authoritative and does not constitute task completion.

## Pitfalls

- Do not let Codex call `kanban_complete`, `kanban_block`, or other board tools.
- Do not pass provider, gateway, GitHub, or dashboard credentials to the child.
- Do not accept Codex-reported tests without rerunning the canonical command.
- Do not retain a temporary worktree without recording it as an artifact.
- Do not turn a provider/CLI failure into a blind model fallback.

## Verification

- Confirm the lane was opt-in and ran in a portable temporary worktree.
- Confirm Hermes reviewed the diff and ran every required test itself.
- Confirm no forbidden path, secret, commit, push, or deployment was accepted.
- Confirm `metadata.codex_lane` is durable before `kanban_complete`.
- Confirm timed-out lanes are killed and temporary worktrees are removed.
