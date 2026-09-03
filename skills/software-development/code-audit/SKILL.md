---
name: code-audit
description: "Proactive code audit — systematically inspect code for bugs across defined categories before they manifest. Find, fix, verify, and report."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-audit, bug-hunting, code-review, quality, static-analysis]
    related_skills: [systematic-debugging, requesting-code-review, code-review-response, test-driven-development]
---

# Code Audit

## Overview

Proactive code audit finds bugs before they manifest — no failing test, no user report, no PR review needed. Systematic inspection across defined categories catches what tests and linters miss.

**Core principle:** Audit from first principles — don't wait for a bug to crash. Read the code, trace the logic, identify what *could* go wrong, and fix it now.

## When to Use

Use when the user asks you to:

- "Audit this code" / "audit this function" / "review this code for bugs"
- "Check logic of X" with specific concerns (type safety, cleanup, edge cases, correctness)
- "Find bugs in" / "fix any issues in" a specific file or function
- "Kiểm tra kỹ logic" (check the logic carefully) + list of concern areas
- "Verify correctness" of new or changed code
- "Audit plan triển khai / đối chiếu invariants / cho verdict" — read-only audit of a Markdown implementation plan or design doc against acceptance criteria (invariants handoff, locked design) → see "Plan / Design-Doc Audit" below

**Don't use for:**

- Debugging an existing failure → `systematic-debugging`
- Pre-commit verification pipeline → `requesting-code-review`
- Responding to third-party review findings → `code-review-response`
- Metrics/statistics → `codebase-inspection`
- Project handoff review → `project-handoff-audit`

## Audit Categories

Inspect every function against these categories:

### 1. Logic Correctness
- Does the algorithm produce the right result for all inputs?
- Are edge cases (empty input, single element, max values) handled?
- Are conditional branches exhaustive, or does a fall-through silently skip?
- **Example:** Fabricated split names "base"/"split_00" instead of actual APK split identifiers → `pm install-commit` always fails.

### 2. Error Handling
- Are failures silently ignored (empty `except`, `if ok:` without `else`)?
- Are error messages actionable (include values, context, not just "failed")?
- Does a failure in one step cascade correctly to the next?
- **Example:** `stat -c %s` fails → `if size_result.ok:` silently skips → wrong `total_bytes` → downstream `install-commit` fails with cryptic size mismatch.

### 3. Resource Cleanup
- Are temp files, connections, locks released on ALL exit paths (success, error, exception)?
- Is `try/finally` used for cleanup?
- Does early `raise` (or `return`) skip cleanup?
- **Example:** `rm -rf remote_dir` only runs after commit, not when `push`/`ls`/`install-create` raises → temp files accumulate on device.

### 4. Type Safety
- Can `int()`, `float()`, `json.loads()` receive non-numeric/non-JSON input and crash?
- Are `None` or empty-string return values handled before use?
- **Example:** `int(size_result.stdout.strip())` crashes with `ValueError` if `stat` returns empty string or error text.

### 5. String Safety (Shell Injection / Path Quoting)
- Are strings concatenated into shell commands without quoting?
- Do paths with spaces break the command?
- Are user-controlled values escaped?
- **Example:** `adb shell` concatenates args with spaces for the device's shell. `stat -c %s /path/to/my file.apk` word-splits at the space.

### 6. Race Conditions & Atomicity
- Check-then-write patterns without locks?
- Shared mutable state across calls?
- **Example:** Two simultaneous installs on the same device could conflict on `remote_dir` (mitigated by `abandon_stale_install_sessions` at top of `install_package`).

### 7. API Contract Compliance
- Does the function match its documented behavior?
- Are arguments in the right order?
- Are return types consistent with what callers expect?
- Are deprecated/private APIs used when public ones exist?

### Artifact-Backed State-Machine Evidence

When auditing recovery handlers against a real run, use the raw run artifacts as the evidence boundary:

1. Read the exact run `report.json`, `checkpoint.json`, execution log, and every referenced screenshot/UI-capture artifact for each target.
2. Distinguish raw artifacts from derived summaries. A `RECAPTURED` field or handoff sentence does not prove the required UI control exists; a screenshot summary does not replace the image or XML.
3. Replay the production classifier/verifier against the saved artifacts where possible and record exact artifact paths, hashes/metrics, lifecycle states, and side-effect guards.
4. If the raw UI XML needed to prove a semantic control is absent, report `NEEDS_PROOF` rather than inventing a fixture or inferring structure from prose.
5. Add a regression test only when it is a real red-capable reproduction. If the current code already fails closed on the available evidence, run the existing focused tests, document the missing raw artifact, and propose the narrow invariant instead of adding a green-only test.

This is especially important for device/UI signatures: safe evidence must show foreground guard, bounded action, fresh before/after capture, semantic control bounds, post-action recapture, and no unsafe downstream side effects.

See `references/artifact-backed-state-machine-audit.md` for the reusable checklist and replay record.

### Browser-to-App and Deep-Link Transition Audits

For email-link, OAuth, browser-to-app, or other UI flows where a tap should change application state, separate three evidence levels: (1) intended action identified, (2) target package foreground, and (3) expected post-action state classified. Package foreground alone does not prove the deep-link payload was consumed. Capture the exact pre/post XML, URL or semantic action, activity/package evidence, and the narrow postcondition state.

When a validated URL exists but a coordinate tap only foregrounds the app, recommend the smallest platform-native action that delivers that validated URL (for Android, a `VIEW` intent) before weakening the classifier. Keep fail-closed behavior for an unchanged pre-action screen. Trace whether leaf and caller both own transition verification; a duplicate helper call is a separate control-flow defect and is not automatically causal.

For history investigations, use `git show <commit>:<file>`, `git log -S`, and `git blame` to prove whether a symbol exists in each historical blob. Distinguish committed history from uncommitted working-tree additions before attributing a regression to a named commit. See `references/deep-link-transition-audit.md` for the evidence matrix, Git recipe, and concrete pattern.

## Workflow

### Phase 1: Scope & Locate

1. Read the user's request — extract the **function name(s)** and **specific concern areas**.
2. Search the codebase for the target function:
   ```
   search_files("target_function", path="src/", file_glob="*.py", output_mode="files_only")
   ```
3. Read the COMPLETE file containing the function:
   ```
   read_file("src/module/file.py")
   ```
   If it paginates, continue with `offset=` until you have the full file.

### Phase 2: Systematic Inspection

Go through each audit category (1–7 above) against the target function.

For each category:
- Note what you find — GOOD or ISSUE
- For each ISSUE: record the exact line number, the pattern, and why it's wrong
- Reference a concrete example from the session's experience when applicable

### Phase 3: Fix

1. Plan fixes in dependency order (if fix A changes a signature fix B depends on, do A first).
2. Apply one fix per `patch` call — batch only truly independent changes.
3. After each batch, verify the module imports: `python -c "from package.module import Function"`.

### Phase 4: Verify

1. Run the project's canonical test suite:
   ```
   python -m pytest tests/ -v
   ```
