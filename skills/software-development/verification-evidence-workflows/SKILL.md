---
name: verification-evidence-workflows
description: "How to produce fresh, isolated verification evidence after code edits — ad-hoc temp-script verification when a harness reports 'unverified', and edit-hygiene pitfalls for large modules under TDD."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, testing, tdd, evidence, edit-hygiene]
    related_skills: [test-driven-development, systematic-debugging]
---

# Verification Evidence Workflows

## When this applies

- A host/harness re-scans after each edit and posts `Verification status: unverified`
  because no canonical test/lint/build command was detected in-band.
- You have finished a TDD cycle (RED→GREEN→verify) but the harness still wants
  proof the changed behavior actually runs.
- You are editing a large implementation module (hundreds of lines) with several
  structural changes and `patch` calls start colliding.

This is the *evidence* layer on top of TDD. TDD proves the test catches the bug;
this skill proves the edit is live-verified and the file is coherent.

## Core: ad-hoc verification (not "suite green")

When flagged unverified, do NOT restate a previous pass from memory. Produce fresh
evidence on demand:

1. Snapshot the pre-existing `hermes-verify-*.py` files in the OS temp directory
   and record only the path(s) created by this run as owned artifacts.
2. Write a temporary verification script under `C:\Users\Kibe\AppData\Local\Temp`
   using an OS-safe `tempfile` path with a `hermes-verify-` filename prefix.
3. Keep it focused:
   - Run the exact named test nodes via pytest (copy the node IDs from the plan).
   - AND/OR a small runtime smoke: import the module, exercise the changed
     behavior with a mocked boundary (no live process / NO-LIVE), assert contract
     invariants (canonical argv, fail-closed states, consume-once, etc.).
   - Include explicitly requested static checks (for example AST, `py_compile`,
     and scoped `git diff --check`) when the task contract names them.
4. Run it from the repository root via a fresh Python subprocess, capture the
   actual stdout/stderr and exit code, then report the exact counts. A prior
   canonical pytest result and the temporary probe are separate evidence lines.
5. Delete only the current run's verifier and private pycache in a `finally`
   block; verify both are absent. Preserve pre-existing `hermes-verify-*` files
   and report that preservation. If the harness repeats `unverified` after a
   prior ad-hoc report, repeat this entire ownership-and-execution sequence in
   the new turn instead of merely quoting the earlier output.

**Windows path rule:** keep path injection out of nested `.format`/f-string
source generation. Pass the repository root through the child environment or
construct it with `Path` inside the verifier; this avoids backslash escaping
and space-containing worktree failures.

**Windows launcher rule:** do not build a multiline verifier with deeply nested
`python -c` quoting through Git Bash. That can fail in the launcher before the
verifier runs (`SyntaxError: unexpected character after line continuation
character`) and is harness setup failure, not product evidence. Use a tiny
out-of-repo launcher file, have it create the actual verifier with
`NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(),
delete=False)`, run it from the repository, and clean only the paths it created.
See `references/windows-fresh-verifier-launcher.md`.

**Launcher/verifier process-boundary rule:** the launcher and generated verifier
run in separate Python processes. Keep launcher helpers (digest, allowlist,
pre/post hashes, cleanup ownership) defined in the launcher, and verifier
helpers defined in the generated script; never assume a name crosses that
boundary. Run the generated verifier unbuffered (`python -u`) with explicit
stage markers and exit codes. A launcher/verifier `NameError`, quoting error,
or cleanup failure is verification failure—not product evidence. The final
report must include the generated verifier's real exit code, focused-test
result, exact allowlist hash stability, and current-run cleanup result.

**NO-LIVE smoke rule for deadline/fence changes:** when verifying timeout,
watchdog, or single-winner publication fixes, add a small mock-only runtime
probe in the generated verifier—not only string/AST checks. Assert the expired
hard-deadline path does not call `subprocess.run`, and assert one terminal owner
wins while the losing owner cannot publish. Do not touch devices, workbooks,
cron, credentials, or real subprocess targets.

