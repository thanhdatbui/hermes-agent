# Recovery-disable plan: closing a MINOR_FIXES audit (shared mechanism + per-route locator fixes)

Knowledge bank for applying an audit round whose findings target a recovery-disable plan's unspecified/incorrect mechanism. Captured from a real `MINOR_FIXES` 7-finding round on `disable-ai-auto-recovery` (consumer `tiktok-luot nuoi acc` + core `automation-core`). Companion to `recovery-disable-route-map.md` (which covers the independent-dispatcher trap). Here the audit already agrees the routes exist — it wants the DISABLE MECHANISM specified and a few locators/RED-validity corrected.

## Finding pattern: "unspecified disabled-state mechanism" (most important)

An audit (e.g. Finding 1) will flag that the plan never says *how* "disabled" is communicated to R1–R10, and that `--enable-live-recovery` already defaults to `store_true` (opt-in) so the RED test might pass on baseline. Fix by introducing ONE authoritative contract (do NOT claim it exists today — it is the implementation contract; the plan BUILDS it):

- **Python (R1–R6): canonical `AUTO_RECOVERY_ENABLED = False`** in `automation_core.global_recovery` (shared core module). Immutable, **no env/CLI/config override**. Every guarded site consults the SAME constant: `alerts.py` (R1), `agent.py` entrypoint/`_spawn_resume_process`/`finally` (R2–R4), `recovery_runtime.py` `main()`/`build_parser()`/`run_target_recovery()` (R5), `recovery_supervisor.py` `run()`/`_run()`/`main()` (R6), `watcher.py` `process_failure()` (R10). One source of truth — no per-route invented toggle.
- **PowerShell (R7/R8): fixed `$AUTO_RECOVERY_ENABLED = $false`** at the top of each `.ps1` (no ENV/CLI override). The existing PowerShell switches are SUBORDINATE and cannot override: `run-schedule-recovery-watch.ps1` `Dispatch`/`EnableLiveRecovery`/`Resume` (~L19-23) are read only inside the *enabled* branch; `register-scheduler-task.ps1` `EnableAutonomousRecovery` (~L45) / `EnableRecoveryTask` (~L47) build recovery action only inside the *enabled* branch. While the constant is `$false`, the disabled branch short-circuits before `Start-Process`/action-build and the enabled branch is unreachable.
- **Re-enable is OUT OF SCOPE.** Emergency hard stop; re-enabling needs a later, separately-authorized release change. Keep release-authorization separation explicit.
- Do NOT state the constant exists in baseline — current `global_recovery.py` has `GlobalRecoveryPolicy` but no switch; mark it as the Task 2/3/9 implementation contract.

## R5 RED must be VALID — all enabling flags, else it passes on baseline

`recovery_runtime.py` `build_parser()` exposes `--resume`/`--dispatch`/`--enable-live-recovery`, ALL `store_true` (default `False`). So invoking `main()` WITHOUT those flags already blocks internally at `if not enable_live_recovery` gates → the test would PASS on baseline → **invalid RED**. Fix:

- The executable RED test invokes `main()` with **ALL enabling flags** `['--dispatch', '--enable-live-recovery', '--resume']` (plus a minimal non-watch mode so `main()` does not block on a watcher loop) while disabled. On unguarded source the runtime is constructed/activated and dispatch proceeds → FAILS pre-fix → valid RED.
- GREEN: guard returns non-success BEFORE `ScheduleRecoveryRuntime` construction/`activate()`/`run_once`/`run_incidents`/`run_target_recovery`; the guard is ABOVE `build_parser`/`activate`/`run`, so parsing the flags cannot bypass it; neither flags nor retry re-enable.
- **Parser-only test is REGRESSION-ONLY, NOT a valid RED node.** `test_recovery_runtime_parser_flags_resolvable` (asserts `build_parser()` still exposes the three flags) passes on baseline because parsing only resolves flags; label it `REGRESSION-ONLY` and never count it toward RED→GREEN validity. The validate_plan_execution_contract.py informational-verification-node allowance covers this, but the plan prose must name it regression-only.

## R6 locator: public `run()` delegates to `_run()`; guard BEFORE both + `main()`

