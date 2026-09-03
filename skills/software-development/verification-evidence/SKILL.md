---
name: verification-evidence
description: "How to produce, present, and gate verification evidence when a platform reminder (e.g. Hermes 'verification status: unverified') demands it, and how to resolve the conflict when the task contract mandates a specific canonical runner."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, testing, evidence, tdd, pytest, ci-gate]
    related_skills: [test-driven-development]
---
# Verification Evidence Protocol

## When This Applies

A platform or agent harness emits a verification-reminder such as:

> "You edited code in this turn, but the workspace does not have fresh passing
> verification evidence yet. ... Create a focused temporary verification script
> under ... with a `hermes-verify-` filename prefix, run it ..., clean it up ...
> and summarize it explicitly as ad-hoc verification rather than suite green."

This reminder fires automatically when it can't detect a canonical test/lint
command in the *current* turn. It is a **gate notification**, not a higher
authority than the user's explicit task spec.

## Core Rule

**A canonical verifier and a platform-requested ad-hoc probe are separate
artifacts. Run both when both are required; never present the probe as a
replacement for the canonical suite.**

## Live Batch Evidence

For a multi-device live batch, a non-zero launcher exit is an aggregate result,
not a diagnosis. Read the batch manifest and each failed target's own log before
reporting the cause. If the user asks to see the failure, send the exact
machine screenshot as a standalone native-media line only after inspecting it;
label historical failure-log state separately from the device's current state.
Do not infer a fresh-registration password failure from a password-field timeout
until the log proves the email was classified as a new account. Existing-account
OTP/login screens are a different branch. After collecting evidence, stop rather
than blindly retrying or tapping the device.

The user's task contract still controls the acceptance verdict: if it says
"do not use ad-hoc probe as replacement for pytest", preserve that rule. But a
later platform reminder that explicitly requires a `hermes-verify-` temporary
script is an additional current-turn evidence requirement, not permission to
skip the suite. Label the two results separately.

## Procedure When Reminded

1. Identify the task's canonical verification command (for example exact
   `pytest -q -p no:cacheprovider`, `py_compile`, and `git diff --check`).
2. If a canonical command exists, run it exactly and report its real counts and
   checks. Do not downgrade the result to "ad-hoc".
3. If the platform reminder also explicitly requires a temporary probe, create
   it with `tempfile.NamedTemporaryFile` (or `TemporaryDirectory`) under the
   OS temp directory, with filename prefix `hermes-verify-`. Run it against the
   changed behavior, not as a duplicate suite invocation, clean it up in a
   `finally`/cleanup path, and report it explicitly as **ad-hoc verification**.
4. If no canonical command exists, the ad-hoc probe is the available evidence,
   but still report it as ad-hoc rather than suite green.
5. If the first probe fails due to import context, make the repository root the
   subprocess `cwd` and/or add that root to `sys.path`, then rerun. This is a
   harness setup correction, not a production blocker.
6. Treat the reminder as turn-local: even if a suite or probe passed in an
   earlier turn, create and run a fresh `hermes-verify-` script in the current
   turn. If the task contract requires canonical verification, rerun that
   command in the same turn and report probe and suite as separate evidence.
7. Make the temporary script self-contained: call `tempfile.mkstemp` or
   `NamedTemporaryFile` from the verification driver to obtain an OS-safe path
   with the `hermes-verify-` prefix, write the script, run it, and remove it in
   `finally` (or explicitly verify deletion afterward). Do not rely on a
   hand-guessed temp path. Keep the probe focused on the changed behavior; do
   not accidentally pass both a whole test module and individual node IDs,
   which can duplicate tests and obscure the reported scope.

### Current-Turn Evidence Discipline

A previous turn's passing output is useful context but is not fresh evidence for
an edit made afterward. If a reminder says the workspace is unverified, perform
at least one new subprocess run after the last write. Record the exact command,
exit code, pass count, and cleanup result. If only the focused probe was rerun,
state plainly that it is **ad-hoc targeted verification** and do not call the
full suite green. If a canonical suite is also rerun, report its result
separately and use it for the final suite verdict.