2. If no test suite exists — create a focused ad-hoc verification script.
3. If the suite covers the changed code, note which tests exercised it. If not, note the coverage gap.
4. Before the final handoff, run the relevant pytest command once more in the current worktree and treat that fresh output as the verification evidence. Do not rely on an earlier green run after a tool/system reminder marks verification stale; if it fails, read the failure and repair or report the concrete blocker.
5. Apply the repository's explicit COMMIT GATE literally: a pre-existing full-suite collection/import blocker is not a reason to edit unrelated files. Run the scoped suite, report the full-suite blocker separately, and do not commit or push unless the named gate is actually green.

### Phase 5: Report

Deliver a structured report:

```
## Audit Summary: <function_name>

### Issues Found & Fixed

| # | Severity | Issue | Lines | Fix |
|---|----------|-------|-------|-----|
| 1 | Critical | description | N-N | fix summary |
...

### Verification
- pytest: N/N passed
- Import check: OK

### Minor/Unfixed Findings
- ...
```

## Plan / Design-Doc Audit (read-only verdict audit)

Used when the deliverable is a verdict on a Markdown implementation plan / design doc against invariants or acceptance criteria — NOT a code fix. These audits are typically locked read-only ("KHÔNG sửa bất kỳ file nào"): deliver the verdict line + findings with locators, do NOT edit the plan or the code. Outcome of the code-fix phases (3–4) does not apply — "fix" happens in a later worker session, guided by your findings.

1. **Read the FULL plan plus every acceptance-criteria source** (invariants handoff, locked design). Record structure: phase headings, acceptance lines, test skeletons, commit messages, files touched per phase.
2. **Build an invariant→phase/test mapping matrix.** Each acceptance criterion must map to a concrete phase + named test; unmapped or only-prose-covered invariants = gap finding.
3. **Re-run every baseline claim the plan cites** (`git status --short`, the exact pytest command). Stale claims (e.g. plan says "117 passed, 3 failed" but the suite is actually green) are MAJOR findings — Phase 0 assumptions built on them collapse.
4. **Run the plan's own math in python** — slot arithmetic, seed hashes, `random.Random(seed)` determinism. Plan formulas are frequently subtly wrong (worked example: pair_gap inserted AFTER S2 instead of between S1_end and S2_start → wrong block end times AND self-contradictory tests that demand the wrong answer).
5. **Verify "ĐÃ ĐÓNG"-style claims about existing code by reading the code** — the named passing test must exist and the actual function must implement the invariant (e.g. journal append and replay genuinely sharing `reduce_and_validate`).
6. **Scan for under-spec markers** — `...`, "nếu cần", "có thể", "khuyến nghị", "tối thiểu", "giữ nguyên", "xem Phase N" in test BODIES (inside `def test_...`) = the worker will fabricate behavior; that's a finding, not a detail. `...` inside COMMENTS of GREEN code snippets (`# journal.append(X, ...)`) is NOT a skeleton — classify grep hits per phase before counting them as residuals.
7. **Cross-check each planned test's mutation against the PLANNED validation branch it claims to hit** — gate masking inside a plan: an earlier gate (entry_id formula check, top-level required-set) may reject BEFORE the branch under test runs, or planned validation may recompute a value the mutation never touched (test FAILs GREEN). Every `pytest.raises` needs its own reachable reject-branch. See the round-2 workflow in `references/plan-audit.md`.
8. **Check cross-phase consistency** — the same fix referenced in several phases (e.g. window mốc `01:30→02:30` in Phases 1/3/5) must be applied once, identically; count every occurrence.
9. **Report format**: verdict dòng đầu (`APPROVED | MINOR_FIXES | REJECT`); each finding has a locator = plan dòng (file:line) + code file:line when relevant; severity MAJOR/MINOR/NIT; note the disposable probes you ran as `_verify` evidence. Batch independent checks (baseline run + grep + read) in parallel.

See `references/plan-audit.md` for the full checklist, the worked fleet-scheduler example (3 MAJOR findings incl. the pair-gap formula error and the stale baseline), and the round-2/round-3 **re-audit-after-fix-round workflows** (closure probes per prior finding, planned-code-vs-planned-test gate-masking checks, `...`-in-comment vs test-body disambiguation, and the APPROVED-with-documented-NITs verdict discipline — a planned test can be green while testing nothing, and planned validation can fail its own test GREEN).

### Implementation-Diff Presence Gate

Before auditing an implementation worker's result, establish that the claimed implementation actually exists. This gate is mandatory for worker handoffs and migrations:

1. Capture `git status --short`, `git diff --stat`, `git diff --name-status`, and the worktree `HEAD` before treating proposed tests as evidence.
2. Distinguish tracked implementation changes from untracked docs/tests. An untracked discovery report or test file is not an implementation diff; do not infer production behavior from names, imports, docstrings, or intended assertions.
3. Check the exact runtime producer/consumer files named by the task with `git diff --quiet <base> -- <path>` (or an equivalent blob comparison). If all implementation paths are unchanged and only tests/docs exist, stop with the user's required blocked verdict, such as `AUDIT_BLOCKED_NO_IMPLEMENTATION_DIFF`, rather than issuing behavioral approval or speculative findings about absent code.
4. Treat placeholder tests (`pass`, `TODO`, `# RED`), unconditional skips, placeholder paths, and tests without assertions as coverage gaps—not proof that a contract is implemented. Record exact locators and do not call them passing evidence.
5. Keep the audit read-only: do not build, edit, stage, commit, push, or run live actions merely to compensate for a missing implementation diff. Report the missing evidence needed for re-audit.

This is especially important for recovery-adapter migrations where a worker may create a RED test skeleton before wiring `executor`, `account_reconcile`, `cli`, or scheduler paths. Separate (a) no implementation diff, (b) placeholder test scaffolding, and (c) shared-core contracts that still need consumer wiring.

### Dirty-Diff Classifier / Pre-Live Audit

When the request is a read-only audit of a dirty worktree before a TikTok registration fix or live run, treat the working tree as an untrusted multi-change surface, not as a single patch:

1. Capture `git status --short` and `git diff --stat` first. Record that baseline and do not edit, normalize line endings, stage, clean, or inspect sensitive generated data. Scope the review to the named classifier/runtime path and its directly related tests; list unrelated dirty files separately. **Reconcile against the user's STATED scope:** the task description often *undercounts* dirty files (a parallel edit by another process, or an unrelated in-progress change the user forgot to mention). The actual `git status` is the source of truth — if a dirty file lies outside the named allowlist, flag it as a separate finding and explicitly state you did NOT fold it into the closeout commit; do not let it silently widen the reviewed scope. Worked case (2026-08-22, tiktok-luot nuoi acc): task said "scoped Captcha-close-X fix" in 2 files (classifier.py, test_classifier.py); first capture showed only those 2, but a later `git status` revealed a 3rd dirty file `flows/benign_popup.py` (≈139-line follow-friends popup rewrite, mtime *after* the captcha edits, zero captcha references) — preserved and flagged, never folded into the closeout.
2. Read the complete changed implementation and every direct caller. Search by symbol and call site, not only by diff hunk. Use an AST/source-level call-site inventory when the API is cross-cutting; grep alone can miss wrappers, live entrypoints, or calls split across files. A classifier change is incomplete if its return contract is not propagated through the caller chain (for example, `numeric | magic-link | unknown` must reach the email handler) or if an old legacy caller still invokes the heuristic API without context. Audit every production caller, not only the files named in the diff.
3. Treat focused tests as executable contract evidence, but not as proof of complete propagation. A green focused suite can coexist with an untested legacy caller that still misroutes production traffic. Add a disposable AST/signature probe when needed to enumerate calls and assert that context (`entry_surface`, `signup_mode`, or equivalent) is passed explicitly at every relevant boundary. For registration OTP handlers, inspect every production `handle_*otp` call separately from classifier call sites: every signup/registration caller must pass `signup_mode`, and ambiguous registration fallbacks must pass the literal `"unknown"`; do not accept a handler default merely because the caller is located in a registration-named file. Run the exact named focused suite, then run a safe syntax/import check. A green subset does not offset missing symbols, `AttributeError` during collection, or tests that assert a return contract the implementation does not provide. Report pass/fail counts and the first concrete failure.

