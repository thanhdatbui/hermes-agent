# Recovery-disable plan: independent dispatcher routes & Route Verification Matrix

Concise knowledge bank for a MINOR_FIXES audit round on a plan whose goal is to **stop AI auto-recovery from launching** while preserving the alert/banner. Captured from a real `disable-ai-auto-recovery` plan revision (consumer `tiktok-luot nuoi acc` + core `automation-core`).

## The core trap: an entrypoint guard on one file is NOT enough

Source-grounded launch routes that recovery may flow through (each is a SEPARATE launch path):

- **R1** `automation-core/.../alerts.py` `subprocess.Popen(...)` launcher seam.
- **R2–R4** `python_runner/ai_recovery/agent.py` direct `__main__` entrypoint / `_spawn_resume_process` / `finally:` relaunch seam.
- **R5** `python_runner/scheduler/recovery_runtime.py` `main()` (`build_parser()` `--resume`/`--dispatch`/`--enable-live-recovery`; `run_target_recovery()`) — **INDEPENDENT dispatcher, NOT proven to delegate through agent.py**.
- **R6** `python_runner/scheduler/recovery_supervisor.py` `RecoverySupervisor.run()` + `main()` driving repair/audit/live executors — **INDEPENDENT, NOT proven to delegate through agent.py**.
- **R7** `scripts/run-schedule-recovery-watch.ps1` `Start-Process` of `-m scheduler.recovery_runtime` — launches `recovery_runtime` DIRECTLY, not agent.py.
- **R8** `scripts/register-scheduler-task.ps1` `Register-ScheduledTask` building an action with `-Dispatch`/`-EnableLiveRecovery` — control-plane route.
- **R9** `scripts/hermes_cron/tiktok_runner.py` generic `Popen` (~L359) — **classify via exact scan, do NOT blanket-disable**.
- **R10** `python_runner/hermes_cron/watcher.py` recovery-bridge methods (`apply_recovery`/`recapture`/`retry`/`verify`); no Popen in current source — producer/consumer bridge route.

Lesson: a fail-closed guard at `agent.main()` does NOT stop R5/R6/R7/R8. Each independent dispatcher MUST carry its own fail-closed disabled guard (return non-success BEFORE `run_once`/`run_incidents`/`run_target_recovery`/repair-audit-live executors/bridge/subprocess/auto-resume), and no flag/switch may re-enable. Treat as a "design-edits" finding (workflow step 5): touch Files + RED tests + GREEN/implementation + Acceptance + Gate for EACH route.

## Route Verification Matrix (concrete, not aspirational)

For each route give: exact `file:symbol/lines`, exact test `module::function`, exact pytest selector, exact command, and (for PowerShell/scan-only routes) a Git-Bash disposable-Python scan command. Scans cannot replace a non-launch EXECUTABLE test where executable behavior exists (R2/R5/R6/R7). Where feasible the executable test is REQUIRED; the scan is corroboration only.

Example R7 (PowerShell launcher) scan — run from Git-Bash (NOT PowerShell):
```bash
python - <<'PY'
import re, pathlib
p = pathlib.Path('/d/Taadaa/tiktok-luot nuoi acc/scripts/run-schedule-recovery-watch.ps1')
t = p.read_text(encoding='utf-8', errors='replace')
for pat in [r'Start-Process', r'-m scheduler\.recovery_runtime', r'--dispatch', r'--enable-live-recovery', r'--resume']:
    print(pat, [m.start() for m in re.finditer(pat, t, re.IGNORECASE)])
PY
```
Pass/Fail: PASS if disabled-mode edit refuses/strips the live-recovery flags and does NOT `Start-Process` the recovery child. Scan alone is insufficient — add an offline disabled-guard test too (mock the process call).

## R2 explicit node (distinct from R3/R4)

- `test_agent_main_disabled_non_success` in `python_runner/tests/test_ai_recovery.py`: invoke `agent.main()` directly with auto-recovery disabled; assert it returns a **non-success** status and that `screen_verifier.live_screenshot`, `_extract_ui_xml`, `_execute_adb`, network/patch (`patcher`), git, and `_spawn_resume_process` are ALL `assert_not_called()` (disabled returns BEFORE any side effect).
- Do NOT collapse into a broad `-k 'disabled or resume'` — that masks which specific RED node failed. Use exact per-RED selectors: `test_agent_main_disabled_non_success`, `test_agent_resume_blocked_when_disabled`, `test_agent_finally_no_relaunch`, `test_recovery_runtime_disabled_fail_closed`, `test_recovery_supervisor_disabled_no_resume`. RED→Verification `(module, node)` parity (validate_plan_execution_contract.py) still applies.

## Test-file inventory discipline

When an audit says "the Task N test list is wrong": re-scan the live tree (plan-baseline-drift pre-flight + `references/scan_plan_test_nodes.py`) and label every file `Existing` or `Create`. Keep **core** (`automation-core/tests/`) and **consumer** (`python_runner/tests/`) lists SEPARATED; never imply a cross-repo test exists. New files are `Create` and are produced only by a discovery checkpoint that runs BEFORE the test/fixture is written (fixture-discovery-before-design). The full focused-suite baseline (e.g. consumer 200 passed / 10 skipped) must be preserved.

## Do NOT blanket-disable unrelated Popen

Classify every subprocess site via EXACT scan. ADB/device/proxy subprocesses and generic cron Popen (e.g. `scripts/hermes_cron/tiktok_runner.py` ~L359) are UNRELATED and MUST stay untouched. Only reclassify + disable if the scan proves the site dispatches recovery. Deleting an unrelated Popen is a scope violation (plan-only scope honored: only the `.md` changes).
