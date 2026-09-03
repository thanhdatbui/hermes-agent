# Hermes cron live-wiring plan: runtime-grounding lessons

Use this reference when a plan stages or pilots `no_agent` Hermes cron jobs on Windows. These are reusable runtime checks, not approval of any session-specific plan.

## Installed CLI/state semantics to verify

- Script paths are relative to the Hermes scripts directory; deployment should hash-verify tracked wrappers copied there.
- `no_agent` runs the script as the job. Empty stdout is silent success; business arguments should live inside a wrapper rather than the cron command.
- `workdir` is applied as the script cwd in no-agent mode. Do not describe agent-context injection as part of no-agent execution.
- There is no atomic paused-create flag in the observed CLI. `create` persists an enabled scheduled record first. Safer staging therefore needs:
  1. before-snapshot + transaction identity,
  2. far-future one-shot create,
  3. exact ID reconciliation even if stdout is lost,
  4. immediate pause,
  5. canonical read-back proving `enabled=false`, `state=paused`,
  6. edit to desired schedule while paused,
  7. second read-back and owned-ID rollback.
- The schedule-changing CLI verb is `cron edit --schedule` in the observed runtime, not a guessed `cron update` command.
- Manual `cron run` claims only enabled/non-paused jobs in the observed runtime. Therefore a "run the paused job for an offline smoke" plan is contradictory. Keep the cron record paused and invoke the deployed wrapper directly under an explicit offline kill-switch, then prove canonical cron state did not change.

## Long-running child lifecycle

Hermes script execution has a configured/default timeout, but that timeout is not a live-session ownership protocol. If the wrapper can outlive a frequent tick:

- either keep the wrapper bounded below the scheduler timeout and prove no overlap, or spawn a detached child with a durable identity-bound launch reservation;
- bind lease/reservation to PID + process creation time + manifest + entry + invocation;
- make later ticks silent no-ops while the reservation is live;
- do not automatically reclaim stale live leases: classify/hold `FAILED_LOCKED` for manual review;
- success requires artifact verification, not merely wrapper exit zero.

## Windows durability probe

Do not copy a POSIX "fsync every file, then fsync directory" sequence into a Windows plan without exercising it. Opening a directory with ordinary `os.open(..., os.O_RDONLY)` can fail on Windows, so directory `fsync` may be unavailable through that recipe. A Windows plan should:

- flush and `os.fsync` each temporary file;
- close handles before replacement;
- use same-volume `os.replace` for generation/pointer publication;
- preserve immutable generations and a small atomic ACTIVE pointer;
- specify reader fail-closed behavior for missing members, hash/revision mismatch, torn pointer, and incomplete generation;
- run target-Python fault-injection tests and record the actual primitive used.

## Audit-byte binding

Include the plan SHA-256 in the audit input. If any line changes after the verdict—even a fixed verification command—the previous verdict is historical only. Re-hash and re-audit before implementation.

## Concurrent-worker reconciliation

A timed-out/background worker may continue writing after the coordinator thinks it stopped. Before cleanup or audit:

1. prove the relevant process/delegation is inactive;
2. wait for file hashes/mtimes to stabilize;
3. inspect exact status/diff;
4. revert/delete only worker-attributable artifacts;
5. preserve unrelated user dirt;
6. re-check status and hash the plan.

Never repeatedly restore a file while a writer is still active; that creates a write/revert race and destroys evidence.

## Phase 9 plan R3 rebake — concrete contradictions to sweep (2026-08-13)

When rebaking the Phase 9 plan to an "R3 executable per runtime" plan-only, these contradictions were found in an earlier draft and MUST be swept for in every future edit. Each is a real runtime fact, not a guess.