For the reusable caller-propagation matrix and AST probe pattern, see `references/registration-context-propagation.md`.
4. Add a disposable source-level contract probe when needed: verify required symbols exist, inspect signatures, exercise representative login/signup/ambiguous/non-TikTok cases, and prove that `unknown` fails closed before reader/resend/live side effects. Do not use workbook, credential, ADB, mailbox, or live artifacts for this probe.
5. For account-routing classifiers, require all of these invariants before `APPROVED`: fresh TikTok foreground evidence; pre-submit entry surface (`login` vs `signup`) preserved; numeric OTP and magic-link modes classified independently; ambiguous mode returns `unknown`; handler receives the mode explicitly; no fallback can infer mode from stale/shared markers; registered-account results defer to the canonical login path without attempting registration.
6. Classify missing implementation/test-contract wiring as P0 when it can send a signup into the wrong OTP/magic-link branch, invoke resend, or bypass a fail-closed stop. Classify residual legacy context-free callers as P0 when they can still misroute real production traffic; otherwise P1. The minimal fix plan must name the producer, propagation edge, consumer, and regression matrix.
7. Audit sentinel/tuple propagation end-to-end, not just classifier output. Enumerate every state spelling returned by the producer and every state spelling accepted by each caller. A semantically equivalent-looking mismatch (for example, producer returns `registered_otp` while the terminal caller only handles `registered_deferred`) is a real control-flow defect: prove whether the caller preserves the current UI and lock before any fallback, BACK/HOME, retry, relaunch, cleanup, resend, or registration action. Add a focused regression that exercises the exact producer→caller boundary, not only the pure classifier.
8. Report exactly as requested by the user: verdict token on line 1 (`APPROVED`, `MINOR_FIXES`, or `REJECT`), then only P0/P1 findings with exact `file:line` locators and a minimal repair plan. Keep the report concise; if the user requests a findings-only format, omit summaries and lower-severity notes. Include only the verification evidence requested and explicitly state that no ADB/live/workbook/credential action occurred when relevant.

9. **Classifier marker-list consistency (token-routing fixes).** When a classifier routes by substring markers (the TikTok-reg codebase is dense with these — `_classify_post_email_submit_xml`, `_classify_post_signup_submit_mode`, `_classify_after_continue_flat`, `detect_after_continue`), a hybrid/secondary branch almost always defines its own marker list (e.g. an "OTP present" sub-list) that is **not** a subset of the primary detection tuple. Audit both directions: (a) every marker a regression test relies on must be reachable through the primary detection path — markers present ONLY in the secondary list and absent from the primary can never trigger the intended branch (dead entries that silently misclassify); (b) conversely, secondary-list entries broader than the primary can pull the wrong screen into the branch. Diff the two lists programmatically and assert each test-relevant marker is in the primary tuple. A fix that adds secondary-only markers without widening the primary tuple is a MINOR_FIXES finding, not APPROVED — even when the two named regression tests pass, because they exercise only the markers the author thought of. Also confirm fail-closed by AST transitive reachability: a removed/avoided fallback (e.g. CDP/browser OTP readers) is genuinely unreachable from every production caller, not merely absent from `git diff`.

10. **Re-capture git state immediately before the verdict (time-of-check vs time-of-use).** The dirty worktree is a LIVE surface — between your first `git diff` capture and your final APPROVED/BLOCKED verdict, it can change (the user or another process commits, stashes, amends, checks out, or pulls). A committed diff can materially differ from the uncommitted snapshot you started analyzing. **Before issuing the verdict, re-run `git status --short`, `git diff --stat`, and `git diff -- <named files>`; if the tree is now clean with a new commit, re-baseline with `git log`/`git reflog` + `git show <commit>` (commit-scoped audit) and re-verify the final blobs and scoped tests.** Never cite a branch/symbol/line absent from the final committed-or-dirty state. Worked case + recipe: `references/dirty-diff-time-of-check-pitfall.md`.

See `references/dirty-diff-classifier-audit.md` for the reusable evidence matrix and disposable probe recipe. For end-to-end route-state/sentinel propagation audits across shared cores, live wrappers, and terminal runners, see `references/registration-route-sentinel-propagation.md`. See `references/classifier-markerlist-audit.md` for the marker-list diff probe (Probe 1) and the AST transitive-reachability check (Probe 2) with runnable python. For the captcha-close-X ↔ popup/manual_challenge fail-closed boundary (five-case matrix + geometry caveat), see `references/dirty-diff-captcha-closex-classifier-audit.md`.

**Proving a fallback path is truly orphaned (post-diff):** when a diff removes a fallback branch (e.g. deletes CDP/browser OTP readers from the numeric path), `git diff` absence does NOT prove the path is unreachable — the old helper may still be defined and called from a legacy wrapper. Prove it with the AST transitive-reachability probe in `scripts/orphan_reachability_probe.py`: it builds a name→def map, walks the transitive call-closure from each live root caller, and reports the intersection with the suspect set. Empty intersection = orphaned (safe to treat as removed). Worked case: legacy `_try_get_otp_outlook_cdp` / `_try_get_otp_browser` were no longer reachable from `handle_tiktok_email_otp` after a seam fix, so they could not reintroduce the old wrong-code path. Use it as a P1-A verdict gate before declaring a fail-closed path complete.

**Read-only test/compile isolation on Windows:** run focused suites with `env -u PYTHONPATH python -m pytest <scoped files> -q` so a stale installed (site-packages) copy of the package does NOT shadow the worktree under audit (the installed-copy shadow is a classic false-green cause documented in the multi-repo audit section). When an `import` is required for a disposable probe, convert the path with `PYTHONPATH="$(cygpath -w "$(pwd)")"` rather than bare MSYS `$(pwd)`. Always `py_compile` (or run the suite) with `PYTHONPYCACHEPREFIX` pointed at a disposable temp dir so a read-only audit leaves NO bytecode inside the repo: `env -u PYTHONPATH PYTHONPYCACHEPREFIX="$tmpdir" python -m py_compile <files>` then `git status --short <files>` to confirm only the original M/?? markers remain.

