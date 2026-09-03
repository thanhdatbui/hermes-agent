---
name: concurrent-workspace-safety
description: "Operate safely in workspaces where multiple agents/workers edit files concurrently — baseline snapshots, collision detection, no-clobber pivot to independent verification, and collision reporting."
version: 1.0.2
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, concurrency, scope-safety, verification, orchestration]
    related_skills: [test-driven-development, code-audit, code-review-response, systematic-debugging]
---

# Concurrent Workspace Safety

## Overview

In coordinator→worker / multi-worker environments (e.g. this user's AGENTS.md + HERMES_SUBAGENT_RULES orchestration), a parallel worker can write to YOUR exact scope while you work. The task brief may even flag it ("đang bị worker khác sửa live"). Blindly implementing anyway clobbers the other worker's in-flight work; blindly reverting destroys their checkpoint. The safe path: detect early, never clobber, pivot to independent verification, report the collision.

**Core principle: before writing, compare the requested hunk with existing dirty hunks and active ownership. A same-file dirty state is not itself a blocker; proceed when the hunks are distinct and no active owner holds the requested hunk.**

## When to Use

- Task scope overlaps files another worker may edit; inspect line/hunk overlap and ownership before writing.
- Multi-worker orchestration environment with parallel dispatch (any repo governed by AGENTS.md worker policy).
- You are about to edit files in a shared worktree where `git status` already shows foreign modified files.

## Workflow

### 1. Baseline snapshot at session start (mandatory)

Before any read-heavy or write work, record a reference frame:

```bash
git status --short --untracked-files=all
stat -c '%y %n' <every scoped file>   # mtimes
date                                  # current time to compare against
```
Plus: `read_file` each scoped file (note line counts / key content anchors), and run the current test suite (`pytest -q`) to record the baseline pass count. This snapshot is what lets you later PROVE a write was foreign.

Classify every baseline red while snapshotting: `git show HEAD:<file> | grep -c '<def name>'` vs the working tree. Reds present in HEAD are pre-existing debt (often YOUR Phase 0 to fix); reds only in the working tree are likely another writer's in-flight work. Never assume the suite is green — record the actual counts.

### 2. Re-verify before the FIRST write

Re-stat the scoped files. Any mtime newer than your baseline that you didn't produce = collision. Re-read a couple of anchors (grep a distinctive string, compare line numbers) to confirm content actually changed.

### 2b. Read-only work is not immune — re-verify before FINALIZING

You may write nothing all session (plan-mode surveys, audits, reports, plans). The working tree still moves under you: a dirty test file grew 239→291 insertions between two read-only checks while a plan was being written. Before finalizing any deliverable that quotes ground truth (test names, line numbers, constants, pass counts):

- Re-run `git status --short`, re-grep the anchors, re-run the suite if cheap. Facts verified an hour ago may be stale.
- Phrase the deliverable robustly to in-flight edits: "fix whatever red tests exist" rather than enumerating named tests that may have been renamed/removed by the time the consumer reads it.
- Record observed drift in the deliverable as an explicit risk (concurrent writer active), not an error on your part.

### 3. Detection signals (any one is enough to stop and check)

- grep/read results differ from your earlier snapshot — line numbers shift, new symbols/imports appear.
- File size / line count changed (e.g. a test file grew 601→732 lines mid-session).
- `stat` mtimes newer than session start, correlated against `date`.
- `git status` gained entries you didn't create.
- `ps aux | grep python` (or tasklist) shows a writer process you don't own.

### 4. On collision: assess the hunk, never clobber

- Do NOT `git checkout --` / revert / overwrite / stage the other writer's hunk. You don't know their checkpoint state; reverting can destroy half-written work.
- Compare the requested hunk with the dirty hunk and process ownership. If distinct and unowned, patch the requested hunk while preserving the existing change. If overlapping, actively owned, or not separable, stop and reconcile.
- Assess completeness instead: read the modified files, run the focused suite, `py_compile`, and `git diff --check`.

### 5. Complete foreign work → pivot to independent verification

Do NOT re-implement. Your value-add becomes verification:
- Replicate the ORIGINAL failing probes/tests (the audit's exact attack shapes) against the current code.
- Tabulate ACCEPTED / REJECTED per probe; run all suites; count tests.
- Report the collision with mtime evidence and a coordinator flag to reconcile ownership.

### 5a. Patch-tool collision is a hard handoff

If `patch` reports that a sibling subagent modified the target after your last read, treat that as authoritative ownership evidence, not a transient retry failure. Stop source edits immediately. Re-stat and re-read the affected regions, inspect both staged and unstaged diffs, and preserve the sibling's checkpoint. Do not retry a fuzzy patch from the stale snapshot, even if the requested hunk appears separate. Continue only with read-only verification, or resume editing after explicit ownership reconciliation. This prevents a partial watchdog/deadline fix from being silently merged into a sibling's newer version.

### 5a-1. Never use restore/reset as collision recovery

A collision recovery command is itself a destructive write. After any overlapping edit, patch warning, or uncertain ownership, never use `git restore`, `git checkout`, `git reset`, `git clean`, stash, whole-file rewrite, or a broad scripted replacement to "put your files back". Those commands can erase a sibling's checkpoint even when the target file was initially modified by you. Preserve the bytes, record `git diff` and `git diff --cached`, and either reconcile ownership explicitly or pivot to read-only verification. If your own incomplete test harness corrupted only an owned file, reconstruct it from a saved preimage in an isolated temporary clone/worktree; do not repair it in-place from memory.

### 5a-2. Proxy fallback needs two distinct acceptance seams

For proxy/router resilience work, separate these behaviors and test both:

1. **Resolution fallback:** a dead account assignment is detected before dispatch and an alive provider-pool member is selected; this is suitable for a fast TCP-health unit test.
2. **Request fallback:** an assigned proxy that accepts TCP but returns a transport/proxy failure (for example HTTP 502, connection reset, or a tagged `proxy_unreachable` result) causes the same request to try the next provider-pool member before direct egress. A resolver-only green test does not prove this path.

The request-level test must assert the observable order (account → pool member 1 → pool member 2 → direct), must use a fresh isolated state, and must prove that upstream `401`, `403`, and `429` are not classified as proxy failures. Do not claim the 3-layer fallback is implemented until the request-level seam is wired into the live dispatch caller and its negative classification test passes.

See `references/proxy-fallback-collision-and-verification.md` for the compact incident pattern and acceptance matrix.

### 5b. Worker-call signature changes require seam reconciliation

When a review fix adds an optional keyword (for example `hard_deadline`) to a worker call, inspect every direct test fake/mocked `_run_child` seam before verification. Existing fakes may use the previous positional signature; a failure such as `unexpected keyword argument` is a real interface regression in the test seam, not proof that the behavior under test passed. Update only owned direct tests or preserve production compatibility, then rerun the exact focused nodes. Keep this separate from unrelated baseline failures.

## Review-remediation gate for staged candidates in a shared worktree

When a user asks to fix findings against an exact staged candidate, treat the index and worktree as two independently owned byte sets. A file can be `MM`: the staged candidate may be the review subject while an unstaged writer is changing the same source or tests. Before patching, capture both `git diff --cached` and `git diff`, then re-stat and re-read the complete affected files immediately before the first write. If an active process or a mtime/content change touches the requested hunk after the baseline, stop with `SCOPE_CONFLICT`; do not replay the finding onto newer bytes, repair test signatures, or use `git checkout`, `reset`, stash, or whole-file replacement to recover the candidate. A rejected patch that reports “no files were modified” is a safe stop, not evidence that the candidate is fixed.

A same-file dirty state is separable only when all three are true: (1) the requested hunk and foreign hunk are independently locator-identifiable, (2) no active writer owns the requested region, and (3) a fresh complete-file read confirms the bytes have not drifted since the ownership check. If any condition is false, preserve staged/unstaged bytes and hand off the exact conflict evidence. Focused tests, compile checks, and diff checks may still be run read-only, but label their results as evidence about the concurrent current tree—not proof that the requested remediation was completed. Reconcile mtimes/status again after every long test run because a concurrent commit or rewrite can invalidate a green result.

### 6. RED evidence when you didn't write the tests

Strict TDD requires watched failures. When a concurrent writer pre-empted you:
- RED source 1: documented pre-fix probe outputs (audit transcripts, review logs showing the vulnerability accepted).
- RED source 2: your own baseline snapshot (pre-fix code read, old test count, no new tests present).
- GREEN: your re-run of the same probes now rejected + full suite passing.
Label honestly: "implemented by concurrent writer (mtimes X–Y), verified by me" — never claim you wrote what you didn't.

### 7. Report

Collision timeline (baseline → foreign mtimes → detection time), what YOU touched (usually nothing), probe evidence table, test/build checks, residual gaps, and a flag for the coordinator to reconcile which worker wrote what between the timestamps.

## Explicitly authorized repository cleanup

When the user explicitly authorizes cleanup of a named repository and says to ask only about important items, treat this as permission to clean disposable repository state—not to touch live devices, unrelated repos, secrets, or remote history without separate authorization. Inspect status, upstream divergence, local-only commits, and dirty diffs first. Classify generated commits by aggregate diff, symbol registration/import/call/test evidence, and duplicate-definition signals; never trust an auto-generated commit message alone. Before destructive cleanup, save status, diffs, commit list, and hashes outside the repo. Restore reviewed tracked noise, remove only reviewed stale plans/backups, and reset to upstream only after local-only commits are proven disposable. Do not push merely because cleanup succeeded. Final acceptance is empty porcelain, no staged diff, diff-check pass, one intended worktree, and 0/0 ahead/behind. See `references/scoped-repository-cleanup.md`.

## Dirty-Worktree Scope Semantics (Model-Agnostic)

A dirty worktree is not automatically a blocker. Treat `git status` as a path-scoped safety signal, not a repository-wide veto:

- **Unrelated pre-existing dirt:** files outside the exact task allowlist and outside the intended commit set are **NEVER blockers**. Leave them untouched, do not stage/revert them, do not stop execution, and continue working on the scoped paths. Stopping or reporting blocked due to unrelated dirty files is a coordinator/worker error.
- **Overlapping dirt:** same-file dirt is not enough to block. Compare line/hunk ranges and ownership; block or request reconciliation only for proven overlap, active ownership of the requested hunk, ambiguity that prevents safe separation, or a concurrent writer changing the requested hunk after the baseline. When active concurrent writers touch the same file, isolate the candidate files to a temporary worktree (`tempfile.mkdtemp()`) to develop/test cleanly.
- **Commit scope:** before committing, stage only the exact allowlist (`git add <file1> <file2>`). A clean staged diff for the task is sufficient; unrelated unstaged files may remain.
- **Scope drift:** means the current agent or its worker changed outside the allowlist. It does not mean unrelated pre-existing `git status` entries.
- **Required report:** distinguish `unrelated dirty preserved`, `overlapping dirty/conflict`, and `agent-caused scope drift`; never collapse all three into `BLOCKED`.
- **Subagent/GPT Stalling & False-Blocker Guardrail:** Subagents/workers (e.g. GPT, Luna) often stall when observing dirty files by treating any uncommitted change as a universal blocker or refusing to proceed. Instruct workers explicitly: unrelated dirty paths outside the allowlist are ignored; only real line/hunk collisions on the assigned files require isolation to an OS temp worktree (`tempfile.mkdtemp()`). A worker must never stop solely because `git status` is non-empty.

When a model or worker claims "dirty workspace" without naming a path and proving overlap, perform a path comparison against the allowlist before stopping. This rule is model-agnostic: do not attribute a false blocker to the selected model until the active prompt/policy and exact dirty paths have been checked.

## Concurrent index and commit-integrity gate

A shared worktree can contain foreign files already staged in the index even when the working-tree diff appears to show only your task. Before any commit, inspect both `git diff` and `git diff --cached`, record pre-existing staged paths, and treat them as owned work. Never use `git add -A`, `git reset`, or whole-file staging as a cleanup shortcut. For same-file concurrent edits, construct staged content from `HEAD` plus only the approved hunks, verify staged added lines and exact staged paths, then inspect `git show <commit>` after committing. A corrective commit may legitimately contain removed unrelated lines; scan added lines separately. If an unwanted block was committed, do not force-push or rewrite remote history; create a corrective commit from the exact remote parent, preserve foreign working-tree changes, and re-run tests on a clean snapshot.

### Exact-byte staging in a live shared worktree

For a closeout request that requires staging but forbids working-tree edits, treat each repository's `HEAD`, index, and worktree as independently moving inputs. Capture, per repository, the full `HEAD` SHA, the pre-existing cached path set, the allowlisted worktree hashes, and the allowlisted index hashes immediately before the first index mutation. Construct policy candidates outside the worktree as `HEAD` bytes plus only the verified appended suffix (for example with `git hash-object --stdin` and `git update-index --cacheinfo`); construct code candidates from a fresh, captured worktree read. Do not use a single multi-repository validation pass as the ownership check.

After every repository's index mutation, immediately re-read that repository's `HEAD`, cached path set, staged blobs, and allowlisted worktree hashes. If `HEAD` advances, a previously clean file becomes dirty, the index gains or loses a foreign path, or a captured worktree hash changes, stop staging immediately with `CANDIDATE_INVALIDATED_BY_CONCURRENT_WRITER`. Do not replay the suffix on the new `HEAD`, restage the code from newer bytes, or repair the index with reset/restore/unstage commands. Preserve the observed state and report the last valid candidate separately from the invalidated final state. A later verification that happens to pass only proves the current bytes; it does not resurrect approval for the superseded candidate.

A sibling commit can absorb or supersede an index-only candidate while the staging operation is still in progress. Therefore the final closeout gate must bind evidence to the final `HEAD` and exact staged diff, not to hashes printed earlier in the run. Re-check `HEAD` and reflog before reporting; if a sibling commit touched a target, classify the result as invalidated even when the worktree bytes still match the artifact. For repositories with pre-existing staged paths, compare the complete cached path set before and after, not only the requested files. The exact-byte staging recipe and invalidation transcript are in `references/exact-byte-closeout-staging.md`.

For same-file concurrent edits, construct staged content from `HEAD` plus only the approved hunks, verify added lines and exact staged paths, then inspect `git show <commit>` after committing. A corrective commit may legitimately contain removed unrelated lines; scan added lines separately. If an unwanted block was committed, do not force-push or rewrite remote history; create a corrective commit from the exact remote parent, preserve foreign working-tree changes, and re-run tests on a clean snapshot.

## Scope-Limited Commit and Push Gate

When the shared worktree must be committed despite unrelated dirty files, add a commit gate after collision assessment:

1. Read the current state before staging: `git status --short --untracked-files=all`, `git diff --name-status`, the scoped `git diff`, branch/upstream, and scoped mtimes. Respect explicit no-read boundaries such as secrets, workbooks, or live-device artifacts.
2. Define an allowlist of production files plus tests whose changes belong to the fix. Never use `git add .`, `git add -A`, or broad globs. Stage exact paths and verify `git diff --cached --name-status` contains only the allowlist.
3. Run focused tests using exact pytest node IDs when the test module also contains unrelated tests. Do not rely on `-k` alone: a keyword can match the module filename and unexpectedly select the whole module. Report focused and broader-module results separately.
4. Run `python -m py_compile` on the scoped Python files and `git diff --check` before and after the commit. If a broader test fails due to a pre-existing/unrelated mismatch, preserve foreign work, record the exact failure, and never claim the whole module is green merely because the fix-specific tests pass.
5. Commit in the requested language/style. Verify `git show --name-status --format=... HEAD` and the full SHA, push the exact upstream branch, and verify the remote ref with `git ls-remote`.
6. Re-run the focused checks post-commit. Independently report exact committed files, SHA, test output, compile/diff checks, push result, and remaining unrelated dirty files. For very large untracked trees, save a status manifest outside the repository and report counts/top-level groups without staging, reverting, or deleting anything.

This commit-gate checklist is also captured in `references/scoped-commit-push-gate.md`.

## Windows Git autocrlf and exact-byte artifact imports

When a fast-forward/import adds LF-encoded artifacts on Windows with global `core.autocrlf=true`, Git may materialize the committed LF blobs as CRLF in the worktree. This is checkout normalization, not source drift. For an exact-byte adoption:

1. Preserve and hash source bytes outside the repository before changing the worktree.
2. After the merge, compare each current file's raw bytes to `git show HEAD:<path>` (and to the preserved copy), not just `git status` or a text diff. Use `git ls-files --eol` to record index/worktree EOL.
3. If the commit blob and preserved bytes are identical but the worktree was normalized, restore the preserved bytes only for the exact allowlist; never normalize unrelated files or amend the commit.
4. Reconcile Git's stat cache with `git update-index --really-refresh -- <allowlist>` and then verify status by path set. A stale stat cache can report a byte-identical restored file as modified; a refresh can clear that false positive without changing content.
5. Re-run hashes, `git diff --check`, focused/full gates, and final dirty-path reconciliation. Report immutable trailing-whitespace warnings separately from all-other-files PASS.

Do not use `git add` as a normalization workaround, change `core.autocrlf` globally, or conclude that preserved artifacts drifted from a CRLF-expanded worktree before comparing raw bytes to the commit blob.

See `references/windows-autocrlf-artifact-import.md` for the compact command/evidence recipe.

## Atomic phase gates for parallel workers

When several workers share one working tree, treat each phase as an **exclusive ownership unit**, not merely a list of files:

1. Write a coordinator ledger before dispatch: worker ID, exact production files, exact test/support files, allowed side effects, and forbidden paths.
2. Keep production implementation and its focused tests in the same worker scope unless the coordinator has a verified handoff between them. Never accept a test-only artifact whose production module is absent; either wait for the producer or re-dispatch the exact missing implementation.
3. A delegation remains active until its completion result is received. Do not infer worker completion from `ps`, an empty local process list, or a quiet worktree; background delegation lifecycle is the source of truth.
4. Do not run a commit, audit, or broad rewrite while any worker owns a file in the candidate diff. After every worker result, re-read the complete affected files, check the allowlist, and run the focused tests independently.
5. If two workers touch the same file, or one worker's test exposes a policy issue in another worker's code, stop the overlapping work, preserve both checkpoints, and reconcile in one coordinator-owned patch only after the workers have handed off.

A green suite is not sufficient acceptance. Reconcile the implementation against `AGENTS.md`, `PROJECT_RULES.md`, and the relevant development guide before commit. In particular, a shared device lease must be released only after verified terminal success; non-success outcomes retain the lease and persist a handoff/retained state. A workbook lock may be short-lived and released in `finally`, but that does not authorize releasing the device lease. Update obsolete tests to assert the invariant rather than weakening production policy.

For audit remediation, use this sequence: audit a concrete commit -> record locator-based findings -> patch only those findings -> run focused tests, full suite, compile/import checks, and `git diff --check` -> create a new commit -> re-audit the new commit. Do not call a dirty working tree approved, and do not treat `N passed` as an audit verdict.

Keep coordinator commentary sparse while workers run: one factual handoff/status update is enough; use tool results and completion notifications as evidence instead of repeated polling messages.

## Scoped checkpoint recovery after a worker corrupts its allowlist

A worker can stop midway after editing only the test file, delete existing tests, nest functions, or create a harness-only RED while production remains at the prior checkpoint. Recover **only the corrupted allowlisted file**; never use broad `reset`, `checkout`, `restore`, `stash`, or `clean` in a dirty/shared worktree.

1. **Before dispatch**, save outside the repo: current `HEAD`, scoped `git diff` patch, SHA-256/size/EOL of every allowlisted file, and the AST top-level `test_*` name set.
2. On abnormal exit, first prove no worker/process still owns the scope. Compare current hashes and diff against the checkpoint to identify exactly which file changed.
3. If `HEAD` moved concurrently, inspect `old_head..new_head` for the scoped paths. A foreign docs/rules commit that did not touch scope may be preserved; a scoped commit requires ownership reconciliation before recovery.
4. Reconstruct the checkpoint in an isolated temp clone/worktree at the recorded base, apply the saved scoped patch there, and verify the reconstructed file's expected hash/test-name set. Then copy back **only** the corrupted file. Do not apply the whole checkpoint patch over good production edits.
5. Re-run syntax/AST checks and the pre-worker targeted baseline. A RED caused by `SyntaxError`, `UnboundLocalError`, missing fixture state, nested tests, or deleted test functions is harness corruption—not TDD evidence—and must be discarded.
6. Dispatch at most one replacement for the exact scope, with the restored preimage hashes and the genuine production behavior that still needs a regression. Afterward, independently compare test-name sets, diff removed lines, targeted/full suites, compile, and `git diff --check`.

This technique preserves unrelated dirty files and concurrent history while returning the worker-owned scope to a provable byte-level checkpoint.

## RED-on-preimage verification for your own scoped fix

When you join a session where the broken state no longer exists on disk (you
wrote the fix before writing tests, or inherited working-tree changes), genuine
RED evidence for new regression tests is still obtainable by temporarily
restoring the preimage bytes of YOUR OWN scoped file:

1. Confirm the scoped file differs from HEAD **only by your own edit** (`git
   diff -- <file>` shows exactly your hunks) and its pre-session hash matched
   your baseline. If ANY foreign dirt exists on that file, DO NOT use this
   procedure — never overwrite another writer's in-flight work to manufacture
   a RED.
2. Save the fixed copy OUTSIDE the repo and record its sha256.
3. Restore the exact preimage: `git show HEAD:<path> > <path>` (verify hash ==
   recorded baseline).
4. Run the new regression tests — each must fail for the EXPECTED reason
   (assertion on the missing guard/behavior), not import/collection errors.
5. Restore the saved fixed copy, verify sha256 matches step 2, re-run → GREEN.
   Report both runs explicitly (RED reason + GREEN pass); delete temp copies.

Observed 2026-08-24 (feed_swipe fast-swipe sponsored-ordering fix): test
"must not run while focus lost" FAILED with the exact AssertionError on HEAD
bytes, then PASSED after restore — clean RED→GREEN pair without stashing
anything.

**Harness trap — production guards that detect mocks:** guards shaped like
`if artifacts.__class__.__module__ == "unittest.mock": return False` silently
bypass the seam when the test passes a `Mock()` ctx, so a terminal-error
regression fails with "ExpectedException not raised" even though production
fail-closed behavior is correct. Diagnose any "not raised" failure by reading
the production guard chain BEFORE blaming the product. Fix the FIXTURE, not
the product: attach a minimal real class instance
(`class _RealishArtifacts: pass`) to defeat only the mock-detection guard,
keeping the real capture seam patched
(`patch("module._capture_xml_text", side_effect=terminal_error)`).

**Boolean-guard ordering is part of the contract:** when acceptance says "X
must not be CALLED before Y", placing the expensive/forbidden call FIRST in an
`and` chain only discards its result — the call still happens (Python
short-circuits left-to-right). The forbidden call must sit LAST in the chain,
after every cheap boolean gate. Re-read the final hunk order before reporting;
a diff containing all the right tokens can still violate the acceptance
criterion by ordering (self-caught in the same session).

## Read-only worker-path provenance diagnostics

When a coordinator reports that a delegated worker wrote to an absolute Windows target but the parent appears unchanged, treat this as a provenance investigation—not as an implementation or recovery task. Use the exact path supplied by the coordinator first, and preserve the no-write boundary throughout.

1. Record the diagnostic shell's exact `pwd`; do not conflate it with the worker's working directory.
2. Query the requested repository with native Windows spelling and `git -C '<absolute target>' rev-parse --show-toplevel`, `rev-parse HEAD`, and `branch --show-current`. Compare the resulting root and HEAD with the coordinator's report.
3. Check the exact requested file paths on disk, but also resolve likely repository-relative paths from the actual tree. A root-level `source_config.py` being absent does **not** prove the source is absent: inspect tracked filenames (`git ls-files`) and allowed source directories for paths such as `python_runner/hermes_cron/source_config.py`.
4. For every relevant file, report existence, byte size, SHA-256, and (when useful) Git index/worktree state. On Windows, record EOL with `git ls-files --eol`; CRLF materialization can explain a size/hash difference even when Git reports no content diff.
5. Enumerate `git worktree list --porcelain`, branches, and related sibling directories (including the explicitly named `*-worktrees` directory). Report empty directories as empty; do not infer a hidden worker clone from a directory name alone.
6. Search only permitted source/test paths for matching artifacts and marker strings. Honor explicit exclusions such as secrets, workbooks, `.env`, logs, and generated runtime trees.
7. Attribute carefully: a worker is proven isolated only when the worker invocation terminal/path or process command line is available and differs from the requested absolute target. Existing sibling worktrees establish possible landing locations, not proof of which worker wrote them. If the process has exited, state that exact attribution is unavailable.
8. Distinguish three claims in the conclusion: (a) whether the current diagnostic terminal is in the requested repository, (b) whether a listed worker worktree is a different checkout, and (c) the exact path(s) where observable prior artifacts currently exist. Never label a modification as worker-authored without provenance evidence.

See `references/absolute-path-worker-provenance.md` for the reusable command/evidence recipe.

## Verification after a worker touches mixed PHP/HTML/JS scope

When the shared scope is a PHP template or provider integration, a worker's green harness is not enough. Re-read every scoped file before making a follow-up edit, then verify the current tree in layers:

1. **PHP layer:** parse all scoped PHP files with the real PHP linter when available. An AST parser is useful supplementary evidence when it is not, but report it as a parser check—not as `php -l`.
2. **JS layer:** extract and parse only the relevant inline block (for example, the block containing the changed toggle function). Do not parse every `<script>` tag blindly: PHP templates may contain third-party snippets, literal template content, or external-loader fragments that are not standalone JavaScript.
3. **Diff layer:** run `git diff --check`, inspect scoped `--name-only`/`--numstat`, and check EOL. Keep verification scripts outside the repository.
4. **Integration path:** for a new supplier/API type, verify add/edit symmetry across option → server-side validation → field toggle → persisted fields → cron registration → checkout adapter. A visible option alone is not sufficient; transport fields such as proxy must be stored on both add and edit paths, and auto-show must be enabled if the requirement is that synced products appear immediately.
5. **Inline error messages:** never interpolate an API message directly into an inline `<script>`. Use `json_encode` with `JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT` so a response containing `</script>` cannot break out of the script element.
6. **Unauthenticated probes:** a `401` proves the endpoint/auth gate exists, not that the catalog, cron, or purchase contract is correct. Do not call a real buy merely to make verification look complete.

See `references/mixed-template-and-provider-verification.md` for the reusable checklist and probe patterns.

## Windows focused-verification harness

When a system banner says verification is unverified and no canonical suite command was detected, create a fresh focused verifier in the OS temp directory with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)`, run it from the repository, and delete it in `finally`. Do not treat a failed harness launch as product evidence: nested `python -c` quoting on Git-Bash/Windows can corrupt multiline payloads and produce `SyntaxError: unexpected character after line continuation character`. Prefer a small launcher written outside the repo (for example with `write_file`) that generates the verifier, runs it, captures output, and cleans both files.

The verification banner may list temporary verifier paths as changed paths even when they are outside the repository. Treat every listed path as a fresh-evidence obligation: create one new OS-safe `hermes-verify-*` file, run it against the live workspace, clean it before final status inspection, and report cleanup explicitly. If the first ad-hoc probe fails because its external location cannot import the repository, fix the launcher with an explicit repository `sys.path` entry and rerun; classify the first failure as harness setup, not product behavior. Keep ad-hoc results separate from canonical suite counts, and never let a passing probe override a failing focused test or a source/test scope blocker.

For exact line-count checks on files ending with a newline, do not assert `len(text.splitlines()) == wc -l`; Python counts the terminal empty logical line differently. Assert raw-byte invariants such as `len(raw)`, `raw.count(b"\\n")`, and required content anchors, then run `wc -l` separately if the user specified the Unix count. The final evidence must explicitly label `Ad-hoc verification: PASS`, distinguish it from canonical suite green, and include a final `git status --short` showing that no temporary verifier path remains.

## Concurrency Routing Fixes: Atomic Admission and Hard Binding

When debugging or patching a priority router that repeatedly selects the first account, distinguish two separate contracts:

1. **Admission:** a `check-is-full()` followed later by `acquire()` is a TOCTOU race. Concurrent callers can all observe a free slot and then queue behind the same preferred account. Use an atomic, non-queueing reservation for priority spillover: reserve the current target or immediately try the next target in priority order.
2. **Binding:** the target's selected `connectionId` must survive every boundary—combo target, single-model handler, credential selection, chat core, and executor. A downstream selector that silently re-resolves credentials can undo correct priority spillover and send every request back to the top account.

Required verification:

- Test the atomic primitive for full-account rejection, no queued waiter, blocked-account rejection, release/replacement, and idempotent release.
- Test the production routing seam for `cap=5`: requests 1–5 use the first account, request 6 spills to the second, and a newly freed first-account slot is preferred again.
- Test hard binding with a target explicitly bound to a lower-priority connection and assert the executor receives that same connection—not the globally highest-priority account.
- Audit reservation ownership across early returns, exceptions, retries, non-stream responses, and stream finalizers. A bare release callback is insufficient when the code must distinguish a lease not handed off from one claimed by downstream code.
- A helper-unit green result is not enough; run typecheck/build and a concurrent integration or live-canary probe before claiming the routing bug is fixed.

See `references/concurrency-admission-and-binding.md` for the reusable matrix and implementation pitfalls.

## Pitfalls

- **Never revert/clobber foreign in-flight work.** Reverting is only safe if the writer is confirmed dead AND the coordinator authorizes rollback.
- **One fresh temp state root PER probe.** Journal/bridge/state share filesystem state; reusing one root lets a later probe silently replay an earlier probe's journal entries and return a misleading outcome (observed: unregistered-handler probe returned HANDOFF instead of NO_HANDLER_IMPLEMENTED because an earlier probe's HANDOFF was in the same root's journal). `tempfile.mkdtemp()` per probe.
- **Keep probe scripts OUTSIDE the repo** (e.g. `C:\Users\<user>\`), delete after. Keeps `git status` clean and avoids polluting the deliverable.
- **When the verifier reports no canonical test evidence, create a focused ad-hoc verifier instead of repeating a summary.** On Windows, create it with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)` so it lands under the OS temp directory; run it with the repo as `cwd`, add the repo to `sys.path` when the script is outside the repo (prefer `sys.path.insert(0, str(Path.cwd().resolve()))` over hand-escaped Windows literals when `cwd` is the repo), and remove it in `finally`. Assert the exact changed contract and its production seam (for example, captured policy, timeout, XML, and callback guards), and report it explicitly as **ad-hoc verification**, not as a green suite. If the first probe fails because an external temp script cannot import the repository, fix the invocation/path by adding the explicit `sys.path` entry and rerun; do not record that transient setup error as a product blocker. Immediately follow the ad-hoc probe with the canonical command in the same evidence window when one exists, then report the two labels separately.
- **Treat an `unverified` system banner as a fresh-evidence requirement, even if an earlier turn reported a passing suite.**
- **The banner can re-fire even after a fully verified turn — the temp verifier file itself is counted as a changed path.** Create the `hermes-verify-*` script, run it, delete it, AND run the canonical focused pytest node IDs all within ONE turn, reporting the two labels in that same response. Do not split create/run/delete across turns: a leftover temp script from a previous turn keeps the workspace flagged unverified and re-triggers the banner (observed 2026-08-11: banner listed `C:\Users\Kibe\AppData\Local\Temp\hermes-verify-*.py` plus the two repo files as changed paths even though the previous turn's verification had passed).
- **A sibling subagent can commit mid-session and ABSORB your working-tree changes** (observed 2026-08-18: sibling `20260816_213915_15ea28ed` committed `df9051d` including the picker production rewrite + most test fixes; my own 4 test patches landed inside that commit and the final `git status` was completely clean). Consequences: (1) re-run `git status --short` + `git diff` before every patch — a file you read 5 minutes ago may have been rewritten (patch tool warns "modified since last read"); (2) when the suite turns red AFTER you verified it green, check `git diff` on the test file for a sibling's HALF-EDIT — e.g. a golden-vector constant updated (`reference_assignment`) while its dependent constant (`reference_entry`, which hashes the manifest_id) was left stale, failing mid-file; recompute the dependent value by RUNNING the production code (`hashlib` + `stdlib_reference_bytes` recipe), patch the one stale line, re-run the full suite TWICE; (3) a clean `git status` at the end is not "nothing happened" — check `git log --oneline -5` + `git show --stat HEAD` to attribute the commit, and report "implemented by sibling commit <sha>, verified by me".
- **For comment-only Python edits, verify both documentation and the preserved seam.** Create the verifier with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)`, assert the exact required comment lines plus `ast.parse()` and the nearby logic anchors (for example, the account-only index and identity-mismatch raise). Run the temp script from the repository, delete it in `finally`, then run the canonical suite in the same evidence window; report `Ad-hoc verification: PASS` separately from `N passed`. Prefer a Python wrapper over deeply nested `python -c` quoting on Windows git-bash. In the current turn, run the temporary verifier and show its PASS output before finalizing. For time-window boundary edits, prefer a seam-level probe that exercises the production methods directly (e.g. construct the object with `__new__` when full fixture setup is unrelated), assert both sides of the boundary (`01:59` accepted vs `02:00`/`02:30` rejected or handed off), and use a fresh temporary state root per probe. Keep the report labels separate: `Ad-hoc verification: PASS` is not a substitute for `N passed`; only claim canonical suite status from a command executed in the current evidence window.
- **Probe fidelity — forge probes must mirror the production derivation exactly.** When a probe re-hashes identity (`assignment_id`/`entry_id`/`block_id`), replicate every production input including DERIVED sets: `account_ids` is the manifest coverage set (entries ∪ skipped), digest `"0"*64 → None`, `generation` passthrough. Fixture dicts must satisfy the parser's EXACT key-set check — one extra typo key silently invalidates every state → picker skips the whole lane → EMPTY payload → the probe "passes" via the legacy/empty path and the real branch is never exercised (tell: `IndexError` on `payload["blocks"][0]`). Assert seam preconditions (`len(blocks) == 3`) before probing. Full incident detail: `references/probe-fidelity.md`.
- **The canonical suite is the tie-breaker between probe bug and product bug.** If an ad-hoc probe fails but the suite has a PASSING test with the same attack shape, the probe's derivation is wrong — fix the probe, never touch production (observed: source-less machine-999 forge probe errored `MANIFEST_IDENTITY_MISMATCH` while the identical-shape r10 test passed). Report probe fixes as probe bugs, separate from product evidence.
- **Persist the baseline OUTSIDE the repo (evidence dir) and re-compare at the END of your run.** Foreign writers can edit repo files DURING your runtime window (observed 2026-08-12: repo gained 3 modified files — bat + 2 scripts + AGENTS.md — while a watcher restart run was in progress, with mtimes inside my window). You know every file YOU touched; anything in the final `git status`/`git diff --name-only` that is newer than your baseline and not on your touched list is foreign. Attribute by (a) your own touched-file list, (b) the pre-change snapshot (`git status --short` + `git diff --name-only` saved to `...evidence/prechange-<stamp>/` at session start), (c) file mtimes — then report "foreign, not mine" instead of absorbing the changes into your deliverable or reverting them. Re-confirmed 2026-08-24 (tiktok-luot nuoi acc): a foreign dirty file's sha256 differed between baseline and final check (mtime inside my window) while my allowlist files stayed hash-pinned; report "unchanged BY ME" with per-file hashes, never blanket "identical all session".
- **mtimes alone aren't proof** — correlate with `date`, process list, and content diffs before accusing anyone.
- **A file you ALREADY read this session can go stale under you.** A foreign writer can rewrite a scoped file minutes after your `read_file` (observed 2026-08-12: test file rewritten 133→147 lines between my read and my verification — assertion changed `assert not out_dir.exists()` → `assert out_dir.is_dir()`). Your byte-identical out-of-repo replication then FAILS while the in-repo canonical suite PASSES, which looks like a probe bug (and the tie-breaker rule says fix the probe) — but the real cause is that the SUITE executes live disk content while your snapshot describes a superseded version. Resolution order: (1) re-stat scoped files and re-read timestamps/TEST file line counts right before running anything; (2) if line count or content differs from your earlier read, your analysis may be based on a ghost version — re-read the actual file before touching production; (3) only then apply probe-vs-product tie-breaking. Never conclude "suite contradicts my read" without re-reading the file in the same evidence window.
- **Out-of-repo pytest replication scripts on Windows: `$TEMP` in git-bash maps to `/tmp` (MSYS path) which native Windows pytest cannot resolve** (`file or directory not found: /tmp/...`, collected 0 items, exit 4). Use a Windows-visible temp path for replication files — e.g. `tiktok-follow` write_file to `/c/Users/<user>/AppData/Local/Temp/...` or `Path(tempfile.gettempdir())` — then delete after; a bash-`$TEMP` path is a silent runner fault, not product evidence.
- **Don't adopt foreign changes as your own work product** in the final report — separate "implemented by" from "verified by".
- **Exclusive artifact-import workflow:** when a repository-integrity task requires committing an existing set of untracked artifacts from a dirty shared root, do not edit or stage in that root. Create a fresh named worktree from the exact required parent/ref, run the canonical combined suite there in the pre-import RED state, verify each allowlisted source artifact's content hash before copying, copy only the exact allowlist, then run GREEN/compile/EOL/hash checks and stage explicit paths. Record the exact artifact count and post-commit `git show --name-status`; never use `git add .` or infer scope from a broad directory.
- **Fuzzy patch on blank-line-heavy files corrupts indentation during revert-style edits.** feed_swipe_smoke.py uses double-spaced lines; a replace whose old_string/new_string differ mainly in removed middle lines made the tool re-anchor the tail at wrong indent (4→8 spaces), producing IndentationError lint in the SAME response. Never craft a revert edit where the trailing context lines are identical between old/new except leading whitespace of one line — instead revert ONLY the inserted block itself (match exactly the added comment+flag lines plus their immediate neighbors, restore to pre-insert shape). Always run py_compile immediately after any multi-line removal on such files and fix from the actual read_file output, never from memory.
- **An AST-source-inspection regression is the smallest safe guard for call-site kwargs in giant flows.** When a wrapper call site lives inside a huge session flow that cannot be invoked in tests (device/session mocks would explode), assert via `textwrap.dedent(inspect.getsource(fn))` + `ast.walk` filtering Call nodes whose checkpoint kwarg matches a unique string literal, requiring the target kwarg to be an `ast.Constant` with the right value. Filter on `ast.Name` (plain module-level calls), NOT `ast.Attribute` — module-level helper calls parse as Name. Distinguish same-file sibling call sites by distinctive substrings of their f-string checkpoint args when one sibling legitimately differs.

- **Git-Bash Windows worktree paths:** `/d/...` can be rewritten unexpectedly when passed as a `git worktree add` argument from a repository whose path is already MSYS-translated. After creation, immediately inspect `git worktree list --porcelain` and `git rev-parse --show-toplevel`; if the worktree landed under `D:\\d\\...`, remove only that self-created worktree and recreate with a native Windows path such as `D:/Taadaa/...`. Do not run tests or copy artifacts until the canonical target path is verified.
- **Immutable artifact vs diff-check:** a byte-for-byte adoption can contain pre-existing trailing whitespace. Run `git diff --check` and report the exact immutable artifact/line as a known pre-existing warning; do not silently alter the artifact to make the check green. Separately run `git diff --check` excluding that immutable file and require PASS for all other scoped files; preserve the original hash. See `references/exclusive-artifact-import.md`.
- **Check EOL/line-ending drift** when a foreign writer touched files (all-LF vs CRLF) — `git diff --check` is vacuous for untracked files; check manually.
- **Foreign dirty files block `git pull --rebase` but not `git push`.** A failed pull ("cannot pull with rebase: You have unstaged changes" from another agent's in-flight work) does NOT mean your commit can't go out — if the remote has no new commits, `git push` still succeeds. Stage only your exact paths, commit, push, and verify the remote ref separately (`fdd66b3..<sha> master -> master`); leave the foreign dirty files untouched and report them as someone else's.
- **A concurrent writer's earlier run can leave STALE `__pycache__` that
  shadows the newer source** (verified 2026-08-12, tiktok-follow): pytest
  ran test `test_mode2_missing_fails_closed` and failed `assert True is
  False` at a line number pointing at OLD test code, while the `.py` on disk
  had already been renamed/rewritten to
  `test_mode2_module_available_after_implementation` (foreign commit
  `9c3465f` landed mid-session). Python reuses `__pycache__/*.pyc` when the
  `.py` mtime matches, and a concurrent writer's earlier compile left a pyc
  that no longer corresponds to the new text. Fix when a failure references
  test names/lines that don't match the file on disk: delete ALL
  `__pycache__` dirs (`find <repo> -name __pycache__ -type d -exec rm -rf {} +
  ` or a `os.walk` shutil.rmtree loop) and re-run; the suite then executed
  the current tests (107 passed). Before blaming the product, always
  reconcile the failing test name against the live file.
- **A foreign writer can COMMIT the dirty file and move HEAD mid-session, not just edit it.** Observed 2026-08-12: a ` M` file from the baseline snapshot was committed by another process (`b34f410 fix(watcher)...`) while a read-only discovery session ran; final "repo unchanged" verification then failed on the tracked-file line even though the worker never ran a write command. Attribution checklist: (1) `git reflog -8 --date=iso` to timestamp every HEAD move — a commit whose author/time is not yours is foreign; (2) `git show --stat <sha>` to see exactly which file the foreign commit touched (must match a previously-dirty path); (3) compare untracked-path sets, not just `git status` text — the 7 untracked paths were identical while tracked state changed. Report as "7 untracked identical; tracked dirty state changed by external commit <sha>, not mine" — never claim blanket "unchanged". Your own git calls on a watched repo must stay read-only (`rev-parse`/`branch`/`status`/`ls-files`/`log`/`reflog`/`diff`/`show`/`worktree list`); `git worktree add` only writes `.git/worktrees/` metadata.
- **Baseline must be the EXACT suite command from the plan/rules, not a per-file loop.** pytest collection differs between invocations: a module that fails collection standalone (`ModuleNotFoundError: core.classifier` when run from repo root with namespace-package layout) collects fine inside the multi-file command because earlier modules' basedir insertion changes `sys.path`. A per-file loop therefore manufactures fake pre-existing errors. Run the canonical combined command once, record its collected/error counts, THEN run per-file breakdowns only as diagnostics labeled as such.
- **Record the ambient interpreter and its installed dist versions with every baseline.** The repo pin (`requirements-automation-core.txt: 0.4.18`) is NOT what pytest imports — the hermes venv may hold a different `automation_core` (observed 0.4.43). Baseline green on a newer installed core is still valid evidence (closer to the upgrade target) but must be labeled with `python -c "import importlib.metadata as m; print(m.version('automation_core')); import automation_core; print(automation_core.__file__)"` so a later GREEN comparison isn't misattributed. Classify collection errors by traceback location: errors whose chain is inside site-packages/venv (e.g. a broken PIL `_imaging` C-extension) are environment-pre-existing, not repo defects — capture the classification technique, not the specific broken package.
- **Never embed a file's own SHA256 inside the file.** A report that states its own hash creates an edit→hash-change→edit loop: every fix that keeps the field accurate changes the hash, and fixed-point iteration can diverge/timeout. Write the deliverable hash-free, compute the hash in the final verification step, and report it in the summary; if the report must reference verification, say "hash computed at verify time, recorded in worker summary".
- **Terminal heredocs whose content contains `&` are rejected as backgrounding** ("Foreground command uses '&' backgrounding") — use `write_file` for such content instead of `python - <<'PY'` heredocs; same rule as inline python with `&` bitwise ops.
- **Diff-audit worker output for REMOVED lines, not just added files** (verified 2026-08-12, P1 feed pilot): a worker's "minimal" edit silently dropped `"ADAPTER_CAPABILITIES"` from a module's `__all__` — the constant still existed and was still used internally, `git status`/`--stat` looked clean, and only scanning the actual `git diff` for `^-` lines surfaced the lost export. Before approving any worker diff: (1) run `git diff` and grep removed lines (`git diff | grep '^-'`) explicitly; (2) for modules with explicit export lists (`__all__`, `__init__` re-exports), diff the name set against HEAD (`git show HEAD:<file> | grep -A30 '^__all__'` vs working tree); (3) restore dropped entries — never let a worker's patch silently shrink a public API surface, even when nothing in-repo imports the name yet.
- **A long canonical-suite run can STRADDLE a foreign write: green-then ≠ green-now** (verified 2026-08-23, tiktok-luot nuoi acc review). pytest imports at collection time, so a combined run started 15:15:35 executed PRE-drift bytes while the concurrent writer edited scoped prod+test files at 15:16:29 and 15:20:10 — INSIDE the run window; the printed "321 passed" described a superseded tree while the deliverable claimed the current one. For any suite longer than a couple of minutes in a shared worktree: record run start/end timestamps, RE-STAT every scoped file AFTER the run, and compare mtimes against the window; any hit ⇒ label the green result as evidence about pre-drift bytes, diff the drift, and re-run at least the modules owning the changed files on current bytes before finalizing. Mirror hazard: a writer who TIGHTENS production (e.g. lenient 8-byte PNG-signature `startswith` check → strict `_is_valid_png` chunk/CRC gate placed EARLIER in the early-return chain) while leaving an OLDER test's fixture built to the lenient contract yields a red that mimics a product regression — read the drifted hunks and check gate ORDER (a new earlier return fires before the branch the old test asserted) to attribute the red to the writer's incomplete fixture reconciliation, not to the reviewed candidate.
- **The review "candidate" may already be a COMMIT when you look** (observed 2026-08-23): all five allowlisted files showed clean vs HEAD although the brief described uncommitted intended fixes — the writer had committed them as `6dfd722` at 14:42:34. When scoped paths come back clean, immediately run `git log -3 --format='%h %ad %s' --date=format:'%m-%d %H:%M:%S' -- <file>` per allowlist file; if one fresh commit covers exactly the allowlist, review `git show <sha>` (verify --name-status ⊆ allowlist, scan removed lines, reconcile numstat vs --stat) instead of `git diff`, and keep treating subsequent dirt as NEW drift to assess separately. **A later commit can absorb a staged remediation while the reviewer is still evaluating an older SHA** (observed in the same session: an external writer committed `bf88db6` and then `cdb9bd1`/`1ce7e88` while PNG/identity remediation was staged, then continued editing the same files). Before every review/commit gate, re-read `HEAD`, `origin/<branch>`, `git reflog`, staged paths, and `git diff HEAD`; if HEAD moved or a scoped file was rewritten, discard the stale verdict, reconstruct the intended patch from the new HEAD in an isolated/index-only operation, and obtain a fresh review for the exact new commit. When concurrent commits already include part of the fix, stage ONLY the remaining incremental delta (e.g. 14 lines) on top of the latest HEAD rather than re-committing the entire module. Never stage or commit while a concurrent writer owns any path in the candidate; stop at `BLOCKED_AT_CONCURRENT_WRITER_REVIEW` and preserve all dirty paths. Reviewers must receive `git show <exact-sha>` or the exact staged diff—not a possibly different working-tree diff—and their verdict binds only to those exact bytes. Related: a preserved rules file may cite a canonical suite command from a DIFFERENT repo (observed PROJECT_RULES.md:909 pointing at `tests/test_tiktok_workflow.py`, absent locally) — verify the cited command resolves in THIS repo before calling it canonical; otherwise run the coordinator-attested module set, report its actual counts, and label it as the attested command.

## References

- `references/android-deep-link-regression.md` — evidence-backed coordinate tap followed by exact CDP-verified Android VIEW intent, strict postcondition verification, no generic `here` fallback, CRLF-safe fixture testing, and honest ad-hoc verification when canonical detection is unavailable.
- `references/r7-collision-case-study.md` — full timeline and evidence from a real scope collision during an audit-remediation round (detection signals, probe table, RED sourcing).
- `references/windows-probe-execution.md` — running verification probes on Windows git-bash (path mangling, sys.path, heredoc failure, fresh-root rule, search_files os-error-3 fallback on non-ASCII dirs).
- `references/fresh-verification-windows.md` — fresh ad-hoc verification when a harness reports unverified, including tempfile probes, explicit source imports, fake-only assertions, cleanup, and honest reporting.
- `references/probe-fidelity.md` — forge/re-hash probes must mirror production derivation exactly (fixture exact-key-set traps, coverage sets incl. skipped accounts, canonical suite as probe-vs-product tie-breaker) plus: branch-deaf suite tests (bare raises() passing via an earlier gate), the observable-difference principle when the literal attack shape can't reach its branch (fail-closed canonical-slot binding, per-machine block counts), and the full manifest identity re-hash chain (assignment_id first, then entry/block ids against the new manifest_id).
- `references/stale-read-collision-dump-selectors.md` — full timeline of a scope collision where the scoped TEST file was rewritten (133→147 lines, assertion flipped) between my read and my verification: replication-fails-while-suite-passes trap, ghost-version reads, resolution order (re-read before tie-breaking), and Windows `$TEMP`→`/tmp` pytest runner fault.
