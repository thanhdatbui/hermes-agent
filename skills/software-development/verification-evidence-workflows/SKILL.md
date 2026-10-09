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
- A vision/OCR service produces structured blocks that must be rendered into a
  selectable-text artifact; use the same fail-closed completeness and fresh-artifact
  gates before claiming the document is final.

### Structured vision-document artifact gate

For multi-page vision translation or OCR pipelines, treat the model response as
source data, not as a finished artifact. Persist one machine-readable record per
page with `page`, `source`, `translation`, `rect`, `fontsize`, `bold`, and `align`;
reject missing pages, empty block lists, malformed rectangles, or missing translations
before rendering. If the schema is nested (for example `{"pages": [...]}`), make the
loader explicitly support that shape and test it against the live JSON rather than
assuming the older flat mapping shape.

When the vision API returns normalized image coordinates, convert them exactly once
at the render boundary into the target PDF coordinate system, scaling both rectangles
and font sizes from the captured image dimensions. Preserve source scan pixels and
add selectable vector text without opaque white-out unless replacement is explicitly
required. A valid schema alone does not prove coverage: report page/block counts and
spot-check required terminology and model identifiers from the persisted JSON.

Keep the draft state fail-closed: emit draft labels and `DRAFT_NEEDS_REVIEW` whenever
any page/block validation fails, and suppress those labels only after all 18 pages (or
the contract's full page set) pass validation. Run the focused compile check and a
fresh render, then verify page count, selectable text extraction, and representative
previews from the first, middle, and last pages. The concrete 9Router/Vision capture
pattern is documented in `references/vision-structured-document-capture.md`.

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

### Same-turn probe execution discipline

A verifier is not evidence until the generated file itself has been executed.
Use a two-command boundary: first create the owned `NamedTemporaryFile` and
print its literal native path; then run that exact literal path in a separate
top-level command from the repository root. If the command guard rejects a
foreground timeout above its limit, lower the timeout and rerun—the guard is a
launcher constraint, not product evidence. After a passing run, delete only the
owned path and explicitly verify deletion. Preserve and report any pre-existing
`hermes-verify-*.py` files separately. In the final report, state the probe's
real exit code and test count, call it **ad-hoc targeted verification**, and do
not re-label it as canonical suite green.

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

**Pitfall: using `write_file` tool for temp verifiers re-triggers `unverified`.**
Any file touched via the agent `write_file` tool (even under `Temp/`) gets registered as a `Changed path` by the harness, causing subsequent turns to report `unverified` with the temp file itself listed alongside target code.
Never use the agent's `write_file` tool to create verification scripts. Run tests directly via `terminal` command, or create/run/delete the verifier entirely inside a one-shot Python process launched from `terminal` with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", delete=True)`.

Reusable recipe: `references/ad_hoc_verification.md`.

### Pinned shared-core compatibility fixes

When a consumer must remain compatible with a pinned shared dependency and the task forbids changing lock/live state, verify the dependency contract at the real seam rather than relying on a permissive mock:

1. Resolve/import the exact pinned artifact used by the test command.
2. Add a strict fake boundary that rejects unsupported arguments/statuses before editing production code.
3. Run the exact regression node and capture the expected RED caused by the contract mismatch.
4. Make the smallest production change at the wire boundary; preserve neighboring consumer state and release semantics.
5. Re-run the focused node, then compile/diff-check and (when affordable) the broader suite with the same dependency artifact.

### Filesystem-independent test isolation (hardcoded paths & host leaks)

When unit-testing path resolvers, fallback roots, or legacy media locators that contain hardcoded absolute paths (e.g. `Path(r"D:\TIKTOK-videonuoinick")` or `Path(r"D:\video goc")`):
- **Pitfall:** A unit test using a real/common slot name or folder id (like `489`) alongside partial monkeypatching can silently leak into the host machine's real drive (`D:\...`), finding real files on disk instead of exercising the fallback or raising the expected exception.
- **Fix:**
  1. Use isolated dummy folder identifiers (e.g. `test_slot_dummy_99999`) never present on real disks.
  2. If monkeypatching `pathlib.Path`, intercept **all** hardcoded search/fallback roots referenced by the function under test (normalizing paths case-insensitively and with forward/backward slashes), redirecting them to non-existent temporary directories (`tmp_path / "fake_dir"`).
  3. Ensure the test passes 100% independently of host disk state.

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

## UI recovery-choice selector gate (Google-style challenge pages)

When a recovery page presents multiple choices, treat the preferred recovery-email row as a higher-priority state than any verification-code fallback. Before attempting the fallback, inspect the candidate row and its clickable ancestor for visible text, `aria-disabled`, `disabled`, and status text such as `Unavailable because of too many attempts` or `Please try again later`. A disabled row may still expose matching text and may intercept pointer events, so do not use a raw `locator.click()` as the first probe. Gate the fallback off whenever the preferred row or an unavailable status is present; then click the preferred row through its nearest clickable/role/`li` ancestor (or a controlled DOM-evaluate fallback), preserving the subsequent input-event and Next-button path. Add one offline mocked DOM check asserting: unavailable code row is not clicked, confirm-recovery row is clicked, recovery email is dispatched via `input`/`change`, and Next is clicked. Keep this check separate from live browser evidence.

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

## Byte-budgeted condensation of targeted candidates

When a closeout gate imposes a raw byte ceiling on a small allowlist, treat byte reduction as an implementation constraint, not a formatting afterthought:

1. Snapshot each target's content and `git diff`/untracked status before editing. For untracked files, the candidate is effectively the full file from `/dev/null`; measure that explicitly rather than relying on ordinary `git diff`.
2. Preserve a recoverable copy outside the repository before any bulk rewrite. Never run an aggressive AST/unparse/minifier pass directly on the only working copy: it can change semantics, destroy review context, or silently produce invalid syntax.
3. Prefer safe, local reductions in this order: remove redundant prose/comments/docstrings, delete unused imports, collapse harmless blank lines, shorten repeated boilerplate, then remeasure. Do not join lines or strip whitespace across bracketed expressions unless a parser/compile check follows immediately.
4. After every condensation batch, run `py_compile` before attempting further reduction. If it fails, restore the last known-good copy immediately; do not continue transformations on corrupted source.
5. Keep test function names and assertions intact. Do not reduce the byte count by deleting coverage, weakening assertions, or changing fixture semantics.
6. Recompute the exact gate payload after the final edit and run focused tests, compile checks, and scoped `git diff --check` against those final bytes. Report measured raw bytes, not an estimate.

A failed bulk-compaction attempt is not evidence of a working workflow. Record only the validated recovery pattern: preserve a backup, make one bounded edit, compile, test, and remeasure.

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

## Deterministic fake-clock tests and repeated-failure stop rule

For safety-margin, lease, timeout, or ownership tests that use a call-count fake
clock, do not tune the threshold by blind repeated retries. First trace every
clock read across setup, renewal, pre-publication checks, and release; registry
operations often consume more reads than the helper itself.

1. Prefer an explicit clock sequence, or advance a mutable time value at named
   phases, over a magic `call_count >= N` threshold.
2. If a call-count clock is unavoidable, document the expected phases and assert
   the call count so future implementation changes fail clearly.
3. Make the injected time satisfy both assertions: it must violate the
   pre-replace safety margin while remaining before lease expiry, allowing
   cleanup to return `RELEASED` rather than `LEASE_EXPIRED`.
4. When the defect is test timing rather than production behavior, change only
   the fixture timing control; preserve production semantics and safety checks.
5. After two identical threshold failures, stop retrying. Trace the full call
   sequence and redesign the fixture. Never claim verification from a partial
   or still-failing run.

Also beware of monkeypatching `os.replace`: lease renewal may use the same
primitive, so a replacement-call list can include registry publication as well
as the target write. Assert at the correct boundary or distinguish the paths.

## Bounded closeout-gate failure triage (read-only)

When a closeout/review gate reports a focused-test failure, progress-dot
position, or apparent hang, do not jump to a broad suite or edit the tree.
Perform a bounded diagnostic that produces fresh, name-level evidence:

1. Snapshot `git status --short --untracked-files=all`, `git diff --name-status`,
   `git diff --cached --name-status`, `git rev-parse HEAD`, and the exact
   `base..HEAD` diff. Explain candidate membership separately from current
   worktree dirt: a file clean in the worktree may still belong to a
   `HEAD~1..HEAD` candidate, while an untracked file is absent from normal
   `git diff` unless explicitly included.
2. Run `pytest --collect-only -q <suspected-file>` to map progress/failure
   positions to actual node IDs. Then run only that file with `-vv -s --tb=short`
   through a parent process that streams each line and kills the child at a
   hard wall-clock bound (normally 120 seconds). Record the last printed node,
   exit code, timeout flag, and elapsed time. This identifies both the test
   after the visible failure and the node where execution stopped, instead of
   guessing from dot counts.
3. If the suspected file passes, run the other directly changed test/module
   files one at a time with the same bounded verbose diagnostic. Keep these
   runs focused; do not substitute a full-repository run for closeout evidence.
4. Classify the result: a reproducible assertion/collection/interface failure
   on current bytes is structural; a prior failure/hang followed by a bounded
   current pass is transient or stale-gate evidence, not a production defect.
   Preserve the original warning/traceback if available, but do not invent a
   root cause from a dot pattern alone.
5. Give the smallest next action: rerun the gate against the stable current
   candidate when focused diagnostics pass; inspect the exact emitted gate
   command/payload when the gate still reports obsolete output; patch only
   when a current focused node reproduces a concrete structural defect.

A reusable session-specific transcript and the six-path candidate-vs-current-
worktree explanation are in `references/bounded-closeout-triage.md`.

## Windows text-file line-ending preservation

When editing an existing Windows Python/YAML file, preserve its current EOL style unless the task explicitly authorizes normalization. A targeted patch can silently rewrite a CRLF test file to mixed or LF/CRLF content; then `git diff --check` reports every added line as trailing whitespace even though the source is syntactically valid. After any patch to a CRLF file:

1. Re-read the edited file and inspect its bytes/EOL style.
2. If the patch introduced unintended mixed EOLs, normalize the file back to its original consistent style in one scoped operation.
3. Re-run the focused test and scoped `git diff --check`; do not report completion from a pass that predates the EOL repair.
4. Keep this distinct from unrelated pre-existing whitespace in out-of-scope files.

This is especially important for focused regression tests added to Windows repositories: a RED test proves the assertion is live, but final evidence also requires a clean scoped diff.

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
4. If a test fixture schema changes or production validation is tightened (e.g. strict rubric breakdown, required metadata, approval flags):
   - Update the mock fixture factories/producers (e.g. `_review()`, synthetic payload builders) and inline literals in the focused test file in the SAME turn or BEFORE re-running tests.
   - Do NOT weaken the tightened production validator to accommodate stale, minimal test fixtures.
   - Batch the fixture updates with the production validator change so contract tests don't fail midway due to schema mismatch when iteration limits or review gates run.

## Exact-allowlist implementation dispatches

For delegated implementation tasks that provide an explicit path allowlist, a small call budget, and a fail-fast stop condition:

1. Treat the contract as the source of truth. Do not browse unrelated repository files or redesign the requested interface; inspect only the minimum registry convention needed to make the new module importable.
2. In the first few calls, write the allowlisted production file and focused mocked test file, then apply the one specified integration edit. If the exact scope cannot be completed within the contract's initial budget, stop and report the blocker rather than expanding exploration.
3. Preserve unrelated dirty changes. Verify the exact path set with scoped status output; do not use broad cleanup, reset, staging, or whole-repository edits.
4. When a token appears in multiple registry/toolset lists, use a unique anchor for the intended list (for example, the list declaration and nearby category comments) so a replacement changes exactly one occurrence. Re-read the edited region after patching; a successful patch call is not proof that the intended occurrence changed.
5. Run the requested focused mocked tests and static check after the final edit, not only before a later integration patch. Report the real test count, warnings, exit status, and the exact changed paths. Keep mocked/offline evidence distinct from live-network or production evidence.
6. **Guard-rail and budget discipline on monolith exploration:** When given a tight tool budget (e.g. <= 15 calls) and a task on a monolith file, DO NOT burn turns on broad exploration tools that can hit root-search guard blocks (e.g. `search_files` on protected roots) or foreground terminal commands without required timeouts. Instead, execute targeted terminal greps with explicit timeouts or direct `read_file` offset reads, apply the `patch` immediately, run verification, and avoid exploratory churn that exhausts the budget before applying changes.

## Live GPM/ChatGPT-Web canary identity gate

For a single-profile browser recovery canary, bind the authentication method from the exact workbook row before launch. A populated `PASS CHATGPT` field means the driver should use Direct Email + Password unless an explicit artifact proves another method; never infer Google SSO from the email domain or an old summary. If the production watchdog has no single-target CLI, do not run the whole-pool entrypoint as a canary—use a dedicated one-account driver.

A live PASS requires fresh same-profile screenshot/OCR evidence, no login controls, visible account identity, and same-account provider/token validation. Exit code 0, GPM stop success, `isActive=true`, or `COMPLETED_UNCONFIRMED` alone is not proof. OCR showing `Sign in with Google`, `Email or phone`, or `to continue to OpenAI` means auth-flow mismatch/UNPROVEN, not a bad password. Fix the driver to submit OpenAI email then workbook password; never enter the OpenAI password into Google. See `farm-alert-autonomous-recovery/references/gpm-chatgpt-auth-method-and-canary-evidence.md`.

**Checkpoint artifact truth (mandatory):** Never claim that a pre-fill, post-fill, or post-submit screenshot exists until the exact path has been checked on disk and its size/mtime are fresh for the current run. A driver patch that adds screenshot calls is not evidence until the driver is rerun. For a multi-step login canary, require and report distinct artifacts in order: (1) landing screen before input, (2) email visibly filled before submit, (3) immediate post-submit screen/URL, (4) password visibly filled before submit, and (5) final result/error. If any checkpoint is missing, label the canary `UNPROVEN`/`BLOCKED`, send only the artifacts that actually exist, and do not infer that a redirect occurred from a later error screenshot or a timeout traceback. The user must be able to inspect the exact evidence image for each claimed UI step.

## Final-edit verification budget

Reserve enough execution budget for the post-edit verification phase before making the final patch. A RED test run before the production edit is useful evidence, but it does not verify the final bytes. After the last source change, always perform the final sequence as one bounded closeout block: re-read/re-stat the allowlisted files, run the exact focused pytest command, run `py_compile`, run scoped `git diff --check`, and inspect the final scoped diff/status. If the tool-call budget is nearly exhausted, stop optional exploration and prioritize this final block. Do not report completion when the final block was skipped; report the exact pre-fix RED result and that post-fix verification remains outstanding.

## Real media canary gate for dubbing/render pipelines

For video dubbing, TTS, subtitle, renderer, or media-pipeline work, a standalone audio/model probe is only a backend smoke test—not an integrated canary. The canary must run one real, representative source video through the actual repository CLI/pipeline and produce a fresh output artifact.

Required evidence sequence:

1. Confirm the exact source video exists and record its native Windows path, size, and media metadata. Do not infer existence from a stale filename or a worker summary.
2. Run the repository's real single-video command, not a mocked unit test or an isolated TTS script. Keep the source, output, config, backend, and run ID explicit.
3. Verify the output artifact exists, is fresh for the current run, has non-trivial size, and contains both video and audio streams with `ffprobe`. Exit code 0 alone is insufficient.
4. For A/B backend work, render the same source with the baseline and candidate backend; hold input, transcript/translation, subtitles, and timing constant. Do not call the candidate integrated or claim Canary PASS until the candidate video itself is verified.
5. Listen/watch the resulting artifact. For expressive dubbing, explicitly assess speech intelligibility, emotion cue realization, speaker-role separation, timing/overlap, background ducking, and subtitle alignment. Report artifact paths and limitations.
6. Classify failures accurately: source-path/launcher failure, provider/model failure, pipeline code failure, render/ffprobe failure, or quality failure. Do not label a path-format or missing-input failure as a model regression.

**Windows/MSYS path rule:** when the shell is Git Bash/MSYS but the application is native Windows Python, pass source and output paths as native drive paths (`D:/...` or `D:\\...`) to Python. Do not assume `/d/...` is accepted by `Path` inside the Windows interpreter. Validate the native path with a small read-only existence check before launching a long canary. The shell may still use `/d/...` for `cd`; application arguments should use the path syntax the application actually resolves.

A reusable dubbing-specific checklist and evidence table belongs in `references/real-media-canary-dubbing.md`.

## Ambiguous subprocess outcomes and remote-command closeout

For workflows that reserve a durable ledger slot before launching a subprocess, treat every post-launch non-success as an ambiguous side-effect outcome. A nonzero exit, timeout, decode error, missing/invalid report, or report mismatch may occur after the external action already happened. Keep the launched reservation fail-closed; only release it for a proven pre-launch/spawn failure. Add a regression test that performs a second invocation and asserts the ledger blocks duplicate work.

For remote-admin branches, add an offline mocked subprocess regression that asserts the exact argv shape and remote command string, including serial, video number, workbook, config, and source-root. Seed `ADB_SERVER_SOCKET` in the parent environment and assert the child `env` explicitly omits it. Keep a separate local-controller assertion so remote routing changes do not silently alter local behavior.

When adding direct helper coverage, call the existing helper rather than reproducing its policy in a test fixture. Cover no-state, inclusive date/streak boundaries, corrupt state (fail-closed), and precedence when row-level and machine-level state coexist. If a broader test exposes stale state from a previous case, reset both precedence sources before boundary assertions; state precedence is itself part of the contract.

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