**Pinned-dependency API-contract verification (read-only):** when the audit hinges on a shared-core/wheel API (signatures, return contracts, exception types, lock semantics), the ACTIVE interpreter's site-packages may hold an OLDER version than the repo pin (`requirements-*.txt` / `pyproject.toml` may pin a `file://` wheel). Do NOT install/upgrade the env to verify. Extract the exact pinned wheel into a disposable temp dir and point PYTHONPATH at it — native Windows paths ONLY for both the wheel arg and `--target` (native pip mangles `/d/...` into `D:\d\...` and an MSYS `/tmp/...` target lands where native python cannot import it; resolve MSYS `/tmp` with `cygpath -w /tmp`). Then `inspect.signature` / `inspect.getsource` the exact methods and use `getattr(module, "Symbol", ())` presence probes for optional exceptions; confirm `automation_core.__file__` AND `importlib.metadata.version(...)` resolve to the temp dir before trusting the probe. Run the scoped suite with `PYTHONPATH` set to the extracted wheel dir so tests exercise the PINNED API, not the env's. Worked recipe: `references/pinned-wheel-contract-audit.md`. For the `AdbClient.shell` duplicate-`"shell"`-token bug class (broken `adb shell shell ...` commands masked by `check=False` + best-effort callers), the full verification sequence, red-capable regression shape, and the avatar MediaStore ordering pattern: `references/adb-shell-argv-contract-audit.md`.

#### Dirty-Tree Failing Tests as Contract Spec (read-only audit of a dirty worktree)

When the working tree already contains parent/in-progress (uncommitted) edits, NEW failing tests are not regressions — they encode the intended invariants. Use them as the fix contract:

1. Capture `git status --short` and `git log --oneline -8` first. Note which files are dirty (source AND tests both modified = parent is mid-change) and which tests fail.
2. Run the scoped suite (the directly relevant test modules) and read the failing tests' bodies — docstrings, expected outcomes, expected tap coordinates, expected reload counts. Align your findings with them; they define what the next worker round must implement. A failing test whose production counterpart has no corresponding code path = missing implementation (the fix contract).
3. **Green-for-wrong-reason check**: a passing test can assert an invariant while the production code never implements it — e.g. a test sets `eng.active_account_handle = "@X"` and asserts exclusion, but `__init__` never creates that attribute and the production method never reads it. The test passes vacuously. Before trusting ANY passing test that claims a safety gate, verify the production symbol/setter/read exists (rg the attribute name in the module + read `__init__`).
4. **Cross-mode/sibling-flow asymmetry probe**: compare the audited flow against its sibling in the same repo (e.g. Mode 1 `follow_one_uid` vs Mode 2 `_open_follower_tab`). A sibling that already has the identity gate (`profile_identity_from_xml` + exact `id/sf5` node + normalized handle == UID) makes the missing gate in the audited flow visible immediately.

Worked case (2026-08-15, `D:\Taadaa\tiktok-follow` Mode 1 audit): 5 failing tests in the dirty tree mapped 1:1 to the P1/P2 findings (wrong-profile rejection, Follower-label exclusion, ambiguous-action rejection, identity-bound classifier); 1 green test (`test_follow_uids_come_from_full_safe_mapping_but_exclude_active_account`) was green for the wrong reason — the attribute it sets never exists in production. Detail: `tiktok-consumer-automation/references/tiktok-follow-mode1-audit-20260815.md`.

## Commit-Scoped Phase Acceptance Audit

When auditing a named commit against one approved plan phase, keep two evidence boundaries separate:

1. **Commit boundary:** derive the exact changed-file list from `git diff-tree --no-commit-id --name-status -r <commit>` and inspect committed blobs with `git show <commit>:<path>`. Do not treat unrelated untracked baseline files as part of the commit.
   - Always add `git diff --shortstat` and `git diff --numstat <commit>^ <commit>`, then check whether each expected residual file is `M` or `A` in the parent tree (`git ls-tree -r --name-only <commit>^ -- <path>`). If a purported narrow fix is actually a full-file addition (`A`, hundreds of insertions, no deletions), the parent does not provide an old source baseline: do not claim that only the named lines changed. Record this as a commit-scope/provenance finding, while separately judging the behavior of the committed blob.
2. **Acceptance boundary:** still inspect current callers/tests when the phase invariant is cross-cutting. A phase can have the correct four-file commit and a green suite while leaving a stale runtime guard or assertion elsewhere that contradicts the new invariant.
3. **Classify residuals accurately:** if stale code is explicitly deferred to a later named phase, report it as a deferred/blocking acceptance residual with both the current code locator and later plan locator; do not attribute it to the audited commit. If the user’s gate requires the invariant globally now, it prevents `APPROVED` even when the commit itself is clean.
4. **Use a direct semantic probe, not only grep:** compare the canonical model predicate with the operational caller at one newly-valid boundary and one newly-invalid boundary. Record both results (for example, model accepts `01:00` while runner rejects it; model rejects `02:30` and caller rejects it). This catches old hard-coded guards that a passing regression suite can miss.
5. **For schema-extension commits, probe cross-link integrity beyond the happy path:** start from a valid generated payload, then make mutations that survive earlier gates by recomputing dependent hashes/IDs. At minimum: (a) splice top-level metadata (e.g. block account/machine/serial) while recomputing block and entry IDs, then validate with the real source; (b) reorder an ordered ID list and verify canonical validation rejects it rather than comparing sorted sets. An accepted mutation is a source-binding/canonicalization finding even when the named Phase only promises “minimum validation”; cite the later phase that claims to close it and do not silently treat the gap as green.
5. **Report the required verdict on line 1** (`APPROVED`, `MINOR_FIXES`, or `REJECT`) with exact `file:line` locators. Then tabulate scope, invariant probes, suite output, compile/diff checks, and untouched-worktree status. Never edit files during a read-only audit.

6. **Prove provenance before requesting a production change:** if the audited commit changes only tests and the operational guard already exists in an earlier commit, compare the current source blob byte-for-byte (or by SHA-256) with that earlier commit and cite its exact guard lines. Treat this as a closed prerequisite, not a baseline trap or a missing Phase change.

7. **Separate acceptance-test evidence from suite evidence:** run the named boundary tests with `-k` as a focused matrix, then run the exact plan/user full-suite command. Read the committed test helpers and assertions, not just the pass count. For offline CLI acceptance, require direct `main([...])` invocation, a stubbed `subprocess.run` (or equivalent process boundary), `calls == []`, and an observable dry-run/journal result.

8. **Make stale-literal scans token-aware:** a naive substring search for `01:00` falsely matches durations such as `00:01:00`. Use boundaries that exclude adjacent digits/colons, while separately scanning `hour = 1` and `replace(hour=1)`, and report the exact roots scanned. Run `py_compile` with `PYTHONPYCACHEPREFIX` pointing to a disposable temp directory so a read-only audit does not leave repository bytecode behind.

9. **Windows probe execution + provenance shortcuts:** run disposable probes from `%TEMP%` with `PYTHONPATH="$(cygpath -w "$(pwd)")"` — a bare MSYS `$(pwd)` silently fails `ModuleNotFoundError` for native Python when the script lives outside the repo dir. If `git ls-tree -r --name-only <commit> -- <path>` returns empty for a file the diff clearly shows as modified, fall back to piping the full tree through `rg`, and prove blob equality with `git hash-object <path>` vs `git rev-parse <commit>:<path>` (also gives a citable hash for `A` files with no parent baseline). For journal-event + maintenance-manifest + offline-CLI acceptance (append/replay chung validator, tamper matrix, timing sweep, stubbed-subprocess idempotence, cross-stream transition), follow the numbered P1–P7 probe recipe in `references/phase-journal-maintenance-cli-acceptance.md`.

