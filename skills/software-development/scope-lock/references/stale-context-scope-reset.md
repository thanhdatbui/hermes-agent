# Stale-context scope reset

Use this reset when a conversation contains a previous plan, TODO, worker handoff,
compaction summary, or dirty worktree that points to a broader task than the
latest user message.

## Reset sequence

1. Quote or paraphrase the latest user request only.
2. Write a replacement contract: Goal, exact allowlist, Non-goals, Acceptance,
   and Stop condition.
3. Cancel or ignore stale TODO items and worker phases. Dirty files are evidence
   of prior work, not permission to continue it.
4. Classify every inherited file/route as `IN_SCOPE`, `OUT_OF_SCOPE`, or
   `NEEDS_USER_DECISION` before reading deeply or editing.
5. Run only the smallest verification that proves the replacement contract.
6. Stop when acceptance passes; report unrelated work as preserved/stale rather
   than absorbing it into the new task.

## Narrow-request example

Latest request: disable recovery only from the farm alert path.

- `IN_SCOPE`: the farm-alert recovery call and its no-spawn/alert-preservation
  checks.
- `OUT_OF_SCOPE`: cron watchers, scheduler supervisors, feed/session launchers,
  PackageInstaller, other recovery ladders, full-suite cleanup.
- `NEEDS_USER_DECISION`: any dependency that appears to require an adjacent
  route or file.

Do not let an earlier "disable all recovery routes" plan, an audit checklist, or
legacy failures reopen the broader scope. Ask for expansion only if the narrow
acceptance cannot be proved without it.

## Communication rule

After a scope correction, send one short boundary statement and continue
silently while tools run. The final report should contain only purpose, result,
blocker, and preserved out-of-scope work unless the user asks for the internal
workflow.