- **9A task ordering + draft contradiction.** The plan must NOT make 9A.1 = "audit the generator draft" and 9A.2 = "source identity". Correct order: **9A.1 = Source identity** runs on the existing `SourceConfig` (`python_runner/hermes_cron/source_config.py`; `_unique_rows` at line ~121 rejects repeated row fleet-wide — must become `(machine, account_row)`; `_unique` line ~115 keeps `account_id` global; `_validate_machine_serials` line ~167 keeps machine↔serial one-to-one). **9A.2 = Generator adoption** runs AFTER 9A.1 + audit, operates on the two untracked outcome-unknown drafts (`scripts/generate_cron_source_config.py`, `python_runner/tests/test_generate_cron_source_config.py`) — hash/archive private rollback, never auto-accept, never commit generated root `hermes_cron_source_config.json`, and the generator MUST derive `account_row` from the per-machine physical slot (not global enumeration) to match 9A.1.
- **No phantom test file.** Do not reference `python_runner/tests/test_hermes_cron_phase9_identity.py` as a source of truth — that file is outcome-unknown. Move its intent into existing `test_hermes_cron_contract.py` / `test_hermes_cron_fleet.py` / `test_hermes_cron_p1_r2.py`.
- **Windows durability primitives (probe, don't assume).** `os.open(dir, os.O_RDONLY)` FAILS with `PermissionError [Errno 13]` on Windows — directory `fsync` is unavailable. Use `f.flush(); os.fsync(f.fileno()); f.close()` per file, then same-volume `os.replace(temp_dir, final_dir)` and `os.replace(temp_pointer, ACTIVE)`. State the directory-fsync POSIX recipe as NOT-required; acceptance uses the probed primitives. Add fault-injection tests: crash before/after generation replace, after ACTIVE replace, orphan `gen_*.tmp` reconciliation, orphan-temp handling, immutable-generation rejection.
- **Cron CLI verbs.** Staging = `hermes cron create <schedule> [prompt] --name --deliver --repeat --script --no-agent --workdir` (no `--paused`) → capture `Created job: <id>` → `hermes cron pause <id>` → `hermes cron edit <id> --schedule <five-field-cron>`. `hermes cron update` subcommand does NOT exist — keep it only as a forbidden/negative guard. `hermes cron run` refuses paused/disabled jobs (so offline smoke calls the deployed wrapper directly, never `run`).
- **Audit verdict vocab.** Only `APPROVED | MINOR_FIXES | REJECT`. `DEFERRED` / `OMITTED` are implementation/watcher decisions (e.g. watcher omitted because producer missing), NOT audit verdicts. One usable AG Opus verdict ends the slot — no cumulative "AG + Sol"; Sol is an optional read-only pilot reviewer, not a gating requirement.
- **Per-task release order (no aggregate commit).** RED → GREEN → exact diff + hash → AG audit BEFORE commit → explicit-allowlist stage/commit (Vietnamese message, per task). No "aggregate Phase 9A commit". Any material post-audit edit (plan OR diff) reopens audit: re-hash + re-audit.
- **Scheduler-timezone preflight.** Hermes config timezone may be `null`; OS Windows is `SE Asia Standard Time` (UTC+7, HCM). Scheduler uses `hermes_time.now()` with configured IANA timezone if present, else server local. Activation must FAIL-CLOSED unless the resolved offset is HCM-equivalent (+7). Do NOT mutate Hermes config inside a plan-only task — that needs separate authorization. Write `phase9-9b2b-tz-preflight.txt` evidence.
- **PowerShell `.ps1` syntax check from Git-Bash.** Single-quote the `-Command` argument so `$errors`/`$null` are not expanded by Git-Bash: `powershell.exe -NoProfile -Command '& { $e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path ''scripts/x.ps1''), [ref]$null, [ref]$e); if ($e.Count) { exit 1 } }'`. Never pass a `.ps1` to `py_compile`. If the plan's declared shell is Git-Bash, multiline Python/pytest commands use POSIX `\` continuation; a Markdown fence labelled `powershell` does not make PowerShell backticks executable in Git-Bash.
- **RED/Verification exact-node parity.** Before exact-hash audit, compare every RED pytest node as `(module, node)` against its Verification block. A whole-module pytest invocation covers nodes in that module; a same-named test under another module does not. In the 2026-08-13 R3 candidate, 9B.2 listed six RED nodes under `test_hermes_cron_job_spec.py` but Verification called the names under `test_hermes_cron_contract.py`; this is a blocking executable-contract mismatch, not an editorial nit. Use `scripts/validate_plan_execution_contract.py` from the umbrella skill to catch this class.
- **Exact-hash audit transport is separate from verdict.** Persist prompt/body/raw-response artifacts and bind path + SHA-256 + bytes + line count. An HTTP 404, transport exception, timeout, empty response, or unparseable body is `AUDIT_TRANSPORT_FAILED` / `BLOCKED_UNKNOWN`, never `REJECT` and never approval. Retry through the canonical configured audit route or wrapper; do not harden the failed endpoint/path as a permanent negative capability claim.
- **Final plan state.** The plan worker must NEVER self-approve. End the plan with `PENDING_AG_OPUS_REAUDIT` / `NO-LIVE` and an exact `path + SHA-256` handoff. Re-audit binds to those bytes; any later edit invalidates the verdict.
- **Evidence path convention.** Phase 9 evidence files are `phase9-9a1-source-identity.txt`, `phase9-9a2-generator-adoption.txt`, `phase9-9b2b-tz-preflight.txt`, `phase9-9a3-snapshot-bundle.txt`, `phase9-9a4-failure-producer.txt`, `phase9-9a5-live-safe-disabled.txt`, `phase9-9b-wrapper-hash.txt`, `phase9-9b-job-spec.txt`, `phase9-9b-staging-transaction.txt`, `phase9-9b-offline-smoke.txt`, `phase9-9c-human-gate.txt` under `C:\Users\Kibe\AppData\Local\hermes\cache\terminal\`.