#### Fresh-verifier ownership and finalization sequence

For every verifier created in the current turn, record the exact owned path and
snapshot the pre-existing `hermes-verify-*.py` set first. Create the probe with
`tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py",
 dir=tempfile.gettempdir(), delete=False)`, run it from the repository root,
and report its exit code and output. Cleanup only the path created by the
current run; never delete pre-existing verifier files. If the platform reminder
asks for cleanup, remove the owned probe in `finally`, verify it is absent, and
report `owned cleanup: PASS`. Then run the canonical focused pytest, compile,
AST, and diff checks in the same evidence window. Label the probe **ad-hoc
verification** separately from the real pytest count.

Some environments track successful verifier files as changed artifacts and
explicitly require them to remain. In that case preserve the owned probe and
report `owned cleanup: NOT PERFORMED — retained per tracking contract`; do not
claim cleanup. This exception must come from an explicit tracking requirement,
not convenience.

For dirty candidates, especially when files are staged/untracked rather than in
`HEAD`, bind evidence to the live bytes: capture `git status`, staged paths,
`HEAD`, and scoped hashes before the run, then re-check after it. If `HEAD`, the
index, or scoped mtimes change during verification, discard stale conclusions
and rerun. A green result from superseded bytes is not final evidence. Always
report unrelated dirty paths as preserved and distinguish them from the exact
allowlist.

### Windows Git-Bash and Space-Containing Repositories

Quote repository paths in shell `cd` commands, e.g. `cd '/d/Taadaa/tiktok-luot nuoi acc'`.
When launching a temp script, pass the repository root as `cwd` so package
imports and relative fixtures resolve. Use forward-slash or `Path`-based paths
inside the temporary script; avoid unquoted Windows paths and shell escaping
when possible.

