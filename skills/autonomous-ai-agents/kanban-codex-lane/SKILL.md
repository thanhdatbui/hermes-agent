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

## Procedure

1. Read the task and create or resolve its Hermes worktree. Never run Codex in
   a shared dirty checkout.
2. State the task id, scope, prohibited actions, acceptance criteria, and
   verification commands in the Codex prompt. Codex must not mutate Kanban.
3. Start the bounded lane. Do not use `--yolo`, `--full-auto`, edge-plugin
   auto-commit, auto-push, or deployment commands.
4. Keep the Hermes source workspace at the starting `HEAD` and clean until the
   lane returns. If it changes while the lane is running, reject reconciliation
   and inspect the durable patch artifact instead of merging two timelines.
5. Review committed, tracked, untracked, deleted, and renamed paths against the
   starting `HEAD`; for a rename, review both the old and new path. Reject
   forbidden or unrelated changes before running code from the lane.
6. Run required tests independently as Hermes against the lane's natural git
   state. The harness stages a snapshot only after those tests finish, so its
   own reconciliation machinery cannot change test semantics.
7. An accepted patch is applied to the Hermes source workspace as an
   uncommitted diff. Review that source diff, then commit it only when the task
   authorizes commits; otherwise block or hand it off with artifact references.
8. Never relaunch the lane while that workspace is dirty. Resolve the existing
   diff instead of retrying, so the same accepted output cannot consume the
   retry budget in a loop.
9. Record `used`, mode, worktree, branch, command, result, commits, rejection
   reason, tests, and artifacts under `metadata.codex_lane`, then complete or
   block the Kanban task from Hermes. Codex output alone is never authoritative
   and does not constitute task completion.

## Pitfalls

- Do not let Codex call `kanban_complete`, `kanban_block`, or other board tools.
- Do not pass provider, gateway, GitHub, or dashboard credentials to the child.
- Do not accept Codex-reported tests without rerunning the canonical command.
- Do not retain a temporary worktree without recording it as an artifact.
- Do not edit or advance the source workspace while the lane is running.
- Do not mistake `accepted` for a committed source workspace.
- Do not turn a provider/CLI failure into a blind model fallback.

## Verification

- Confirm the lane was opt-in and ran in a portable temporary worktree.
- Confirm Hermes reviewed the diff and ran every required test itself.
- Confirm no forbidden path, secret, commit, push, or deployment was accepted.
- Confirm `metadata.codex_lane` is durable before `kanban_complete`.
- Confirm the accepted source diff was committed or explicitly handed off
  before another lane claim.
- Confirm timed-out lanes are killed and temporary worktrees are removed.
