---
name: agent-verification-loop
description: "How to produce fresh, accepted test/lint verification evidence inside a Hermes agent session: the same-turn execution gate, and the pytest.main() deadlock pitfall under subprocess/multiprocessing suites."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, verification, pytest, agent-loop, evidence, harness]
    related_skills: [test-driven-development, systematic-debugging]
---

# Agent Verification Loop

How to *run* verification so it counts as evidence inside a Hermes agent session,
distinct from TDD philosophy (which is covered by `test-driven-development`). This
skill is about the mechanics of proving a change works *to the harness that audits
your work*, and the non-obvious failure modes of invoking pytest from within the
agent.

## When this applies

Any time you finish (or incrementally edit) code and must show it passes:
- After a RED→GREEN TDD cycle
- After a bug fix
- Before reporting "done" on a task with a verification gate
- When a system message says your work is `unverified`

## Scope contract before execution

A verification loop proves the **current task**, not an inherited plan. Before the
first tool call, freeze a short task contract:

```text
Goal: one sentence describing the requested outcome.
In scope: exact files, routes, components, or actions allowed.
Non-goals: adjacent systems that must remain untouched.
Done when: observable acceptance criteria and focused tests.
Stop when: criteria pass; ask before widening the scope.
```

The latest user message is authoritative over preserved TODOs, compaction
summaries, old plans, worker handoffs, and historical context. Treat those as
background only; never revive them when the user has narrowed or changed the
task. In particular, a narrow request to disable one alert-triggered recovery
route does **not** authorize changing global recovery, cron watchers, schedulers,
PowerShell tasks, unrelated launchers, or UI recovery.

Run a scope checkpoint at each boundary:

1. before the first read/write/delegate;
2. before touching a new file, route, or test family;
3. before broadening focused tests to a full suite;
4. before dispatching a worker or auditor; and
5. before the final report.

At every checkpoint ask: **Is this directly required by the current acceptance
criteria, or is it only suggested by stale context / a nearby failure?** If the
answer is the latter, do not edit, test-fix, delegate, or investigate it. Record
it as out of scope and stop or ask the user. Full-suite failures in unrelated
legacy domains are not a reason to widen production changes.

For every side-effecting worker, pass the same contract and an exact allowlist;
workers must self-stop on scope drift. Reaching the focused acceptance criteria
is a valid stopping point. More tests, route hardening, docs, or audits require
explicit task justification rather than a generic desire for completeness. Use
[`references/scope-contract-checklist.md`](references/scope-contract-checklist.md)
for the reusable checkpoint template.

## Cancellation and stale-plan gate

A later user instruction to stop, disable, pause, or change direction supersedes
preserved TODOs, compaction summaries, and earlier plans immediately. Cancel the
old verification plan before doing more edits or tests; do not finish a pending
fix merely because its RED/GREEN loop was already started.

For automation/recovery work, report these states separately:

- **Stopped:** no new retry, recovery, resume, patch, or live probe was started.
- **Disabled:** the future launch seam is fail-closed and the no-spawn behavior was
  actually tested; alert/reporting may remain enabled if requested.
- **Not disabled:** only investigation, a draft test, or an uncommitted edit exists.
- **Already running:** inspect process state only as needed; do not kill unrelated
  processes or touch devices without explicit scope.

Never claim a worker is disabled from a test draft or from the absence of a matching
process alone. Verify both the launch seam and the current process state when the
user asks for a shutdown.

## The same-turn execution gate (most important)

Some harnesses mark every edit turn `unverified` unless a **real test command
actually executes in the same turn the edit was made**. Writing a result-JSON, a
summary, or re-stating "228 passed" from a *previous* turn does NOT satisfy the
gate — it re-fires on the next edit.

**Rule:** after any code/test edit, run the real `pytest` (or equivalent) command
in that *same* turn, then report. If you need to prove a remediation, run the
thinnest failing-then-passing slice in the turn — do not lean on memory of an
earlier green run. The gate is satisfied by *execution in the turn*, not by
assertion in prose.

Concrete pattern that worked:
1. Make the edit (code + test).
2. In the same turn, run the targeted test(s): `terminal("pytest path::test_x -q")`.
3. Only then write the result JSON / report complete.