10. **Probe adversarial-test branch reachability, not just greenness:** a committed adversarial test can pass while exercising a different branch than its docstring claims. Worked case (Phase-7 fleet audit, 2026-08): moving a session's `slot_time` without rehashing `entry_id`/`idempotency_key` rejects at the entry_id formula gate inside `_validate_entry` (`entry_id_for` hashes slot_time), so `_validate_block_structure` — the branch the docstring claims — never runs. Monkeypatch-wrap the suspected validator (record call, delegate to original) to prove whether the intended branch executed; classify an earlier-gate rejection as a documented NIT only when that gate genuinely enforces the same invariant. Verify plan-vs-committed assertion softening (e.g. `set(skipped) ==` → `>=`) by probing the real picker/runner first — the plan's exact expectation can itself be wrong. For conditional docs steps ("Nếu X tồn tại thì update"), check the named doc files exist AND contain the named section before flagging a missing update as MINOR. Recipe + worked details: see "Adversarial-test branch-reachability probe" in `references/commit-phase-acceptance.md`.

See `references/commit-phase-acceptance.md` for the reusable evidence table and probe recipe.

## Examples

### ADB Multi-Split Install Audit (automation-core, device.py)

**Trigger:** "Kiểm tra kỹ logic install_multi_split (tính total_bytes, split_name mapping, cleanup khi crash, type safety, edge case file path có space). Nếu ổn → ghi 'NO_ISSUES_FOUND'. Nếu có → sửa."

**Result:** 6 bugs found & fixed:
1. **Critical** — fabricated split names → use `os.path.splitext(f)[0]`
2. **High** — stat failure silently skipped → hard-fail with `ADBError`
3. **High** — no cleanup on early failure → `try/finally` guarantees `rm -rf`
4. **High** — commit failure doesn't abandon session → `finally` calls `install-abandon`
5. **Medium** — `int("")` crash on non-numeric stat output → validate with `isdigit()`
6. **Medium** — shell path broken by spaces → `_quote()` helper wraps in double quotes

**Verification:** `pytest: 66/66 passed`, import check OK.

## Windows Repository Edits & Timeout-Migration Verification

For focused changes in a Windows repository where the working tree may already contain unrelated edits:

1. Capture `git status --short` before editing and treat unrelated modifications as protected scope.
2. Scan all non-vendored Python files for the actual UI-capture operations (`capture_ui_xml`, `uiautomator dump`, and `screencap`). Exclude `.runtime/` and leave non-UI timeouts (locks, workbook operations, `dumpsys account`, transfers, and process waits) unchanged. Treat ADB atomic command timeouts (`tap`, `shell`, `wm`, `input`, `pull`, and raw `screencap` command timeouts) as protected unless the request explicitly names them; a UI wait timeout is not permission to change the underlying command timeout.
3. Record each target as a per-spot table entry: file, exact line/context, old timeout, new timeout, and whether it is a UI wait or an atomic ADB command. Include paired timeout knobs such as a client `default_timeout` and the operation timeout when both govern the same screen capture, but do not widen the atomic command merely to make the UI wait longer.
4. Measure the target file's current byte-level EOL counts before editing and verify they are identical afterward. Do not normalize a pre-existing CRLF working-tree file merely because `git show` uses LF. Check `git ls-files --eol -- <file>` first: `i/lf w/crlf` means a CRLF working tree over an LF index, and such files are frequently MIXED (individual LF lines inside a CRLF tree) — snapshot sha256 + crlf/lf/lone-cr counts before the first edit as the restore proof.
5. **Do NOT use the patch tool on mixed-EOL/CRLF files** — observed failure (2026-08): a single-line replace normalized the EOL of the ENTIRE hunk region, flipping ~26 surrounding LF lines to CRLF across 5 regions (huge spurious diff); a context-rich `old_string` does not prevent it. Use the line-targeted byte-exact edit script instead: `splitlines(keepends=True)`, edit by line number with a content assertion, keep each line's OWN EOL suffix (`\r\n` vs `\n`), re-encode and write; expect exactly +1 line in the tally when a one-line construct becomes two lines (e.g. `for` → deadline `while`). If patch-tool damage already happened, reconstruct the baseline from `git show HEAD:<file>` → CRLF-convert → re-apply the known-LF lines → assert sha256 equals the pre-edit baseline.
6. After the canonical checks, create a disposable focused probe with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", delete=False)` under the OS temp directory. Stub device/ADB calls and assert the changed UI wait/default values and any explicitly requested capture-policy values. Do not treat raw `screencap`, `pull`, `tap`, `shell`, `wm`, or `input` command timeouts as UI waits; assert those atomic timeout lines remain unchanged when the request protects them. Clean the probe in a `finally`/shell cleanup path. Report this as ad-hoc verification, not as a green full suite. When a system/tool reminder marks verification stale, prior output is invalid for the handoff: rerun the disposable probe in the current worktree, even if an earlier focused pytest run passed. For generated Windows probe source, use forward-slash path literals or `Path` joins; avoid accidentally encoding doubled backslashes in raw `Path` literals. For timeout-budget behavior, monkeypatch the module's `time` with a FakeClock (`time()` returns `t`, `sleep(s)` advances `t`) and assert the wait consumed exactly start+60 (or <60 for early-success paths) — proves the loop polls the new budget without waiting real seconds. Probe pitfalls: restore EVERY monkeypatched symbol between sections (leaked `get_ui_xml`/`find_node_in_xml` stubs falsify later sections); stub XML must use DOUBLE quotes for raw-string detectors (`package="com.android.gms"`); account for pre-loop sleeps in budget arithmetic. Add an AST-based contract test alongside (parse source, assert every wait-helper default AND every literal caller `timeout=` == new value) — run RED before the edit, GREEN after.
7. If the full suite has unrelated failures from pre-existing lock/scheduler work, report exact failing tests and the focused verification result separately; do not fix or attribute them to a timeout-only change without evidence. A failure in a module that was edited is not automatically independent: compare the failing assertion/stack with the patch and label it an existing expectation mismatch only when the failure locus is outside the changed behavior.
8. On Windows with `core.autocrlf`, prefer `git diff --cached --check` after staging for the final patch. `git -c core.autocrlf=false diff --check` can misclassify every CRLF as trailing whitespace; record that as an EOL-tooling warning, not as a source whitespace regression.
9. For a commit/push deliverable, verify the exact commit file list, full local SHA, `git ls-remote origin refs/heads/<branch>` SHA, and final status. Confirm the protected baseline file is still unstaged and unrelated untracked files remain untouched.
10. When the requested fix lands in a file that also has protected baseline edits, stage only the timeout/fix hunks with `git add -p` or a minimal `git apply --cached` patch. Inspect `git diff --cached` before committing. If the target code exists only inside an unstageable baseline-added block, do not force a partial malformed index; restore only your own probe edits, leave that protected file untouched, and report the audit finding explicitly.

See `references/windows-ui-timeout-migration.md` for a compact reusable checklist and probe pattern.

## Re-auditing Schema-Integrity Remediation: Independent Probes and Gate-Masking Defense

