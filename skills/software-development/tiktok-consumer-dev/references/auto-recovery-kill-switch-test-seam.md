# Auto-Recovery Kill-Switch → Legacy Test Reconciliation (option b)

Captured 2026-08-22 from the read-only review of worktree
`codex/disable-ai-auto-recovery-consumer` (consumer @ `e337d2fc`, core @
`automation-core-implementation` / `c1575a0`). The approved plan was the
audit-revised "Disable AI Auto-Recovery + fix PackageInstaller" plan mandating
an immutable, fail-closed `AUTO_RECOVERY_ENABLED = False` consulted by every
auto-recovery route, with NO env/CLI/config override.

## The problem

Adding the kill-switch flips existing legacy tests to RED not because the
recovery logic is wrong, but because the guarded entrypoints short-circuit
before any algorithm runs:

- `recovery_supervisor.run()` returns `"AUTO_RECOVERY_DISABLED"` before `_run()`
- `recovery_supervisor.main()` / `recovery_runtime.main()` return `1`
- `Watcher.process_failure()` returns `"AUTO_RECOVERY_DISABLED"` before the bridge
- PowerShell R7/R8/R11 `*.ps1` short-circuit before `Start-Process` /
  `Write-ResumeRequest` / `Start-ScheduledTask`

Legacy tests that assert the *algorithm* outcome (`FINAL_BLOCKED`,
`READY_FOR_LIVE_VERIFY`, explicit registry injection) therefore break.

## The three failing buckets (and how each was reconciled)

1. **Legacy supervisor/planner tests** (`test_recovery_supervisor.py` classes
   `RecoverySupervisorTests` + `RecoveryRuntimeTests`) — ~8 tests expected
   `FINAL_BLOCKED` / `READY_FOR_LIVE_VERIFY` from `supervisor.run(...)`.
   *Fix:* `setUp` adds
   `patch("scheduler.recovery_supervisor.AUTO_RECOVERY_ENABLED", True)` and
   `patch("scheduler.recovery_runtime.AUTO_RECOVERY_ENABLED", True)`, stopped in
   `addCleanup`. This opts the offline algorithm into its internal seam ONLY
   inside the test process; production `main()`/`run()` stay fail-closed.
   *Verified:* full file → **73 passed**.

2. **`test_cli_incident_path_injects_explicit_registry`**
   (`test_recovery_handlers.py`) — expects `code == 0` from
   `main([...--observe-only])`, but `main()` returns `1` when disabled.
   *Fix:* wrap the call in `with patch("scheduler.recovery_runtime.AUTO_RECOVERY_ENABLED", True):`.
   Safe because `--observe-only` is detection-only (`run_incidents` →
   `observe_incident`, no planner/target runner — no live recovery occurs).
   *Verified:* file → **9 passed**.

3. **`test_recovery_health_contract.py` static `index('Start-ScheduledTask')`
   ordering assertions** — worried they'd break because `Start-ScheduledTask`
   also appears in comments. *No change needed:* the R11 short-circuit in
   `recovery-health-watch.ps1` already sits BEFORE the executable
   `Write-ResumeRequest` / `Start-ScheduledTask` calls.
   *Verified:* file → **14 passed**.

New fail-closed coverage added alongside (all green, 25 passed):
`test_recovery_runtime_audit.py`,
`test_recovery_healthwatch_disable.py`,
`test_recovery_powershell_disable.py`,
`test_recovery_task_register_disable.py`, and
`test_recovery_health_contract.py::RecoveryWatcherDisabledTests`.

## Recommendation rationale (chose b, reject a/c)

- **(b) test-only `patch(...ENABLED, True)` seam — ADOPTED.** Minimal, preserves
  the immutable production switch, requires no env/CLI bypass, keeps
  non-recovery contracts green.
- **(a) production observe-only carve-out — REJECTED.** Would weaken the
  immutable kill-switch and risk re-enabling detection under the emergency stop.
  Production already returns fail-closed; no production change was needed.
- **(c) rewrite legacy contracts — REJECTED.** Would discard genuine coverage of
  the non-recovery planner/ledger behavior (`READY_FOR_LIVE_VERIFY` gating,
  `FINAL_BLOCKED` caps) that must remain green.

## Verification commands (offline, no ADB/network/Telegram)

```
cd "D:/Taadaa/tiktok-luot nuoi acc-implementation"
python -m pytest -q python_runner/tests/test_recovery_supervisor.py
python -m pytest -q python_runner/tests/test_recovery_handlers.py
python -m pytest -q python_runner/tests/test_recovery_health_contract.py
python -m pytest -q python_runner/tests/test_recovery_healthwatch_disable.py \
    python_runner/tests/test_recovery_powershell_disable.py \
    python_runner/tests/test_recovery_task_register_disable.py \
    python_runner/tests/test_recovery_runtime_audit.py \
    python_runner/tests/test_recovery_health_contract.py
python -m pytest -q python_runner/tests/test_ai_recovery.py \
    python_runner/tests/test_device_prepare.py
```

(Use a clean interpreter with `env -u PYTHONPATH` and the repo's real Python —
see the PYTHONPATH-poison section — and prefer the Windows-absolute path since
`search_files`/rg fail on the repo's space-containing path `D:\Taadaa\tiktok-luot
nuoi acc`.)

## Pitfalls / checklist before declaring reconciled

- Confirm the **production source changed ONLY guards** (the `if not
  AUTO_RECOVERY_ENABLED: return ...` seams + the `import xml.etree.ElementTree`
  fix in `agent.py`). No recovery-logic behavior change.
- Confirm `automation_core.global_recovery.AUTO_RECOVERY_ENABLED` is still
  `= False` (untouched) — the seam patches only the *test process*, not source.
- A reported "N failing tests" may already be reconciled in the working tree by a
  prior worker — RUN the buckets before assuming they're still red. In this
  session all 3 were already green; the real deliverable was the
  recommendation + rationale, not a code change.
- PowerShell static-ordering tests (`text.index("X") < text.index("Y")`) can be
  confounded by the same token appearing in COMMENTS — scope the check to the
  function body (slice `text[text.find("function X {"):]`) and match executable
  call lines, not comment lines.
- The seam is unittest-mock `patch` on the *imported module attribute*; it does
  NOT touch the canonical constant and cannot re-enable production recovery.