### Canonical-command discoverability gate
A passing pytest subprocess nested inside a shell heredoc or temporary driver may still be classified as `unverified` by an outer harness that scans for a canonical command. Satisfy both requirements in one same-turn terminal invocation:

1. Create the self-cleaning `hermes-verify-*.py` under the OS temp directory.
2. Have it run the exact focused command with a fresh interpreter (`[sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", TARGET]`) and print the full command, stdout, stderr, and exit code.
3. After the driver returns, invoke the exact canonical command directly in the same terminal invocation as a second check (not via `pytest.main()`): `python -m pytest -q -p no:cacheprovider TARGET`. This direct invocation makes the evidence discoverable while the driver remains the required isolated/adversarial check.
4. Run `py_compile`, AST, and `git diff --check` directly or from the driver, print each exit/result, then remove the verifier and isolated pycache in `finally` and print boolean cleanup evidence.
5. Report the result as **fresh ad-hoc verification**, never as full-suite green. If the direct canonical rerun differs from the driver result, treat the tree as unverified and investigate rather than quoting the better result.

If a turn *only* writes a JSON file (no test execution), expect an `unverified`
If a turn *only* writes a JSON file (no test execution), expect an `unverified` flag and a request to run a temporary verification script.

### Fresh evidence outranks earlier passes

A prior focused pass is historical as soon as a later fresh verification run starts.
The verifier and the direct canonical command must both be reported for the current
bytes; never quote an earlier green count to override a later failure. If either
fresh invocation fails, classify the tree as **unverified** and report the exact
failing node, assertion, captured output, and exit code. Do not retry until green,
weaken an acceptance assertion, or attribute the failure to the harness merely
because static checks pass. This is especially important for timing-sensitive
watchdog/queue tests: record the observed deadline/queue behavior and preserve the
failure for the owning implementation review.

#### Conflict-aware verification-only window

When a prior patch/read checkpoint reported a concurrent writer, or the candidate
is staged/dirty in a shared worktree, a verification request is **not** permission
to repair source or tests. Re-snapshot status, HEAD, staged/unstaged path sets,
hashes, and mtimes immediately before creating the verifier. Run the verifier and
the direct canonical command against that same evidence window. If either command
differs in result, or an allowlisted hash/mtime changes between them, invalidate
both as final evidence and report `CURRENT_TREE_DRIFT`; never quote the better
result. Re-read the live file and hand off the exact failure/ownership evidence.

The verifier launcher and its `hermes-verify-*` child are temporary evidence
artifacts, not repository edits. Create them under the OS temp directory, isolate
`PYTHONPYCACHEPREFIX`, and delete only artifacts created by the current run;
preserve pre-existing verifier files and report that preservation separately.

### Harness-safe Windows evidence window

The temporary verifier is itself a filesystem edit. A harness may therefore list the
`hermes-verify-*.py` path in Changed paths or re-issue `unverified` even when the
pytest subprocess passed. Prefer one self-contained terminal invocation that
creates the verifier with `tempfile`, writes it, runs it, prints the real result,
and deletes both the verifier and its isolated pycache in `finally`; verify the path
is absent before reporting. If separate tool calls are unavoidable, execute the
real test subprocess immediately after the verifier write, then clean up and
run no later source/test edits before the final report.

**Changed-path hygiene:** Treat every temporary launcher or verifier path reported by
the harness as an owned artifact, not as a repository change. Remove the launcher
and verifier after the evidence window, then perform a final status/path check. If
cleanup itself is a separate edit turn, rerun the canonical focused command in that
same turn before claiming fresh evidence. Report repository candidate paths
separately from temporary verification artifacts.

For Windows pinned-consumer checks, pass the exact interpreter and dependency
artifact explicitly (`PYTHONPATH` to the pinned wheel), set a private
`PYTHONPYCACHEPREFIX`, use `python -m pytest -p no:cacheprovider`, and report the
result as **ad-hoc verification**, never as suite green. Copy exact node IDs from
collection output when possible; for parametrized tests, invoke the parent test
node or use `--collect-only` instead of guessing an empty `[...]` parameter ID.
See `references/windows-temp-ad-hoc-verification.md` for the runnable recipe.