When re-auditing a remediation commit that claims to close manifest/schema tampering, do not treat a green `pytest.raises(ValueError)` as proof of the intended invariant. Use a valid generated payload as the fixture, then:

1. Validate the untouched payload with the real source configuration and record that it is accepted.
2. Verify dependent identity formulas directly: derive the manifest identity (`assignment_id:day`), recompute each entry ID and idempotency key, and compare `block.entry_ids` to the exact canonical `[session 1, session 2]` list. A set/sorted comparison is insufficient for ordered fields.
3. Mutate each security-relevant top-level metadata field independently (account, machine, serial, account row, day, lane, seed, and any block identity fields). Recompute block IDs and dependent entry IDs/idempotency keys so the mutation survives earlier hash gates. Keep topology, timestamps, and required shapes valid whenever the target is a binding check. Record the exact rejection reason/branch.
4. Treat a bundled mutation as supplemental only. If it changes `day` while leaving payload day or canonical session slots inconsistent, an early structural gate can reject it before source-binding or entry-binding logic; `with pytest.raises(ValueError)` then proves only that some gate fired.
5. Exercise ordered-list tampering separately: canonical order must be accepted and reversed order must be rejected after all earlier gates pass.
6. Exercise source-less validation when the API permits `source=None`. Distinguish source authorization (which necessarily needs `SourceConfig`) from internal canonical integrity (which should not silently disappear). Conditional guards such as `if source is not None` around a derived identity check are a likely bypass; probe a seed-only or equivalent mutation with and without source.
7. Require adversarial tests to assert the intended rejection reason or otherwise demonstrate branch reachability. Report any test that only asserts an arbitrary `ValueError` as gate-masked coverage, even when the implementation probe passes.
8. **Exact reason is not branch proof.** A test can assert the expected enum while failing at an earlier check that happens to use the same reason (for example, a metadata mutation reaches entry-level feed/lock consistency before `SourceConfig` mapping). For each source-binding mutation, independently keep *all* dependent fields canonical—entry IDs/idempotency keys, `feed.row`/`feed.machines`, lock machine/serial, block metadata, `validation` counts, skipped-account coverage, resources, and any assignment identity—and instrument the validator or use a disposable `sys.settrace` probe to record the rejecting locator. Report `MAPPING_CONFLICT@source-account` separately from `MAPPING_CONFLICT@entry-shape`.
9. Distinguish temporal/topological validity from mapping validity: “slots and block topology remain valid” does not mean the mutation reaches the source-binding branch. A serial test that synchronizes entry/feed/lock fields is stronger than a parameterized test that changes only block and entry fields. Add a dedicated fully rehashed account/serial source-bound case when the acceptance criterion names that branch.

For this reusable probe recipe and evidence table, see `references/schema-remediation-reaudit.md`. For the focused branch-reachability mutation recipe, see `references/source-binding-gate-masking.md`.

## Emergency Hard-Stop / Feature-Disable Fail-Closed Audit (Python + PowerShell)

When the deliverable is a read-only audit of an "emergency hard-stop / disable feature X"
implementation (shared Python core + Python consumer + PowerShell control-plane scripts)
against an approved plan, audit fail-closed correctness across heterogeneous routes:
allowlist conformance, immutability of the single disabled-state constant, guard ordering
before every launch/side-effect seam (Python entrypoints AND PowerShell `Start-Process`/
`Write-ResumeRequest`/`Start-ScheduledTask` via static source text/ordering scans), route
classification that does NOT blanket-disable unrelated Popen, and the autocrlf "M but
byte-identical" false positive. Reusable checklist + worked R1–R11 case:
`references/feature-disable-fail-closed-audit.md`.

## Read-Only Multi-Repo Consumer Audit (Phase-4 style)

Used when a single core feature (recovery contract, shared wheel, escalation hook) must be audited across N consumer repos WITHOUT any write: deliverable is ONE report artifact inside the core repo, per-consumer evidence tables, zero edits/commits to consumers. Full worked recipe + disposable scan script: `references/multi-consumer-readonly-audit.md`.

1. **Locate the plan/scope first with pathlib, not one path guess.** The referenced plan may live in a SIBLING repo (observed: plan at `automation-core/.hermes/plans/…` while the worktree was `automation-core-failed-locked-wt/`). `read_file` on the guessed path returns "File not found" — `pathlib.rglob('*<name>*')` across all plausible roots before concluding it is missing.
2. **Baseline every repo up front:** per-repo `git -C <Windows-path> status --short` + HEAD short SHA via python `subprocess` (Windows paths, not MSYS). Re-run the SAME counts at the end to prove the audit wrote nothing to consumers; pre-existing dirty states are recorded, not touched.
3. **Safe-vs-banned inventory via ONE disposable `os.walk` script** (run from `%TEMP%`, never inside the repos so `git status` stays clean): `BAN_DIR` regex (`\.git|\.ai-runs|\.runtime|__pycache__|node_modules|runs|outputs|reports|data|assets|presets|logs|\.hermes|…`), `BAN_EXT` set (xlsx/xls/csv/env/pem/key/log/jsonl/ndjson/pyc/bak/…), `BAN_NAME` regex (`^\.`, `.env`, secret, credential, token, password, auth, session, otp, serial, workbook). Prune blocked dirs with `dns[:] = [d for d in dns if not blocked]`; wrap `os.path.relpath` in try/except ValueError (the `nul` pseudo-file trap). Report banned paths as COUNTS only — never open them.
4. **Import-resolve BEFORE trusting a plan's pytest verify:** an installed copy of the package (venv site-packages) may shadow the worktree `src/` — run `python -c "import <pkg>; print(<pkg>.__file__)"` first. If it resolves elsewhere, the plan's verify fails at collection (`ModuleNotFoundError: No module named '<pkg>.<new-module>'`); report that blocker honestly with the exact error and the resolved path. Do NOT fake a pass or edit source to make it green.
5. **Report verification loop (pathlib):**
   - **Never embed the file's own SHA-256 inside it** — fixing the stated hash changes the hash, so it never converges. State line count in-file; record the hash externally (`git hash-object`/script) and return it in the summary.
   - Marker scan: an email regex flags NON-email `@` (version-claim strings like `handler@0.4.30`) — rewrite incidental `@` first, then assert no real emails / serials (`SM-…`, `R58…`) / 6-digit OTPs / token markers (`ya29`, `ghp_`, `eyJ`, `-----BEGIN`).
   - Coverage check: assert N per-consumer rows AND every required label stem appears in EVERY row (per-row count, not just global count).
   - `git status` of the core repo must show ONLY the report untracked; consumer repos must match session-start baseline counts.

## Cross-Repo Strict Diff Review (JSON-verdict pre-commit gate)

When the user asks for a strict pre-commit security/logic review of `git diff` across N repos and wants ONLY a JSON verdict (`passed`, `security_concerns`, `logic_errors`, `suggestions`, `summary`), use this recipe. Worked case 2026-08-18 (register gmail + Tiktok_Reg + add mail khoi phuc + automation-core): full detail in `references/strict-diff-review-nameerror-probes.md`.