`recovery_supervisor.py`: public `RecoverySupervisor.run()` (~L2126) accepts `enable_live_recovery`, repair/audit/live executors, `artifact_root`, catches `LedgerInvalidError`, and delegates to `_run()` (~L2149); separate `main()` (~L2355). Audit may mislabel `_run()` as `run()`. Fix:

- Guard targets the public `run()` seam AND `main()` entrypoint; guarding only the internal `_run()` is insufficient (workers may bypass by calling `run()`/`main()` directly). Assert non-success BEFORE reaching `_run()` and before invoking executors/relaunch.
- RED test invokes the public `run()` with `enable_live_recovery=True` (and required executors/artifact_root) and asserts uncalled executors; also asserts `main()` guarded.

## R7/R8 PowerShell tests are STATIC TEXT/ORDERING SCANS — NOT runtime mocks

The `.ps1` files cannot be executed in CI. The Python tests (`test_recovery_powershell_disable.py::test_watcher_disabled_no_start_process`, `test_recovery_task_register_disable.py::test_register_action_disabled_no_live_recovery`) read the `.ps1` file **content** and assert the disabled branch exists and short-circuits before `Start-Process`/action-build. They do NOT execute PowerShell, do NOT mock a runtime process call, do NOT register a scheduled task. Capture this explicitly:

- Acceptance = SOURCE-LEVEL disabled branch proven (static scan + static test).
- Actual PowerShell execution / installed-task behavior remains **NOT PROVEN** → deployment-gap risk (track in Deployment-Gap Check, never report as complete).
- Do NOT claim "the Python test mocks the process call" or "inspects the generated action string at runtime" — that implies runtime behavior the test does not exercise.

## R10: target the caller `Watcher.process_failure()`, NOT the `RecoveryBridge` Protocol

`watcher.py`: `RecoveryBridge` (~L30-34) is only a `Protocol` (interface definition) — it does NOT call anything. The actual invocations are in `Watcher.process_failure()` (~L478 onward): `self.bridge.apply_recovery` (~L564), `recapture` (~L572), `retry` (~L581), `verify` (~L590). Fix:

- The disabled-bridge test instantiates/patch `Watcher` with a `unittest.mock.Mock` `RecoveryBridge` (the `self.bridge` attribute), triggers `process_failure()` through the disabled path, and asserts `applyarance`/`recapture`/`retry`/`verify` are ALL `assert_not_called()` (guard returns before any bridge invocation). No live execution.
- Explicitly state "do NOT target the `RecoveryBridge` Protocol class — target the `process_failure()` caller."

## Task ordering: numeric heading ≠ execution order

A plan may place Task 8 (final verification) BEFORE Task 9 (route hard-stop) by heading number, but Task 8 must RUN AFTER Task 9. An audit (Finding 6) flags this as ambiguous. Fix: rename the heading ("FINAL Verification — MUST run AFTER Task 9") and add a mandatory blockquote ordering: Gate 0 → Tasks 1–7 → Task 9 → Task 8; note the only reason Task 8 precedes Task 9 in prose is document layout, which must never be read as execution order. Keep the "Execution handoff" ordering consistent with this.

## Post-closure no-claim sweep (mandatory before reporting)

After closing findings, grep the whole plan and confirm 0 of each:
- No claim that `AUTO_RECOVERY_ENABLED`/`$AUTO_RECOVERY_ENABLED` already exists (should read "does NOT exist today / introduced by this plan").
- No claim R7/R8 Python tests are runtime mocks / execute PowerShell / register tasks.
- No claim the parser-only R5 test is valid RED.
- No diacritic path (`tiktok-luot nuôi acc`) — only ASCII `tiktok-luot nuoi acc`.
- No stale locator phrasing the findings superseded (e.g. `_run()` mistaken for `run()`, "regardless of disabled" RED expectation that ignores `store_true` defaults).

An intentional sentence *stating the old approach is forbidden* is allowed and reported separately, not mistaken for a stale hit.

## Verification evidence after closing

`wc -c` + `sha256sum` the plan; re-read fully (pagination) to confirm changed sections landed and no stale wording remains. Report path + bytes + SHA-256 + changed sections (by locator). The parent re-audits via hash/readback — the self-report is not evidence.
