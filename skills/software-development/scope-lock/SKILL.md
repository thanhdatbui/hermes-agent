---
name: scope-lock
description: "Use before any task or tool sequence to lock the user's current goal, scope, non-goals, acceptance criteria, and stop condition."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [scope, task-contract, anti-drift, verification, orchestration]
    related_skills: [agent-verification-loop, plan, test-driven-development]
---

# Scope Lock

## Overview

Use this skill before acting on any non-trivial request, especially repository,
automation, debugging, testing, deployment, or delegated work. Its purpose is
to prevent **scope drift**: turning a narrow request into a larger plan because
an old plan, test failure, worker handoff, or adjacent route is visible.

This is a coordination gate, not permission to edit anything. The latest
explicit user request remains authoritative.

## Task contract

Create a compact contract before the first state-changing action:

```text
Goal:              the single outcome the user asked for
In scope:          exact repo/worktree/files/routes/devices/operations allowed
Non-goals:         adjacent files/routes/operations that must remain untouched
Acceptance:        observable conditions proving the goal is met
Stop condition:    when acceptance passes, stop; do not continue by curiosity
```

Keep the allowlist concrete. “Recovery” or “the repo” is not an allowlist;
name the actual route, file, worktree, or operation. If the request is clear,
derive the contract narrowly instead of asking the user to repeat it.

## Authority and stale context

1. The latest user message wins over older plans, summaries, TODOs, handoffs,
   delegated-worker prompts, and compressed context.
2. A plan describes possible work; it does not authorize every phase. Adopt only
   the phases and paths covered by the current contract.
3. A discovered dependency or failing adjacent test is not automatically in
   scope. Record it as `OUT_OF_SCOPE` or `NEEDS_USER_DECISION`.
4. Do not treat “make it robust,” “full suite,” or “audit everything” as
   permission unless the user actually requested that breadth.

## Closeout versus remediation

Treat a user request such as `chốt phiên`, `đóng phiên`, or `kết thúc phiên` as a
**closeout command**, not an invitation to resume the oldest unresolved plan.
First identify the exact code/diff the user asked to close in the current task.
Do not resurrect a historical candidate, adjacent subsystem, or prior worker
handoff merely because it appears in compressed context, session history, a TODO,
or a review transcript.

A review finding authorizes a fix only when the user has explicitly asked to
fix review findings until approval (for example, “sửa đến khi review đạt”).
Even then, review only the exact requested candidate and keep the remediation
inside its original allowlist. A finding that proposes a new subsystem, a
broader audit, or a different historical candidate is `OUT_OF_SCOPE` until the
user explicitly expands the contract.

For the closeout decision tree, exact-scope review payload, and shared-worktree
failure pattern, see `references/closeout-scope-and-review.md`.

## Dirty-tree classification gate

A dirty working tree is not a blanket blocker. Before editing or verifying, classify
paths against the current contract's exact allowlist:

1. Paths outside the allowlist are `OUT_OF_SCOPE`; do not inspect deeply, modify,
   revert, reset, unstage, stage, or wait on them. Their staged/unstaged state,
   unrelated test processes, and unrelated failures do not block the task.
2. A path inside the allowlist may already contain staged and/or unstaged hunks.
   Staged state alone is not evidence of a concurrent writer and must not be
   discarded or normalized.
3. Treat a scope conflict as proven only when the same allowlisted file or
   overlapping region changes during the current task's ownership window (for
   example, hash/mtime/content changes between checkpoints), or when ownership
   cannot be separated safely. Otherwise continue with the exact allowlist.
4. Verification may run against a dirty but stable allowlisted tree. Report
   staged and working-tree path sets separately; do not upgrade unrelated dirt
   into `SCOPE_CONFLICT`.

## Scope checkpoints

Re-check the contract at these boundaries:

- before the first tool call that changes state;
- before a new file, route, repository, worktree, device, or account;
- before delegating or changing worker scope;
- before switching from focused tests to a full suite;
- before any live, network, scheduler, deploy, commit, or push action;
- after a failure reveals an adjacent subsystem.

Ask one question: **“Is this directly required by Goal and inside the
allowlist?”** If no, stop that branch. Do not inspect deeply, edit, test,
delegate, clean up, or retry it. Report the out-of-scope finding and ask for
explicit expansion only when expansion would materially help.

## Narrowing and context-reset gate

At the start of every turn, rebuild the active contract from the **latest user
message**, even when older messages, plans, TODOs, handoffs, worker summaries,
or a context-compaction note use the same vocabulary. A compaction/handoff
summary is reference material, never a new user instruction.

When the latest message narrows or corrects the task:

1. Replace the old contract; do not merge the old scope into the new one.
2. Mark stale TODOs, worker work, and plan phases cancelled/ignored for this
   task. Do not resume them merely because files are already dirty or a worker
   is waiting.
