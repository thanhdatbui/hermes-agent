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

## Procedure

1. Resolve an isolated Hermes worktree; never point Claude at a shared dirty checkout.
2. Give Claude scope, forbidden actions, acceptance criteria, and tests. Claude must not mutate Kanban.
3. Launch the bounded lane. Never pass `--dangerously-skip-permissions`, `--permission-mode bypassPermissions`, push, or deploy commands.
4. Keep the Hermes source workspace at the starting `HEAD` and clean until the
   lane returns. If it changes while the lane is running, reject reconciliation
   and inspect the durable patch artifact instead of merging two timelines.
5. Hermes parses the JSON result for usage and cost, then independently checks every changed path and test command.
6. An accepted patch is applied to the Hermes source workspace as an
   uncommitted diff. Review it and commit only when the task authorizes commits;
   otherwise block or hand it off with artifact references.
7. Never relaunch the lane while that workspace is dirty. Resolve the existing
   diff instead of retrying, so repeated claims cannot consume quota in a loop.
8. Complete only an accepted lane with Hermes-owned test evidence. Record
   rejected or timed-out lanes instead of retrying blindly.

## Pitfalls

- Do not treat Claude's JSON success as task acceptance.
- Do not widen `allowed_tools` with wildcard shell, push, or deployment capability.
- Do not expose credentials or copy Claude auth files into artifacts.
- Do not allow partial acceptance; create a new bounded repair task instead.
- Do not edit or advance the source workspace while the lane is running.
- Do not mistake `accepted` for a committed source workspace.
- Do not use a permission-bypass setting, even when interactive Claude guides suggest it.

## Verification

- Confirm the lane was opt-in, isolated, and cleaned up.
- Confirm `metadata.claude_lane` contains parsed usage/cost or an explicit parse failure.
- Confirm Hermes reviewed the diff and ran at least one test itself.
- Confirm the accepted source diff was committed or explicitly handed off
  before another lane claim.
- Confirm no forbidden path, permission bypass, push, or deploy occurred.