## Pitfall: `pytest.main()` deadlocks under process-spawning suites

If the target tests use `multiprocessing.Pool`, `subprocess`, or
`concurrent.futures` with *process* workers (e.g. atomicity / concurrency / race
tests that fork 8 processes), calling them **in-process** via a temp driver script:

```python
import pytest
pytest.main(["-p", "no:cacheprovider", "-q", *targets])   # can HANG
```

...can deadlock or stall indefinitely. Observed: the 8 adversarial tests finished
in ~1.6s via `python -m pytest` but the `pytest.main` wrapper sat at 400s+ (the
child processes never detach cleanly under the captured runner).

**Robust form — shell out to a fresh interpreter:**

```python
import subprocess, os, tempfile

env = os.environ.copy()
env["PYTHONPYCACHEPREFIX"] = tempfile.mkdtemp(prefix="hermes-verify-pycache-")
# set any tzdata / path env the suite needs, e.g.:
# env["PYTHONTZPATH"] = "D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo"
cmd = [PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", *targets]
proc = subprocess.run(cmd, cwd=WORKTREE, env=env, capture_output=True,
                      text=True, timeout=120)
print(proc.stdout, proc.stderr)
sys.exit(proc.returncode)
```

Notes:
- `-B` is an **interpreter** flag, not a pytest arg. `pytest.main(["-B", ...])`
  errors with `unrecognized arguments: -B`. Keep `-B` out of the argv list.
- A temp driver script should live under `C:\Users\Kibe\AppData\Local\Temp` (or
  `$TMPDIR`) with a `hermes-verify-` filename prefix and use a `tempfile` path for
  the pycache, then delete itself when done.
- Prefer `python -m pytest` over an in-process driver whenever the suite spawns
  processes.

### Final live-verification freshness gate
When a task has a resolved live target, any production or test edit after a canary invalidates that canary as final evidence. Run focused tests and compile/diff checks after the final edit, then run one fresh canary from the exact final tree via the approved recovery entrypoint. Verify artifact `final_status`, `stop_reason`, target identity, XML/screenshot evidence, and lock terminal state; an exit code or old artifact alone is insufficient. If a normal scheduler path rejects an intentional `blocked` recovery hold, treat that as the wrong entrypoint—not permission to delete the lock or change targets.

## Ad-hoc vs suite-green

A temp-script re-run of the *targeted* tests is **ad-hoc verification**, not the full committed suite. State that explicitly when reporting. The full suite (all files) is the real regression gate; if it is too slow to re-run in-turn, run the thin slice for the same-turn evidence and reference the prior full-suite run
for the same tree separately — but the thin slice must still *execute in the turn*.

## Delegated-work and final-diff audit gate

A delegated worker's completion message is not evidence that it edited the intended repository. Before accepting worker output:

1. Verify the exact worktree with `pwd`, `git status --short`, and `git diff --name-only`.
2. Confirm the reported test command belongs to that repository and language/toolchain. A green result from another project (for example, unrelated npm suites) is irrelevant and must be explicitly rejected.
3. Re-read the changed production files and tests yourself; worker summaries are untrusted claims for external side effects and code changes.
4. After every final edit, rerun the relevant tests in the exact worktree. Previous green counts are stale.

A green focused suite does not replace a structural diff audit. Read the final diff for integration omissions that tests may not cover: missing parser returns, unresolved-vs-environment paths being passed incorrectly, identity fields dropped at process boundaries, and changed dirty files outside the allowlist. Then run a small import/argument smoke check for newly added CLI flags and launcher contracts. If that smoke check fails because of import setup, fix the invocation (`PYTHONPATH`, pinned interpreter, or working directory) and rerun; do not classify a setup failure as a production failure.

For multi-process orchestration, test the actual boundary contracts, not only pure functions: assert the launcher argv contains assignment/cohort/worker identity, assert child publication writes the identity into the canonical manifest, and assert a surviving non-first child keeps the lease alive. Keep stale pre-existing dirty files untouched and verify their stash/working-tree presence before reporting.

