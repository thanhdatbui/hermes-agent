# External Audit Remediation — Verification Recipe (R8→R9 hermes_cron)

Session: 6 P1 findings from an independent audit (gpt-5.6-sol, read-only, 13:56) of
`python_runner/hermes_cron/{journal,watcher,models}.py`; task = fix under strict TDD,
scope-limited (only journal/watcher/models + 4 test files), no commit/live action.

## The core surprise

The working tree ALREADY contained the R9 fix before this session started:

- `ls -la --time-style=full-iso` on the scoped files: `journal.py` 18:46, `watcher.py` 18:55,
  `test_..._p1_r2.py` 18:53 — all AFTER the audit's 13:56 transcript.
- Re-running the audit's exact probes (the transcript even included the probe scripts
  in `exec` blocks) showed all six findings already REJECTED/fail-closed.
- The 109-test suite passed before any edit. => Fix existed; verification was the job.

Lesson: a "fix the audit findings" task is a verification task until proven otherwise.
Staleness check = mtimes vs transcript timestamp + re-run the auditor's probes verbatim.

## Probe pattern (per finding)

Run each probe against a FRESH temp state root — journal/bridge share filesystem
state and a reused root silently pollutes later probes. Two probe files were used:
one re-running audit probes verbatim, one probing DEEPER angles the audit named
but its probes didn't cover (registered-handler sensitive/locked, handler_id vs
evidence mismatch, attempt=9, cross-attempt artifact binding, replay-forged lines).

Result table shape to report:

| # | Audit finding | Audit probe (old code) | Current tree | Mutation test |
|---|---|---|---|---|
| 1 | registry check after DETECTED | CLASSIFIED written | NO_HANDLER_IMPLEMENTED | RED ✓ |

## Mutation-verify (RED evidence when code already green)

TDD normally requires watching the test fail first. When a prior round already fixed
the code, natural RED is impossible — so PROVE red-capability by disabling each guard:

1. Record sha256 of `journal.py` / `watcher.py` BEFORE mutating (files were untracked —
   no git baseline; sha is the only restore proof).
2. For each finding, patch out exactly one gate (e.g. `if not self._registered_handler_matches():`
   → `if False and not ...:`), run the matching test, confirm exit != 0, then patch back
   and assert sha256 == baseline.
3. Report "6/6 mutations caught → every test is red-capable".

## Gate-masking: "mutation not caught" != "bad test"

First mutation run: F3/F5/F6 tests still PASSED with their gate disabled. Cause:
an EARLIER gate rejected the probe before the value gate under test could fire:

- **F3 (invocation binding)**: probe appended `LAUNCH_FINISHED(inv-B)` directly after
  `LAUNCH_RESERVED` — the TRANSITION TOPOLOGY gate (FINISHED requires STARTED first)
  rejected it, so the invocation-value gate was never reached. Fix: append a valid
  `LAUNCH_STARTED(inv-A)` first, then the spliced FINISHED is topology-legal and only
  the value gate can reject.
- **F5 (artifact reference_time)**: artifact file lived at `root/evidence/...` but the
  v2 binding gate requires `candidate.parent.name == kind` — i.e. files must live in
  `invocation_root/<kind>/`. Path-structure rejected before the reference gate. Fix:
  create the artifact at `invocation_root/recapture/artifact.json`.
- **F6 (final-blocked matrix)**: `evidence_paths=[]` + `evidence_binding={}` were
  rejected by the payload-shape gate before the attempt-matrix gate ran. Fix: build
  real v2 evidence/sol files + bindings (ArtifactBindingV2.from_file) but leave the
  attempt-8 chain incomplete, so the matrix gate is the only rejector.
- **F3 re-check**: the invocation check exists in TWO gates (transition + canonical
  reducer); mutating only one was not caught. Disable BOTH call sites.

Diagnosis method: run the test with `--tb=short` while the mutation is applied and
read WHICH gate raised (e.g. `_existing_regular_paths` → INVALID_PATH).

## Windows byte-safety (EOL corruption)

`Path.write_text()` on Windows uses `newline=None` → converts LF→CRLF on write.
The first mutation harness used it to patch repo files => every file flipped to CRLF,
"RESTORE MISMATCH" everywhere, and the audit's EOL cleanliness check would have failed.
Fix used thereafter:

- `read_bytes()` / `write_bytes()` only, replacing a UTF-8-encoded needle asserted to
  occur exactly once (`data.count(needle) == 1`).
- sha256 baseline + equality assert after every restore.
- To recover an already-flipped file: `path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))`
  and re-verify sha against the pre-session baseline.

Note: `git diff --check` emits a "LF will be replaced by CRLF" warning when repo
`core.autocrlf=true`; exit code 0 is the pass signal — the warning is not an error.

## Scope discipline & final evidence set

- `git status --short` before editing: treat unrelated modifications (flows/, config/)
  as protected scope; report them as pre-existing, never touch.
- Final verification bundle: full 4-file suite (117 passed = 109 baseline + 8 new),
  `py_compile` on all scoped files, EOL/trailing-whitespace scan (all LF), `git diff --check`,
  production-file sha == baseline (proves "0 diff on production" claim), then a disposable
  `tempfile`-based probe with `hermes-verify-` prefix for the changed behavior, cleaned up
  afterwards, reported explicitly as ad-hoc verification (not suite green).
- No commit/push/stage unless asked; no live action on scheduled systems.