**Always label it ad-hoc verification, not "suite green."** The difference matters:
a full-suite run is durable regression proof; an ad-hoc script is a point-in-time
check you wrote to satisfy a specific "is it actually verified?" prompt.

Reusable recipe: `references/ad_hoc_verification.md`.

### Pinned shared-core compatibility fixes

When a consumer must remain compatible with a pinned shared dependency and the task forbids changing lock/live state, verify the dependency contract at the real seam rather than relying on a permissive mock:

1. Resolve/import the exact pinned artifact used by the test command.
2. Add a strict fake boundary that rejects unsupported arguments/statuses before editing production code.
3. Run the exact regression node and capture the expected RED caused by the contract mismatch.
4. Make the smallest production change at the wire boundary; preserve neighboring consumer state and release semantics.
5. Re-run the focused node, then compile/diff-check and (when affordable) the broader suite with the same dependency artifact.

Use a fresh temp verifier when the harness still reports `unverified`; create/run/delete it in one evidence window and prove old verifier paths are absent before finalizing. Details and the strict-lease example are in `references/shared-core-version-compatibility.md`.

For the deployment-side counterpart (core source fix → versioned wheel build → artifact copy to the pinned path → consumer file-pin repin → isolated provenance probe via wheel-extract + PYTHONPATH subprocess → dual-wheel A/B pre-existing-vs-regression attribution), see `portable-consumer-repo-maintenance` §"Offline versioned-wheel bump and consumer repin".

Gated tasks needing AG Opus exact-byte approval + exact-allowlist commit
(delegate-crash fallback, pre-commit audit invocation, commit guard rails,
Windows spawn shim, fake clock): `references/exact-byte-gate-execution.md`.

## Dirty-tree scope classification before evidence

A dirty repository is not automatically a conflict and must not widen the
verification scope. First classify every staged/unstaged path against the
current task contract:

1. Paths outside the exact allowlist are `OUT_OF_SCOPE`. Ignore them; do not
   inspect, edit, revert, reset, unstage, stage, wait on their processes, or
   attribute their failures to the current task.
2. Paths inside the allowlist may contain pre-existing staged or unstaged hunks.
   Staged state alone is not proof of a concurrent writer.
3. Only a content/hash/mtime change to an allowlisted file or overlapping region
   during the current ownership window proves `SCOPE_CONFLICT`; otherwise run
   verification against the stable current tree.
4. Report staged and working-tree path sets separately. Do not label the whole
   repository conflicted merely because unrelated files are dirty.

## Evidence binds to exact candidate bytes

Test output is only evidence for the bytes that actually executed. In shared
worktrees with concurrent writers/committers, a green run can predate the final
candidate:

- If `git diff <paths>` comes back EMPTY while `git status` still lists the files
  as modified, do not conclude "no changes" — the files were likely staged.
  Re-read `git status --porcelain` and use `git diff --cached`.
- Re-snapshot `git status` + `git log -1` after every anomalous tool result
  (empty diff, missing hunk, unexpected failure). Cheap read-only re-checks are
  free; misattributed evidence is not.
- If HEAD moved (the writer committed) between reading the diff and running the
  tests, rebind to the new SHA: compare `git show <sha> --stat` per-file line
  counts against the diff you reviewed, inspect any NEW hunks (additive/test-only
  vs production change), then re-run the focused suites against the exact final
  bytes before reporting results. Prior runs on older bytes don't count.
- A failed run that overlapped a since-reverted transient mutation is NOT a
  regression signal. Verify the tree matches the candidate again
  (`git status` clean vs the SHA, `git diff --stat` empty for scoped paths),
  then re-run. Report the false failure and its cause; never drop it silently.

### Current-tree structural consistency gate

When a sibling worker or another session changes an allowlisted file after your
last read, stop all further source edits in that overlapping scope. A fresh
verification-only pass is still allowed, but it must bind to the live bytes and
check call/definition consistency before interpreting pytest output:

1. Re-read the changed region and snapshot `git status`, working diff, cached
   diff, and scoped hashes before running tests.