### Final live-verification freshness gate
When a task has a resolved live target, any production or test edit after a canary invalidates that canary as final evidence. Run focused tests and compile/diff checks after the final edit, then run one fresh canary from the exact final tree via the approved recovery entrypoint. Verify artifact `final_status`, `stop_reason`, target identity, XML/screenshot evidence, and lock terminal state; an exit code or old artifact alone is insufficient. If a normal scheduler path rejects an intentional `blocked` recovery hold, treat that as the wrong entrypoint—not permission to delete the lock or change targets.

See [`references/delegated-verification-and-diff-audit.md`](references/delegated-verification-and-diff-audit.md) for the compact checklist and regression matrix.

The reference covers delegated-worker validation, cohort denominator consistency, process-boundary identity, multi-child lease semantics, and final diff verification.
files) is the real regression gate; if it is too slow to re-run in-turn, run the
thin slice for the same-turn evidence and reference the prior full-suite run
for the same-turn evidence and reference the prior full-suite run separately — but the thin slice must still *execute in the turn*.

### Node/npm full-suite runs

For JavaScript/TypeScript repositories using Node's test runner, run the package's
actual test script without inventing extra runner flags. Some harnesses append a
stale `--runInBand` (a Jest option) to `npm test`; do not treat that command's
30-second timeout as a code failure. Re-run the configured script cleanly, preferably
as a tracked background process with completion notification, while running the
focused changed-file tests and typecheck in parallel.

If the full Node suite remains active through a bounded wait, produces no failure,
and is stopped to avoid an unbounded session, classify it as **inconclusive / not
suite-green**. Never report a partial run as a pass or infer completion from the
absence of failures. Capture the last observed test area and duration, then report
the independently fresh focused counts, compile result, and formatting/diff checks.
After any final formatting or source/test edit, rerun the focused slice and compile
check; previous output is stale for the current tree.

## Evidence freshness is tied to the exact tree

A green command proves only the file tree, dependency artifact, and environment
that existed when that command started. Any subsequent source or test edit
invalidates it as **final** evidence for the current tree, even when the edit
looks documentation-only or "obviously safe." Keep it as historical/targeted
evidence, then rerun the relevant slice and final gate after the last write.

Before claiming release-ready, record together:

- exact `HEAD`/base and current changed-file allowlist
- dependency provenance (imported module path plus callable signatures; for a
  pinned wheel, run the focused suite with that exact artifact forced onto the
  import path)
- fresh targeted and full-suite results after the last edit
- compile/import check and `git diff --check`
- independent audit of the exact current diff

A passing ambient-runtime suite is not compatibility proof when production pins
a different wheel. Conversely, requirements text is not proof of what tests
imported. Verify both. If a full suite times out or a command returns no usable
count/traceback, classify it as inconclusive and isolate the failing slice; do
not quote an older count as the current-tree result.

## Cross-consumer lock-gate verification

When a shared manual-only device-lock contract is propagated across several
consumer repositories, verify each boundary independently rather than treating
a green core suite as proof for the consumers:

1. Inspect each worktree's baseline, dirty-file ownership, and exact diff before
   editing. Do not reset, checkout, stage, or commit files that contain another
   agent's concurrent work; narrow verification is still valid when the tree is
   intentionally dirty.
2. Separate **lock creation authorization** from **takeover authorization**. A
   normal consumer reservation that must retain a blocked lock may pass
   `user_authorized=True` so the core creates a real lease, while keeping
   `allow_takeover=False` and `takeover_authorized=False`. Reserve takeover flags
   for the explicitly authorized recovery/operator scope. Do not derive
   `user_authorized` from takeover flags: the core's `user_authorized=False`
   automation mode returns an unlocked no-op lease whose terminal `set_status`
   cannot persist `blocked`.
3. Add a real-filesystem regression at the consumer boundary: assert every lock
   alias exists before the worker runs, a non-success result leaves aliases with
   `status=blocked` and inactive ownership, and verified success removes them.
   Mock ADB/device seams; do not replace the lease with a mock in this test.
4. Verify `DeviceLockNeedsUserDecision` is caught before the generic unavailable
   exception and remains a distinct result, not `SKIPPED_LOCKED` or success.
