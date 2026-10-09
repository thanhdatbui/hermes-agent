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
5. **Cross-Session Context Bleed Guard (KỶ LUẬT CHỐNG RÒ RỈ NGỮ CẢNH):**
   - Khi phiên chat có khối tóm tắt `[CONTEXT COMPACTION — REFERENCE ONLY]` hoặc kết quả subagent/tiến trình ngầm trả về, CẤM TUYỆT ĐỐI tự ý lôi các sự cố, câu hỏi, hoặc chủ đề của các phiên cũ (ví dụ: nick bị ban, lỗi 413, audit trước đó) vào trả lời nếu người dùng KHÔNG HỀ hỏi tới trong lượt hiện tại.
   - Việc trả lời vượt ngoài prompt đang hoạt động bị người dùng coi là "trả lời nhầm session" hoặc nói nhảm.
   - BẮT BUỘC neo câu trả lời 100% vào đúng câu hỏi ở tin nhắn mới nhất của người dùng. Mọi context thừa từ khối tóm tắt chỉ dùng để tra cứu ngầm (read-only), không được chủ động phát tán ra câu trả lời.

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

### Exact-review-payload gate

When the user asks to apply named patches from a review (for example, “exact
P1–P4”), treat the review payload itself as an input artifact that must be
located and bound before editing:

1. Identify the exact two policy-file paths and the exact latest review artifact
   from the current workspace or the user-provided source. Do not infer patch
   text from filenames, stale session-search snippets, unrelated reviews, or a
   1. Identify the exact repository, exact policy-file paths, and exact latest review artifact from the current workspace or the user-provided source. Do not assume the current working directory is the candidate repository. First inspect its staged path set; if it has no matching staged policy files, stop editing there and perform only bounded discovery of known repository candidates or explicitly named paths. Do not infer the candidate from unrelated dirty code, a similarly named file, a stale session-search snippet, or a worker summary.
   2. Bind the candidate to its observed `HEAD`, branch, staged path set, and worktree path before reading or changing it. A staged policy candidate in a different checkout is authoritative for this task only after its exact staged paths are confirmed; unrelated unstaged paths in that checkout remain preserved and out of scope.
   3. Extract each requested patch as an explicit old/new block or an
      unambiguous section-level contract. If any named patch is missing or
      ambiguous, stop as `BLOCKED/MISSING-REVIEW-PAYLOAD`; ask for the review text or exact artifact path rather than guessing.
   4. Snapshot bytes, hashes, EOL/BOM facts, and status for the two allowlisted files before editing. Preserve bytes outside the intended blocks; do not normalize line endings or rewrite whole files.
   5. Apply only the named patches, preferably with unique surrounding context.
      Reject any patch that touches a third file, broadens a safety exception, or
      weakens an existing fail-closed invariant without an explicit reviewed
      replacement.
   6. Verify required markers/sections and exact occurrence counts, run scoped
      `git diff --check -- <file>`, and inspect the complete diff. Report the
      exact diff and confirm that no other path changed; do not commit unless the
      user explicitly asks.

   **Repository-discovery pitfall:** if the first checkout inspected has only
   unstaged implementation/test changes and no staged policy files, that is a
   scope-location failure, not permission to edit those files. Preserve them,
   record the mismatch, and locate the staged candidate using bounded, known paths.
   Once the correct checkout is found, re-run the full staged/worktree snapshot
   there before the first write. Never broaden discovery into an unbounded
   recursive search or use a guessed policy filename as evidence of scope.

A failed search for the review artifact is not permission to search the entire
workspace recursively or to reconstruct the patches from historical context.
Use bounded, known candidate paths first; if the payload remains unavailable,
stop and report the blocker truthfully.

## Repository and target binding before broad discovery

When a request refers to a schema, workflow, example, or state machine without
an explicit path, bind the repository and target before searching:

1. Inspect only the current working directory and its immediate repository
   metadata (`git rev-parse --show-toplevel`, status, and a bounded file list).
2. Search tracked files and obvious project documentation for the distinctive
   markers named by the request; exclude generated/vendor/binary trees and set
   a bounded output/time budget.
3. If the markers are absent or the directory is not a repository, do not scan
   the user's home directory, backups, unrelated repositories, or historical
   artifacts to guess the target. Report `BLOCKED/MISSING-TARGET` and ask for
   the exact repository/path (or an explicit search boundary).
4. Preserve the discovered repository's dirty state as evidence. Never infer
   that a similarly named backup or neighboring repository is authoritative.

### Windows multi-repository path-resolution gate

On Windows, do not treat a plausible directory name, a failed shell `workdir`, or a workspace-level folder as the repository. A drive root may contain several independent repositories and similarly named worktrees. Before reading anchors or editing:

1. Establish the candidate with native Windows filesystem checks and `git -C <native-path> rev-parse --show-toplevel`; verify the exact root and that the requested files exist there.
2. If Git-Bash/MSYS spelling (`/d/...`, `/c/...`) disagrees with native resolution, stop retrying equivalent path variants. Use one verified native path consistently for Git and file reads, and record the discrepancy as harness/path setup evidence—not as a source finding.
3. Inspect only immediate candidate directories and bounded tracked-file metadata. Do not recursively search a whole home/drive to guess among unrelated repositories.
4. If the candidate contains multiple projects or the exact consumer/canonical file pair is absent, report `BLOCKED/MISSING-TARGET` and ask for the exact repository/path. Do not edit a similarly named sibling checkout.

This gate precedes anchor reads, dirty-hunk classification, and any patch. It prevents path-resolution failure from being mistaken for a clean repository, an empty worktree, or permission to broaden discovery.

A plausible nearby file is not a valid target merely because it contains one
shared keyword. The target must contain the requested schema/example/state
machine relationship, and the final edit/verification scope must remain bound
 to that exact path.

### Bounded Windows repository discovery

If the initial working directory is not a Git repository, do not repeatedly
retry equivalent shell path spellings and do not recursively scan the user's
home/drive. Treat this as a repository-binding checkpoint:

1. Resolve the native Windows path and inspect only its immediate children for
   Git repositories or explicitly named candidate roots.
2. For each bounded candidate, run `git -C <native-path> rev-parse
   --show-toplevel`, then check the exact requested files before reading review
   artifacts or editing.
3. Prefer the candidate that contains the complete requested file set and the
   relevant staged/dirty state. If multiple candidates match, stop and report
   `BLOCKED/AMBIGUOUS-TARGET` rather than choosing by filename or recency.
4. Once bound, use one native path consistently for Git, reads, writes, tests,
   and diff inspection. Record unrelated dirty paths and preserve them.
5. Do not spend the iteration budget on broad discovery after the exact target
   is found; immediately snapshot status and read only the allowlisted files
   and bounded review artifacts.

This prevents a non-repository cwd, an MSYS/native path mismatch, or a similarly
named sibling checkout from being mistaken for the authoritative worktree.

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

### Hard Gate: Absolute Path Scope Lock & Hermetic Sandbox Architecture (v4.4)
When delegating fix/code/patch/test tasks, the contract MUST contain at least
one concrete **Absolute Path** (e.g., `D:/Taadaa/.../target.py` or `C:/Users/...`),
and the referenced file MUST exist on disk before dispatching. Gated at runtime
by `farm-coordinator-guard` (Scope Lock Absolute Path Hard Guard):
- Tasks without an absolute path fail immediately with `SCOPE LOCK MISSING TARGET FILE`.
- Tasks with speculative/nonexistent paths fail immediately with `FILE/PARENT NOT FOUND`.
- Specifying whole directories (e.g., `D:/Taadaa`) is rejected with `DIRECTORY NOT ALLOWED` to prevent unconstrained scanning.
Never delegate open-ended exploration ("find where X is defined in repo"); inspect
O(1) first to locate the exact file path before dispatch.

#### Zero-Bypass Principles (Claude Opus CLI Certified):
1. **Physical Pre-Tool Guard vs Soft Constraints:**
   - Memory entries and system prompts are *soft constraints* (stochastic and prone to lost-in-the-middle context drift).
   - Real, immutable enforcement requires *hard constraints* at the runtime pre-tool hook layer (`pre_tool_call` plugin hook) that reject invalid operations before execution.
2. **Symmetric Enforcement (Declaration != Enforcement):**
   - Validating `target_files` during `delegate_task` is incomplete unless the child worker's own write operations (`write_file`, `patch`) are symmetrically intercepted and gated against that exact scope list.
3. **Recursive Value Scanning (Alias & Embedded Diff Protection):**
   - Security checks must not rely on guessing argument parameter names (`path`, `target`, `file_path`, `filename`).
   - Every string value across all argument keys and nested structures must be recursively extracted, resolved via `os.path.realpath`, and validated against the whitelist.
   - For `patch` operations (especially V4A unified diffs), embedded target headers (`*** Update File:`, `*** Add File:`, `*** Delete File:`, `*** Move to:`, `+++ b/`) must be parsed and verified to prevent decoy-parameter write escapes.