2. Parse the live module with AST and compare newly introduced production calls
   against their definitions: keyword arguments must exist in the callee
   signature, referenced helper names must be defined or imported, and wrapper
   contracts must agree. Presence-only checks are insufficient.
3. Run a small NO-LIVE verifier against the changed seam with mocked boundaries.
   Treat an undefined symbol, signature mismatch, or import-context failure as a
   concrete verification failure, not as a harness detail.
4. Run the canonical focused test only after the structural probe. If it fails
   because the current bytes are internally inconsistent (for example, a wrapper
   calls an undefined helper), report the exact failure and retain
   `VERIFIED_CURRENT_TREE`/blocked status; never patch around an ownership
   conflict, claim an earlier pass, or label the task `FIX_COMPLETE`.
5. If the current tree changes again during this window, discard all evidence,
   re-read, and rerun the structural probe and canonical checks.

This gate is especially important for large Python modules where a worker can
land half of a coordinated change (such as an executor wrapper plus a matching
child signature) while the parent is only asked to verify. The reusable Windows
recipe and the observed `shallow_copy`/`hard_deadline` signature-mismatch pattern
are recorded in `references/current-tree-structural-verification.md`.

## Pitfall: stacking fuzzy `patch` on large modules

`patch` uses fuzzy context matching. Stacked edits on the same region drift and
leave the file half-broken:

- A "succeeded" patch inserted a new function *inside* an existing function body,
  so the original function's trailing lines ran as top-level code → `NameError`.
- Repeated `patch`/`write_file` cycles propagated stray renamed constants
  (`_DISABLED`, `__DISABLED`) and duplicate defs.

**Fix:** once the interface is settled, re-read the whole file, then do ONE clean
`write_file` of the full corrected module. Reserve `patch` for single,
well-isolated, one-shot edits. Prefer writing the new module in full once rather
than nudging it into shape through many partial edits.

If you must patch a big file, patch ONE region, re-read, then patch the next —
never accumulate 3+ pending edits against the same paragraph.

## Shared-worktree staged-vs-working-tree gate

When a candidate is partly staged and the working tree has newer edits, never review or report the staged tree by implication. Run tests against the intended final bytes, then explicitly reconcile the two views:

1. Record `git diff --cached --name-only` and `git diff --name-only` separately; preserve unrelated staged files and do not use `git add -A`, whole-tree reset, stash, or cleanup as a shortcut.
2. For every allowlisted file, compare the index/worktree state with `git diff-files --quiet -- <allowlist>` and capture blob hashes after the final edit. If tests ran against newer worktree bytes than the cached candidate, re-stage only the allowlist before review.
3. Review exactly the final cached payload (`git diff --cached --binary -- <allowlist>`), not a working-tree diff assembled earlier. Recompute the payload hash immediately before and after the reviewer call; any change invalidates the verdict.
4. Treat a same-file writer change during the ownership window as `SCOPE_CONFLICT`; stop source edits in that overlap. A green test on subsequently changed bytes is only `VERIFIED_CURRENT_TREE`, not proof of the previously reviewed candidate.

## Identity-bound UI bounds compatibility gate

UI parsers and shared-core helpers may represent the same rectangle differently. Before enforcing an identity/header bound match, inspect the actual contracts and normalize at the seam (for example parser `(x, y, width, height)` versus core `(left, top, right, bottom)`). Test both a valid exact match and malformed, duplicate, or suggested-card mismatches. A direct tuple comparison can silently turn every valid Path-B verification into `MANUAL_REVIEW`, while a loose overlap check can accept the wrong profile.

## Live batch verification gate

For a production batch that writes files and maintains state (downloaders, renderers, importers, crawlers), a successful launch is not proof of progress. Before reporting success:

1. Stop duplicate writers first. Identify the exact production command and process tree; stop only matching job processes; verify zero matching workers before relaunching.
2. Capture baseline and post-launch evidence: state-DB counts by status, folder states, newest output-file mtime/count, newest report mtime, and the last fatal traceback.
3. Separate process crash, state-recovery failure, source-pool shortage, per-item provider errors, and output-verification failure. `INSUFFICIENT_POOL` is not a download success.
4. Resume every active state: reset folders/items left in `reserved` or `downloading`, restore source/channel-to-folder claims, and preserve the invariant that one folder uses one source/channel.
5. Validate provenance before retrying: folder niche/platform must match the source niche/platform. Do not mix channels or weaken gates merely to make the counter move.
6. Run a single known-good canary first and assert a real output file, non-trivial bytes, media probe success, matching downloaded DB row, and matching report provenance. Scale workers only after this canary passes.
7. After a bounded interval, require a fresh output mtime/count increase. If output is unchanged while the process only emits pool/claim/provider errors, stop it and report the blocker rather than letting a no-op batch run.

The user's preferred operational report is short: action, verified result, blocker, next action. Do not add unrelated farm commentary when the job is an independent downloader.

Detailed SQLite/ledger/resume incident pattern: `references/live-batch-recovery.md`.

## NO-LIVE constraint

Ad-hoc verification must not spawn real processes, touch devices, read credentials,
or mutate live state. Inject mocks/lambdas for the launcher/boundary under test.
If a real run is required to verify, stop and ask — do not fake the evidence.

## Fresh finalization gate (Windows, after the last edit)

Treat the harness `unverified` banner as a new evidence request, not as a prompt to repeat an old summary. After the final state-changing edit:

1. Re-read/re-stat the exact allowlist and confirm no foreign writer changed those bytes during the verification window. If they changed, rebind the verifier to the new bytes and rerun.
2. Create one OS-safe verifier with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)`. The verifier should add the repository path explicitly when launched outside the repo, parse the changed files with `ast.parse`, and run the exact focused pytest command with `-p no:cacheprovider`.
3. Run the verifier from the repository, capture its real output and exit code, then delete the temporary file in the same evidence window. Verify that no `hermes-verify-*` path remains.
4. Report the result as **Ad-hoc verification: PASS** (or the concrete blocker), separately from the pytest count. Never call this "suite green" or claim that a prior test run proves the post-edit bytes.

This procedure is NO-LIVE: use only tmp-path fixtures and fake boundaries; do not invoke sync/live/device/workbook/journal state merely to satisfy verification.

## Scoped candidate and staged-byte verification

When the worktree is already dirty or the candidate is partly staged, bind
verification to the exact allowlist rather than the whole repository:

1. Snapshot `git status --short`, `git diff --name-only -- <allowlist>`, and
   `git diff --cached --name-only -- <allowlist>` before the final run. Treat
   pre-existing staged and unstaged hunks as separate candidate bytes; do not
   reset, unstage, or clobber them.
2. Run `git diff --check -- <allowlist>` and, when cached bytes are part of the
   candidate, `git diff --cached --check -- <allowlist>`. A repository-wide
   `git diff --check` can report unrelated pre-existing whitespace changes and
   is not evidence against a scoped candidate.
3. Re-run the focused test and static checks after the last edit, even if the
   same commands passed earlier. Report working-tree and cached path sets
   separately when both exist.
4. If a test fixture schema changes, update every in-scope fixture producer and
   direct literal in the focused test file before interpreting failures; do not
   weaken the production validator to preserve stale fixtures.

## Checklist

- [ ] Final edit bytes were re-read/re-statted before verification
- [ ] Temp script uses `hermes-verify-` prefix and an OS-safe temp directory
- [ ] Verifier uses explicit repo import path when outside the repo
- [ ] Runs exact plan nodes (or equivalent) and shows real output
- [ ] Runtime smoke uses mocked boundary, asserts contract
- [ ] Temp script deleted in the same evidence window; no verifier path remains
- [ ] Report explicitly states "Ad-hoc verification" not "suite green"
- [ ] Large module edited via single clean rewrite, not stacked fuzzy patches
- [ ] Working and cached scoped path sets were checked independently
- [ ] Scoped diff checks were used; unrelated dirty whitespace was not attributed
  to the candidate