5. Verify the CLI/runner exit code and the batch aggregate independently. A
   machine row such as `needs-user-decision` must produce a non-success aggregate
   (for example `manual-needed`) and a non-zero exit code.
6. After the last edit in each repo, run compile/import checks, the narrow lock
   tests, and `git diff --check` in the same turn. Re-run the full relevant suite
   after final semantic/test changes; earlier counts are historical evidence only.

Use the session-specific checklist in
[`references/manual-lock-gate-consumer-verification.md`](references/manual-lock-gate-consumer-verification.md)
for the exception/status/aggregate matrix and dirty-worktree review pattern.

## Windows temporary-driver recipe

For the Windows `unverified` gate, use the reproducible temporary-driver workflow in [`references/windows-temp-ad-hoc-verification.md`](references/windows-temp-ad-hoc-verification.md). The driver must use an OS-safe `tempfile` path with the `hermes-verify-` prefix, spawn a fresh `python -m pytest` subprocess, isolate `PYTHONPYCACHEPREFIX`, clean up the driver/pycache, and report exact counts as **ad-hoc verification** rather than suite green. If the environment injects a conflicting `PYTHONPATH`, remove it in the child environment; treat that as a setup fix, not a persistent tool limitation.

**Windows cwd quoting pitfall:** when the verifier is launched through a bash/MSYS wrapper, do not embed a Windows path literal as the subprocess `cwd` unless its escaping has been independently proven. Nested quoting can turn sequences such as `\\t` into a tab and cause `WinError 267`. Prefer `worktree = os.getcwd()` inside the driver (the outer command already runs in the repository), or construct the path with `pathlib.Path`/forward-slash normalization. Print the resolved cwd before spawning pytest. This is a verifier-launch fix, not evidence against the code under test.

**Windows nested-source quoting pitfall:** do not build a multiline verifier containing Python strings with `python -c` plus nested triple quotes. The outer shell/`-c` parser can consume `\\n` escapes and produce an unterminated-string or invalid-syntax failure before the verifier runs. Create the owned `hermes-verify-*.py` with an OS-safe temp path and a file writer, then launch that file with a fresh interpreter. Classify failures before pytest starts as `HARNESS_SETUP_FAILURE`; repair the harness and rerun the real targeted command. On success, remove only the verifier and isolated `PYTHONPYCACHEPREFIX` directory created by the current run and print explicit cleanup booleans.

**Same-turn evidence checklist:** after any source/test edit, run the self-cleaning verifier in the same tool turn; include exact pytest output, exit code, AST/compile result if included, and explicit driver/pycache cleanup booleans. A prior green command from an earlier turn is historical only and must not be reported as current-tree evidence.

### Follow-up `unverified` reminders

If a later turn repeats the platform reminder after an earlier verification report, treat the reminder as authoritative for that turn: create a new owned verifier and rerun against the current bytes. Do not merely restate the earlier pass. Prefer a simple launcher file built from `tempfile.NamedTemporaryFile` (or a shell command that exports the verifier source and writes it once) over a nested multiline `python -c`; complex quoting commonly fails before pytest starts. Classify such a pre-pytest syntax/unmatched-quote failure as `HARNESS_SETUP_FAILURE`, repair the launcher, and rerun. The successful evidence window must contain, in order: (1) verifier subprocess pytest, (2) direct discoverable `python -m pytest` command, (3) compile/AST/diff checks, (4) cleanup and final allowlist status. Report verifier and direct-run counts separately, and label the former **ad-hoc verification**.

## Anti-patterns

- Writing only a result JSON in the edit turn (no execution) → flagged `unverified`.
- Invoking `pytest.main()` for suites that fork processes → infinite hang.
- Re-asserting a prior green run as if it were fresh evidence → gate not satisfied.
- Putting `-B` in the pytest argv list → argparse error.
- Creating a temp verification script but not cleaning it up or not reporting cleanup status.
- Treating a timed-out canary or wrapper as a pass. A timeout is inconclusive: inspect the child process and isolated artifacts, confirm the production worker was untouched, then stop unless a fresh approval exists for retry. Do not retry a recursively destructive cleanup command merely because the first attempt was blocked.