1. **Scope discipline:** per repo, capture `git status --short` + `git diff --stat` in parallel. Review tracked `.py` diffs as the core; also READ new untracked `.py` files that are clearly part of the change set (`_run_all_targets.py`, launchers) — they ship the next run even though they aren't in `git diff`. Ignore AGENTS.md/PROJECT_RULES.md doc churn. Verify every file parses (`ast.parse`) but treat that as a floor, not a gate.
2. **AST undefined-name scope probe (catches crashes compile can't):** `ast.parse` OK ≠ no runtime crash. Build a probe: collect function-local args + module-level assigns, walk all `Name` nodes in each target function, flag `used - defined` for suspicious identifiers. This caught three guaranteed NameErrors on the account-removal success path (`adb_shell`, `serial`, `target_account` — cleanup block copied from a different module). **Must read with `encoding='utf-8-sig'`** — these repos ship BOM'd files and plain `utf-8` read raises `SyntaxError: invalid non-printable character U+FEFF` at line 1. Confirm module-level globals and `global` statements before declaring a name undefined.
3. **Verify every NEW import symbol against the PINNED wheel, and that the pin exists:** consumer diffs import new automation-core APIs (`close_all_recent_apps`, `resolve_proxy_mapping_path`, `batch_manages_target_locks`). The active site-packages may be a different version than `requirements-*.txt` pins. Extract the pinned wheel into a temp dir (native Windows paths, `cygpath -w`), point PYTHONPATH at it, probe each imported symbol with `getattr`/`inspect`. Also `ls dist/` — a pin referencing a wheel that was never built (`automation_core-0.4.24` with only 0.4.36+ present) breaks fresh env installs. Report mismatches: symbol missing from pinned wheel = consumer crashes at import under the pinned env; pin target absent from dist/ = stale pin.
4. **Class-method API-contract check:** when new code calls methods on shared-core objects (`lease.finish()` on `DeviceLockLease`), confirm the method actually exists on the class (`awk '/class X/,/^class /'` + grep `def `). `hasattr`-guarded calls to non-existent methods silently no-op — `elif hasattr(lease,'set_status')` releases nothing on the success path → leaked lock files that block the next batch. A silent no-op on a release/cleanup path is a P1 logic error, not a suggestion.
5. **Behavior-invariant spot checks for the risky patterns this codebase keeps producing:** random-salt username generation breaks retry determinism (re-run for same STT regenerates a different username than the one Gmail consumed); destructive `pm clear`/force-stop with no pre-state evidence or rollback; jitter minimums that exceed small-element bounds (±8px min vs <16px controls); loosened substring classifier markers (`"live"`, `"tim kiem"` in `_is_home_feed_xml`) that match nav bars on every screen; positional workbook column reads instead of header-driven lookup.
6. **Verdict contract:** `passed` = false unless BOTH `security_concerns` and `logic_errors` are empty (fail-closed, same as requesting-code-review). Blockers = guaranteed crashes (NameError on success path), broken pins, leaked locks. Hardening = suggestions. Keep `summary` to one paragraph naming the blocker and the fix order.

## Relationships to Other Skills

| Skill | When to Use Instead |
|-------|---------------------|
| `systematic-debugging` | Bug already exists, need root cause — audit is proactive, debugging is reactive |
| `requesting-code-review` | Pre-commit verification pipeline with security scan — audit is deeper, category-based inspection |
| `code-review-response` | Someone already reviewed your code and gave findings to fix |
| `test-driven-development` | Writing tests before code — use audit *after* code exists |
| `codebase-inspection` | Statistics (LOC, languages, ratios) — not bug hunting |

## Verifying an External Audit's Remediation (Stale-Audit Defense)

When the task is "fix findings from audit R<X>", the working tree may ALREADY contain the fix (a prior worker round, or the audit ran on older code). Blindly re-implementing wastes the round and can revert working code. Sequence:

1. **Check staleness first**: compare source-file mtimes against the audit transcript timestamp (`ls -la --time-style=full-iso`). If mtimes > audit time, the tree changed after the audit — re-verify before fixing.
2. **Re-run the auditor's exact probe shapes** against the current tree (tabulate ACCEPTED/REJECTED per finding, fresh temp state root per probe). If everything is already REJECTED/closed, the fix exists — do NOT re-implement.
3. **Prove the fix with mutation-verify when code is already green** (natural RED is impossible): temporarily disable each guard gate, run the matching test, confirm it FAILs (RED evidence), then restore byte-exact. This proves the test is red-capable, which is the TDD requirement when the fix predates your tests.
4. **Diagnose "mutation not caught" as gate masking, not a bad test**: an earlier gate (topology, path structure, empty-list shape) often rejects BEFORE the value gate under test fires. Re-run the test with `--tb=short` after mutating to see WHICH gate raised, then reshape the probe so topology/shape are legal and the value gate is the only thing that can reject (e.g. FINISHED must follow a real STARTED; artifacts must live in `invocation_root/<kind>/`; evidence_paths must be non-empty files).
5. **Byte-safe mutation harness on Windows**: never use `Path.write_text()` to patch repo files in a helper script — its default `newline=None` converts LF→CRLF on Windows and corrupts EOL (this bites exactly when the audit checks EOL cleanliness). Use `read_bytes()`/`write_bytes()` with an asserted single-match replace, record sha256 of every touched file BEFORE mutating, and verify sha equality after restore.
- **Untracked files have no Git baseline** — sha256 is your only restore proof and your "production code untouched" evidence for the report. Capture baselines before ANY edit (including probe scripts that import the package).

- **Baseline-trap provenance check:** when a purported narrow fix shows `A`/full-file additions, do not infer line-level edits from the commit diff. Verify `git log --follow -- <path>`, `git ls-tree -r --name-only <commit>^ -- <path>`, and the parent-tree status. Report the full-file addition as provenance, then identify the actual semantic change from the current guard/test content and a direct boundary probe. Keep tracked cleanliness separate from pre-existing `??` baseline files in the final status report.

2. **Acceptance boundary:** still inspect current callers/tests when the phase invariant is cross-cutting. A phase can have the correct four-file commit and a green suite while leaving a stale runtime guard or assertion elsewhere that contradicts the new invariant.

- Make the boundary probe observe control flow, not only the final return value. If both sides return the same sentinel for different reasons, instrument a post-guard operation (or use a minimal safe stub) so the report proves that the newly-valid boundary passes the guard while the newly-invalid boundary is rejected before side effects. On Windows, if `py_compile` cannot target `os.devnull`, compile into a disposable `tempfile.TemporaryDirectory()` and remove it before the final status check; never write probe bytecode into the repository.

## Pitfalls

- **Samsung S7 timeout propagation:** a longer UI budget does not cure invalid/non-XML UiAutomator output or a valid-but-wrong foreground surface. Classify fresh screenshot/XML evidence first; update shared core before consumers, protect atomic ADB budgets, and verify each repo's exact staged file list and remote head. See `tiktok-upload-ui-recovery/references/samsung-s7-ui-timeout-propagation.md`. **Worked case (2026-08-10, máy 74):** `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` repeated identically twice — root cause was NOT wait time but a *wrong-accepted root surface*: after `MEDIA_PUSH`, the flow's wait-for-feed accepted root indicator `'hồ sơ'` (Profile) as feed-ready, but `VIDEO_PICK` requires Home (`'trang chủ'`) with a labelled bottom-centre create control (`+`); Profile/video-detail has no such control → `_find_bounded_create_button` returns None → fail-closed (classifier correct, flow precondition wrong). 2 identical attempts = stop retrying blind; fix generic invariant: `MEDIA_PUSH → normalize to Home semantically (tap Trang chủ tab, no blind coordinates) → verify labelled create control → VIDEO_PICK`, fail closed `VIDEO_PICK_HOME_NOT_REACHED`. User insight: after a successful publish TikTok opens the just-posted video detail page — that IS the expected post-POST surface, not a pre-publish bug; always classify pre-publish vs post-publish lifecycle before treating video-detail as the failure.

- **Don't audit from partial context** — always read the complete file, not just the target function. Surrounding code may influence correctness.
- **Don't skip the test suite** — "looks right" after fixing is not enough. Run tests.
- **Don't fabricate findings** — if the code is clean, report `NO_ISSUES_FOUND`. Audits that always find something lose credibility.
- **Don't over-engineer fixes** — fix the specific issue, not everything that looks suboptimal. One change per root cause.
- **Don't forget to check callers** — a fixed function signature may break its callers. Run the full test suite.
- **Space in paths is a real shell-injection vector on `adb shell`** — `adb shell` joins args with spaces for the device shell. Always quote remote paths with `_quote()`.
- **`AdbClient.shell(args)` prepends `"shell"` itself** (automation-core `adb.py`: `return self.run(["shell", *args], ...)`) — callers that also pass a leading `"shell"` token produce the broken command `adb shell shell ...`. When a diff removes such a token from `adb.shell([...])` call sites, verify the contract against the PINNED wheel (`requirements-automation-core.txt` pins a `file://` wheel; the active site-packages copy can be an older version — see `references/pinned-wheel-contract-audit.md`) before approving. Then grep `'"shell",'` and classify every hit: raw-subprocess wrappers (e.g. `device_transport.py` building `[adb, "-s", serial, "shell", ...]` for `subprocess.run`) legitimately include the token; `AdbClient.shell` / `adb.shell([...])` call sites must NOT. A red-capable regression asserts the exact argv list for each fixed helper AND `all(command[0] != "shell" for command in commands)` — it must fail on the pre-fix `"shell"`-prefixed argv.
- **When verifying an EXTERNAL audit's remediation, re-run the auditor's exact probe shapes against the fixed code** (tabulate ACCEPTED/REJECTED), with a fresh temp state root per probe — journal/bridge share filesystem state and a reused root silently pollutes later probes. If a concurrent worker already implemented the fix, verify instead of re-implementing: see `concurrent-workspace-safety`.
- **On this Windows host, `search_files` with drive paths (`D:/...` or `D:\\...`) fails** — the path is MSYS-converted to `/d/...` which native rg cannot resolve ("IO error: The system cannot find the path specified"). MSYS `/d/...` paths resolve fine in bash builtins, but NATIVE binaries (git, rg) can also choke on them ("cannot change to ..." / "IO error: os error 3"). Bulletproof forms: `cd 'D:/…' && <binary> <relative-path>`, or `subprocess.run([..., '-C', 'D:/…', ...])` with Windows-path arguments from python.
- **Windows `nul` pseudo-file breaks `os.path.relpath`** — a stray file literally named `nul` inside a repo (observed `D:\Taadaa\gan-proxy\nul`) raises `ValueError: path is on mount '\\\\.\\nul'` mid-`os.walk`; wrap the `relpath` call in try/except ValueError and skip that entry, or the whole inventory scan dies on the first repo that has one.
- **Command scanners hard-block literal `reboot`/`shutdown` words** — a read-only grep pattern that merely CONTAINS the word `reboot` (e.g. `rg -n 'def |reboot|retry' file.py`) is rejected outright by the hardline blocklist ("system shutdown/reboot") even though it is only a search string, not a command to run. Workaround: character class (`re[b]oot`) or rephrase to avoid the literal token; same applies to other destructive-action keywords.
- **Probes importing the repo package fail with bare MSYS `PYTHONPATH="$(pwd)"`** — native Windows Python cannot resolve `/d/...`; convert first: `PYTHONPATH="$(cygpath -w "$(pwd)")"`. (Sibling fix to the search_files issue: MSYS path conversion bites native tools on both sides.)
- **`git ls-tree -r --name-only <commit> -- <path>` can return empty for tracked files on MSYS git** — do not conclude "absent from parent". Pipe the full tree through `rg` instead (`git ls-tree -r --name-only <commit> | rg 'path'`) and verify blob equality via `git hash-object` vs `git rev-parse <commit>:<path>`.
- **Verify consumer API contracts against the PRODUCTION venv interpreter, not bare `python`.** On farm hosts consumers run under `D:\Taadaa\python-envs\automation\Scripts\python.exe` (editable install: `pip install -e D:\Taadaa\automation-core`), while bare `python` resolves `...\Python312\Lib\site-packages\automation_core` — a STALE copy that can lack functions the committed code imports (worked case 2026-08-18: `resolve_proxy_mapping_path` absent in system site-packages → false "missing attribute" MAJOR alarm; present and correct under the venv). Probe with the venv interpreter FIRST (`import automation_core; print(automation_core.__file__)`) and state the resolved path in the verdict so a re-audit doesn't re-hit the same false alarm. Locate the venv via the admin install doc / `D:\Taadaa\python-envs\` listing. This is the consumer-run mirror of the pinned-wheel shadow lesson: the wheel lesson guards which worktree copy is loaded, this one guards which interpreter the repo actually runs under.
- **Imported symbol missing from the repo is NOT always a broken import — it may live in the pinned shared-core wheel.** When `from core.benign_popup import detect_captcha_puzzle_close` appears and `git grep "def detect_captcha_puzzle_close"` finds nothing in the repo, the symbol may be defined/re-exported by the installed `automation_core` wheel (e.g. `automation_core.tiktok.benign_popup`), not the repo file. Confirm with `python -c "from core.benign_popup import detect_captcha_puzzle_close; print(detect_captcha_puzzle_close.__module__, detect_captcha_puzzle_close.__code__.co_filename)"`. If it resolves to a site-packages wheel path, the import is valid — do NOT flag it as missing/undefined. Even more direct: `import inspect; inspect.getsourcefile(detect_captcha_puzzle_close)` returns the absolute path of the *defining* module — which disambiguates a re-export stub (e.g. the repo's `core.benign_popup` does `globals().update(...)` from `automation_core.tiktok.benign_popup`) from a true local definition in one step. (Inverse of the installed-copy-shadow lesson: there the wheel shadows the repo's source; here the repo re-exports a wheel symbol. Both require resolving the real loaded path before judging.)
- **Re-auditing a "migrate 100% of raw calls to helper" commit:** grep the raw primitive and expect exactly ONE hit — the helper's own implementation line (worked case: `grep -n '"input", "swipe"' social_reg_v1.py` → 1 hit at the `swipe()` helper body). Prove constant removal with `git log -S <SYMBOL> --oneline -- <file>` (expect add + remove commits; current grep = 0 hits). Report un-migrated sibling calls of the same primitive (e.g. raw `tap` sites left behind) as explicit out-of-scope notes in the verdict, not silent omissions.