4. **Hermetic Worker Sandbox (Default-Deny):**
   - **Tool Default-Deny:** Worker subagents are restricted to a minimal whitelist (`read_file`, `write_file`, `patch`, `terminal`, `search_files`). Calling `execute_code`, `browser`, or recursive `delegate_task` is hard-blocked.
   - **Terminal Default-Deny:** Worker terminal access forbids arbitrary script execution (`python foo.py`, `pytest`) and shell chaining (`;&|` metacharacters blocked via `shlex.split(posix=False)`). Terminal is strictly confined to read-only inspections (`git status/diff/log` with zero flags, `adb devices`, `inspect_machine.py <N>`, `psutil`).
   - **Git Isolation:** Subprocess Git commands enforce `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `GIT_ATTR_NOSYSTEM=1`, `GIT_PAGER=cat`, and `--no-textconv` to eliminate config-based pager, textconv, and fsmonitor RCE vectors.
   - **Fail-Closed Identity:** Sessions whose parentage cannot be positively verified from SQLite DB default to untrusted worker (least privilege), never coordinator. `None` results must never be cached to avoid sticky privilege escalation.

### Concurrent index and exact-commit gate
A dirty index may contain another session's already-staged files even when the working-tree diff appears unrelated. Before committing, inspect both `git diff` and `git diff --cached`, record pre-existing staged paths, and treat them as owned work. Never use `git add -A`, `git reset`, or whole-file staging as a cleanup shortcut. For same-file concurrent edits, construct staged content from `HEAD` plus only the approved hunks, then verify staged added lines and exact file paths. Inspect `git show <commit>` after committing; a removed unrelated block is not evidence it was safely excluded unless added lines are checked. If separation is not provable, stop with `DIRTY-ALLOWLIST-CONFLICT`.

#### Git index-lock closeout safety
A scoped staging operation is not a commit result. Before committing, verify the exact staged path set and retain the pre-commit status snapshot. If Git reports `.git/index.lock`, do not immediately delete it or kill processes: inspect whether a Git process is active and whether the lock is fresh. Treat an active Git process or a lock that is recreated as `COMMIT_BLOCKED/CONCURRENT_GIT`; preserve the staged state and unrelated dirt, report the exact blocker, and stop rather than retrying blindly. Only remove a demonstrably stale lock when no Git process is active and the repository owner explicitly permits cleanup; then re-check the staged path set before retrying. Never use `--no-verify` as a workaround for an index lock, and never claim a commit SHA until `git commit` exits successfully and `git rev-parse HEAD` plus `git show --stat HEAD` confirm it.

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

### Final-write and staged-policy closeout gate
For staged policy/documentation fixes, the last source edit invalidates every
earlier staged snapshot and structural check. After the final edit: re-stage only
the exact allowlisted files, rerun all marker/heading/anchor/occurrence checks
against live bytes, rerun `git diff --cached --check -- <allowlist>`, and compare
`git diff --cached --name-only` to the exact expected path set. Then inspect
`git status --short --untracked-files=all` for accidental artifacts. Do not report
completion from checks run before the last patch. Keep shell operands containing
comparison operators quoted (for example, quote `'>=85'` or use Python
assertions) so Bash does not create an accidental file such as `=85`. If final
verification is interrupted, report the tree as not finally verified rather than
relying on the pre-edit pass.

Use explicit status labels:

- `SCOPE_CONFLICT`: source work stopped because ownership/overlap was unsafe.
- `VERIFIED_CURRENT_TREE`: focused checks passed on whatever bytes currently
  exist; this does not clear the conflict or authorize more edits.
- `FIX_COMPLETE`: only when the requested findings were actually applied, the
  final diff is attributable to this task, and acceptance checks pass.

Never convert a green test run, compile check, or diff check into
`FIX_COMPLETE` when the conflict gate stopped the implementation path.

## Policy-only documentation change gate

When a task is limited to policy/workflow documentation, especially when it names
required reads, excluded files, or a no-commit/no-push boundary, treat the policy
files as an exact allowlist rather than as permission to audit the repository:

1. Read the user-named source documents before editing. Bind the requested change
   to the exact canonical section, pointer, and workflow wording, and record
   explicitly excluded files (for example, `PROJECT_RULES.md`) as forbidden.
2. Snapshot `git status --short --untracked-files=all` and inspect staged and
   unstaged diffs before writing. Pre-existing staged policy files are not proof
   that this task owns all their hunks; preserve them and distinguish the task's
   new diff from prior staged content.
3. Patch each allowlisted document with unique surrounding context. Do not rewrite
   whole policy files, normalize line endings, or touch code/tests to make
   documentation verification convenient.
4. Verify exact markers/section counts, canonical pointers, prohibited-operation
   wording, and the complete scoped diff. Run `git diff --check -- <allowlisted
   files>` and prove excluded/unrelated paths are unchanged. If the contract says
   no commit/push, do not stage, commit, or push as part of verification.
5. Report exact policy paths changed, excluded paths untouched, pre-existing
   unrelated dirt preserved, and real verification output. A dirty worktree is
   not a blocker when the task contract permits scoped documentation edits.

For the reusable policy-only checklist and a representative scoped-commit-policy
verification pattern, see `references/policy-only-documentation.md`.

## Three-iteration contract feasibility gate

For safety-sensitive automation changes, bind the contract before editing and
track the first three investigation iterations explicitly:

1. **Iteration 1 — anchor discovery:** locate the exact existing read/update
   pattern and authoritative state fields. Do not infer an API contract from
   field names or a nearby script alone.
2. **Iteration 2 — behavior contract:** demonstrate that the requested action
   can be decided from already-recorded evidence without adding a probe,
   broad `/test` sweep, live network, device, or scheduler side effect.
3. **Iteration 3 — offline proof:** define a minimal mockable seam and a
   negative-case matrix for every protected state named by the user.

If the contract is not demonstrable after iteration 3, **ABORT before source
edits** and report the exact unresolved anchor plus the proposed contract.
Do not spend the budget on speculative endpoint discovery or invent field names.
A plausible field name is not evidence of an existing contract.

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