**The Hermes session exports `PYTHONPATH` pointing at the hermes venv** (e.g.
`C:\Users\Kibe\AppData\Local\hermes\hermes-agent;C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`).
That venv may carry compiled extensions built for a different CPython version
(observed: PIL `_imaging.cp311-*.pyd` while the repo's interpreter is 3.12),
so running `pytest` from a terminal tool call can fail with
`ImportError: cannot import name '_imaging' from 'PIL'` — a FALSE environment
failure, not a product/test defect. Fix: clear it for the canonical run:

```
PYTHONPATH= /c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe -m pytest -q -p no:cacheprovider tests/...
```

Diagnose before concluding the package is broken: `echo $PYTHONPATH`,
`which -a python`, `python -c "import sys; print(sys.executable)"`, and compare
`ls <site-packages>/PIL/_imaging*.pyd` cp-tags against the interpreter version.
Also note `python -m pip` output can report the hermes venv's pip/site-packages
even when `sys.executable` is the standalone interpreter — another symptom of
the same injection. Full recipe: `references/windows-git-bash-running-tests.md`.

### Windows generated-verifier construction

When a launcher generates a second Python verifier, avoid nested `.format(...)` or f-strings over verifier source: verifier code commonly contains its own `{...}` expressions, producing `KeyError` before the probe runs. Inject paths with explicit sentinel replacement instead. Convert injected Windows paths to `Path.as_posix()` before writing Python source; raw `C:\\...` literals can become `unicodeescape` errors (`\\U`). Treat these as harness setup failures, repair the launcher, and rerun the product probe. The reusable sequence and failure taxonomy are in `references/windows-ad-hoc-verifier-harness-pitfalls.md`.

#### Platform-branch probes on Windows

Do not monkeypatch `os.name` to force a POSIX branch in a Windows verifier. `pathlib` and pytest use the process-wide platform value and can raise `NotImplementedError` while constructing `PosixPath`, turning a valid product probe into a harness failure. Prefer a narrow production seam such as `_is_windows_platform()` that can be monkeypatched, or use a small fake filesystem seam; restore/cleanup the seam in the verifier's `finally` path. Keep replacement-window interleaving at the actual production operation (for example, the rename/claim boundary), and assert both the exact fail-closed error and preservation of the competing canonical bytes.

## Owned temporary artifacts and harness failures

Before creating a verifier, snapshot the existing `%TEMP%/hermes-verify-*.py`
set and track every launcher/probe path created in the current turn. Cleanup
only those owned paths; never delete the whole glob because older verifier files
may belong to another session or worker. A launcher created with `write_file` is itself a changed path and must be removed explicitly before final status. For a probe created with `NamedTemporaryFile`, cleanup timing follows the active contract: if the current platform reminder asks for cleanup, delete the owned probe after the run and verify absence; if an explicit tracking contract requires successful probes to remain, preserve it and report that exception. Never delete pre-existing `hermes-verify-*.py` files. Report `owned cleanup: PASS` separately from `pre-existing artifacts preserved`.

Do not put a multiline verifier inside nested `python -c` quoting on Windows
Git-Bash. If the generated probe fails with a syntax error such as
`unterminated string literal`, `unexpected character after line continuation`,
or a `try/finally` syntax error caused by a one-line launcher, classify it as
`HARNESS_SETUP_FAILURE`, not product evidence. Prefer a short one-line driver
that writes a small probe, or write the launcher itself to a temporary file;
avoid embedding multiline `try`/`finally` blocks in `python -c`. The probe must
run with repository `cwd`/`sys.path`, capture the output, and clean only the
owned paths in `finally`. If the platform verifier tracks changed paths and
re-issues the reminder after an in-turn deletion, preserve the successful
`hermes-verify-*` probe until the next turn unless the current contract
explicitly requires immediate cleanup; report its path and ownership instead of
claiming the canonical suite is green. The exact Windows ownership recipe is in
`references/windows-owned-temp-verifier.md`.

## Reporting Format (proven useful)

- Baseline count (before any write), RED result, GREEN result, final exact
  suite count, compile, diff-check, changed paths, and blockers.
- Distinguish "real pytest pass count" from any ad-hoc probe. Never claim
  "verified" on a probe when the contract required the suite.

## Harness Fidelity Gate

A failing smoke harness is not automatically evidence of a production defect.
Before writing a regression or patching production:

1. Trace the real caller and identify the helper's exact caller-owned precondition
   (state, identity, lock/readiness, inputs).
2. Prove the harness established that same precondition immediately before the
   helper call.
3. If the harness invoked the helper from another state, classify
   `HARNESS_PRECONDITION_MISMATCH`, fix the harness, and re-run it. Do not create
   a production test/commit merely to support a non-production call sequence.
4. Keep the negative evidence: live screenshots/XML may disprove the proposed
   production finding even though the harness genuinely failed.

For high-risk live probes, review in two stages: architecture/plan first, then
exact generated harness bytes plus offline guard tests. A plan approval does not
cover code that did not exist during the audit. Only the exact-artifact approval
may authorize the bounded live phase.

## Independent Worker / Audit Handoff Gate

When an implementation worker or background delegation edits the workspace, its
completion status, reported hashes, or claimed test results are not evidence.
Before accepting the work:

1. Re-read the live files and reconcile `git diff` in the parent workspace.
2. Verify the worker touched only the authorized paths; explicitly inspect
   `git status --short` and protect unrelated untracked files by staging named
   paths only.
3. Run fresh RED regressions for each confirmed fail-open finding when the task
   requires TDD, then run the focused module and the full canonical suite after
   the final edit. Any earlier counts become historical context, not final
   evidence.
4. Run static checks independently: `py_compile` to an external temp target,
   `git diff --check`, EOL/BOM checks, and an AST review that confirms old
   top-level tests were not silently removed or nested.
5. For material changes, perform an independent read-only audit of the exact
   current diff. Do not audit a stale worker report or an earlier checkpoint.
   A pre-commit audit must return an explicit `APPROVED`; `MINOR_FIXES` or
   `REJECT` requires another fix → fresh verification → re-audit loop.
6. Only after approval, stage explicit allowed paths, commit, push, and verify
   local `HEAD` equals the remote branch SHA. Re-run a focused smoke test after
   push if the release gate calls for it.

Fail closed: a green test suite without a matching approved material-diff audit
is not a release approval, and an approved audit for an older diff does not
cover later edits.

## Exact-byte audit binding and post-live documentation

For a material read-only audit, a diff pasted into a prompt is not enough when
untracked files or a dirty worktree are in scope. Bind the auditor to the exact
current artifact set:

1. Record `HEAD`, branch, sanitized status, dependency provenance, and the exact
   canonical verification results.
2. For every scoped file, include SHA-256, byte count, line/EOL/BOM facts and,
   when prompt size permits, the full current numbered text. Treat sensitive or
   unrelated files as explicitly out of scope rather than silently reading them.
3. Require an unambiguous first-line verdict such as `APPROVED`,
   `MINOR_FIXES`, or `REJECT` and save the raw response separately.
4. Before accepting the verdict, re-read every bound file and require zero hash
   or byte-count mismatches. Also hash the saved audit response so the evidence
   can be identified later.
5. Any subsequent source, test, rule, HANDOFF, compatibility-record, or
   live-evidence documentation edit invalidates the exact-byte approval—even if
   executable code did not change. Regenerate the bindings and rerun the audit.
   A pre-live approval therefore does not cover post-live evidence text added
   afterward.
6. A healthy live run that short-circuits a recovery ladder proves only the
   direct path. State explicitly which conditional branches were covered by
   production-symbol tests rather than claiming the live device exercised them.

This binding check is distinct from the canonical test suite: both are required
when the task contract calls for tests and an independent audit.

## Async hard-deadline verification pattern

For watchdogs that submit work to a bounded thread pool, an outer `wait()` timeout is not a hard stop if the executor context manager later calls `shutdown(wait=True)`. Bind one absolute monotonic deadline into each child before submission, check it immediately before any queued side effect starts, and bound every child subprocess/queue wait by the remaining budget. On deadline expiry, cancel pending futures, terminalize every unreported target fail-closed, retain the required lock/handoff state, and use an executor shutdown path with `wait=False, cancel_futures=True` so the caller does not wait indefinitely for already-running threads. Regression tests must assert both: (1) queue timeout records queue wait/budget evidence and `subprocess_started=False`; (2) a queued child cannot start its side effect after the absolute deadline. Preserve a separate success gate: a future that finishes after the deadline must not be published as success.

Keep the focused reproduction recipe and expected evidence in `references/async-hard-deadline-watchdog.md`.

## Pitfalls

- **Don't let the reminder downgrade a strict contract.** If the plan says
  "no ad-hoc probe as replacement for pytest", creating one to satisfy the
  reminder is a contract violation, not compliance.
- **Don't claim green from a probe you were told not to use.** If you must run
  one, label it ad-hoc and still run the canonical suite for the real verdict.
- **Re-run the EXACT mandated suite**, including every file the plan lists —
  partial runs don't satisfy "exact baseline/focused/final counts".
- **Don't trust asynchronous worker completion metadata.** A worker can finish
  after a transport error or edit a different checkout; verify the parent live
  diff, hashes, test output, and authorized scope yourself.
- **Don't commit before the final audit.** Any post-audit edit invalidates the
  approval and requires a fresh audit of the new exact diff.
- **Don't stage with `git add .` in a protected workspace.** Use explicit file
  paths and verify protected/unrelated files remain unstaged and untouched.
- **A green result can be vacuous when the assertion lives inside a mock that
  is expected to yield a failure outcome.** Production error handlers swallow an
  AssertionError raised inside a `side_effect`, wrap it into the expected
  "failed" result row, and the test passes while the bug still exists (observed:
  asserting `_deadline_monotonic not in config` inside a failing fake
  `prepare_tiktok_for_smoke`). Record what the mock observed into an external
  `observed` dict/list; assert outside the patched block. Treat any new-behavior
  test passing immediately as a suspect for this shape — re-check what the test
  actually proves before counting it as RED/GREEN evidence.

See `references/windows-git-bash-running-tests.md` for invoking the canonical
See `references/windows-git-bash-running-tests.md` for invoking the canonical command in a Windows/git-bash repo whose working directory path contains
spaces (e.g. `tiktok-luot nuoi acc`). See `references/worker-material-audit-release.md` for delegated-worker reconciliation and the audit → commit → push gate.