3. Restate the corrected boundary in one short line before the next
   state-changing action.
4. Re-check every proposed file, route, test, delegation, and live surface
   against the replacement contract.

A request naming one component or alert path defaults to that component/path
only. Adjacent watchers, schedulers, recovery ladders, launchers, tests, or
cleanup are non-goals unless the user names them or the acceptance criteria
prove they are directly required. A plan, audit request, robustness concern,
or full-suite failure never reopens a narrowed scope by itself.

For the reusable reset checklist and contract template, see
`references/stale-context-scope-reset.md`.

## Goal, scope, and contract vocabulary

- **Goal:** the outcome the user wants.
- **Scope:** the allowed boundary — files, routes, repos, devices, and
  operations.
- **Scope lock:** the checkpoint mechanism that prevents crossing that boundary
  without explicit expansion.
- **Task contract/spec:** Goal + scope allowlist + non-goals + acceptance
  criteria + stop condition.
- **Acceptance:** observable evidence that the goal is met.
- **Stop condition:** the point at which further work is not authorized.

## Worker/delegation contract

Copy the full contract into every worker prompt. Require the worker to return
`SCOPE_DRIFT` immediately if it discovers work outside the allowlist. Workers
must not silently add files, tests, routes, cleanup, or broad verification.
The coordinator must independently verify the exact changed paths and run only
the contract's acceptance checks.

### Concurrent index and exact-commit gate
A dirty index may contain another session's already-staged files even when the working-tree diff appears unrelated. Before committing, inspect both `git diff` and `git diff --cached`, record pre-existing staged paths, and treat them as owned work. Never use `git add -A`, `git reset`, or whole-file staging as a cleanup shortcut. For same-file concurrent edits, construct staged content from `HEAD` plus only the approved hunks, then verify staged added lines and exact file paths. Inspect `git show <commit>` after committing; a removed unrelated block is not evidence it was safely excluded unless added lines are checked. If separation is not provable, stop with `DIRTY-ALLOWLIST-CONFLICT`.

### Conflict stop versus verification-only follow-up

A concurrent edit discovered after a write/read checkpoint is a hard stop for
further source edits in the overlapping region. Do not repair the situation by
reverting, restaging, normalizing line endings, or replaying the patch. It is
still valid to run evidence-only verification against the current bytes when
the user or harness asks for fresh evidence, but report it as verification of
the current tree—not proof that the requested fix was safely completed.

### Ambiguous follow-up turns and isolated candidate worktrees

When a user asks what to do next after a blocked or confusing state, answer the
current operational decision before resuming remediation. Do not treat “what do
I do now?” as authorization to pick an implementation base, reconcile another
session, or continue an old plan. If the original fix request is still active,
state the exact next action and its boundary, then act only within that boundary.

A clean worktree made from `origin/*` is a **candidate patch surface**, not proof
that the remote commit contains the user's authoritative local work. Before
using it as a fix base, record the base SHA and compare it with the local HEAD,
staged paths, and relevant unstaged path. If local work may contain required
context, preserve it and label the result `CANDIDATE_FIX` until ownership and
integration are explicitly resolved. Never report a candidate-worktree test as
an applied fix to the user's working tree.

When editing multiple documentation files with repeated headings, use unique
surrounding context for each edit and immediately inspect the diff for deleted
checklist/policy lines. A successful patch operation is not sufficient evidence
that the intended block was preserved.

Use explicit status labels:

- `SCOPE_CONFLICT`: source work stopped because ownership/overlap was unsafe.
- `VERIFIED_CURRENT_TREE`: focused checks passed on whatever bytes currently
  exist; this does not clear the conflict or authorize more edits.
- `FIX_COMPLETE`: only when the requested findings were actually applied, the
  final diff is attributable to this task, and acceptance checks pass.

Never convert a green test run, compile check, or diff check into
`FIX_COMPLETE` when the conflict gate stopped the implementation path.

## Verification and stop rule

Prefer the smallest evidence that proves acceptance:

- focused test for the changed behavior;
- negative test proving the forbidden action did not occur;
- diff/status check proving no adjacent path changed.

Do not run a broad suite merely because it exists. Do not fix unrelated
failures to obtain a green dashboard. When acceptance passes, report the result
and stop. If acceptance cannot be proved without expanding scope, report
`BLOCKED/NEEDS_USER_DECISION` rather than widening the task yourself.

## Checklist

- [ ] Latest user request identified as the active authority
- [ ] Goal is one sentence
- [ ] Exact allowlist recorded
- [ ] Non-goals recorded
- [ ] Acceptance criteria are observable
- [ ] Stop condition is explicit
- [ ] New file/route/worker/test scope passed a checkpoint
- [ ] Focused evidence is sufficient
- [ ] Final diff/status contains no unapproved path
- [ ] Stopped immediately after acceptance
