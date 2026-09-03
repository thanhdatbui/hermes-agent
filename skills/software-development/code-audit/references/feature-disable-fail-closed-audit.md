# Emergency Hard-Stop / Feature-Disable Fail-Closed Audit (Python + PowerShell routes)

Reusable checklist for read-only audits of a "disable feature X via emergency hard-stop"
implementation spanning a shared Python core, a Python consumer, and PowerShell control-plane
scripts. The deliverable is a verdict + findings with locators, NO edits/commits/runtime.

Worked case (2026-08-22): disable AI auto-recovery routes R1–R11 across
`automation-core` (`alerts.py`, `global_recovery.py`), consumer `python_runner`
(`agent.py`, `scheduler/recovery_runtime.py`, `recovery_supervisor.py`,
`hermes_cron/watcher.py`, `flows/device_prepare.py`), and PowerShell
(`run-schedule-recovery-watch.ps1`, `register-scheduler-task.ps1`,
`recovery-health-watch.ps1`). Against approved plan
`2026-08-21_221734-disable-ai-auto-recovery-and-fix-packageinstaller-recovery.md`.

## 1. Allowlist conformance (mandatory, first check)
- Capture `git status --short` per repo. Every MODIFIED/ADDED file must appear in the
  plan's authorized changed-file list (the approved plan enumerates exact `Modify:`/`Create:`
  file paths per task). A file that is **changed but NOT in the allowlist** is a finding
  even if its diff is benign — flag it for parent to either (a) expand the allowlist or
  (b) revert. (Worked: `python_runner/tests/test_recovery_handlers.py` gained a
  `patch("scheduler.recovery_runtime.AUTO_RECOVERY_ENABLED", True)` to keep a legacy CLI
  test green after production `main()` started returning 1 — harmless but out-of-scope.)
- A core UI-compatibility doc change (`docs/ui-compatibility-contract.md`) may look like a
  scope leak but is REQUIRED by the plan's Task 5/Acceptance "update the canonical
  UI-compatibility record" clause — verify the content matches the contract, then note it
  as authorized, not a leak.

## 2. Immutability of the disabled state (the single source of truth)
- The canonical constant must be `AUTO_RECOVERY_ENABLED: bool = False` — module-level,
  literal `False`, added to `__all__`, with NO env/CLI/config override anywhere.
- Every guarded site must `from automation_core.global_recovery import AUTO_RECOVERY_ENABLED`
  (or, in sites with fragile import order, `try: import ... except ImportError: AUTO_RECOVERY_ENABLED = False`
  fail-closed fallback). Confirm the fallback value is `False`, not `True`.
- NO caller may re-enable: grep the whole tree for assignments to the name inside tests
  (`patch.object(global_recovery, "AUTO_RECOVERY_ENABLED", True)`) — these must be confined
  to mocked, no-executor, offline tests and never escape to live code.

## 3. Guard placement = fail-closed ordering (Python)
For each route, the guard must sit ABOVE every launch/side-effect seam:
- `agent.py` `run()` and `main()`: return non-success BEFORE `live_screenshot`,
  `_extract_ui_xml`, `_execute_adb`, vision/network, `code_patcher`, `_spawn_resume_process`.
  `finally` must only release locks — no relaunch/report/ADB/network/patch/git/resume.
- `recovery_runtime.main()` / `run_target_recovery()` and `recovery_supervisor.run()` / `main()`:
  return before constructing/activating the runtime, `run_once`/`run_incidents`/`run_target_recovery`,
  and before repair/audit/live executors. Guard the PUBLIC seam AND the entrypoint (`run()` + `main()`),
  not only the internal `_run()`.
- `watcher.py` `process_failure()`: return `"AUTO_RECOVERY_DISABLED"` BEFORE
  `apply_recovery`/`recapture`/`retry`/`verify` (target the caller, not the `RecoveryBridge` Protocol).
Verify with: `assertNotEqual(result, 0)` + `assert_not_called()` on each side-effect mock,
and a test that passes ALL enabling flags (e.g. `--dispatch --enable-live-recovery --resume`)
so the disabled guard is genuinely exercised (without the flags it would already block
internally and would NOT be a valid RED).

## 4. Guard placement = fail-closed ordering (PowerShell)
PowerShell cannot import Python, so it mirrors a fixed `$AUTO_RECOVERY_ENABLED = $false`
with NO ENV/CLI override. Audit the SOURCE-LEVEL disabled branch with a disposable text/ordering scan:
- Use `text.find()` indices, NOT a runtime mock. Assert
  `guard_idx < launch_call_idx` and `return/exit_idx < launch_call_idx`.
- Worked R7 `run-schedule-recovery-watch.ps1`: `guard=23074 < Start-Process=24130`,
  `exit 0 (after guard)=23288 < Start-Process` → disabled branch short-circuits before launch.
- Worked R8 `register-scheduler-task.ps1`: override block
  (`$recoveryLiveArgument=''` / `$recoveryTaskEnabled=$false`) sits INSIDE
  `if (-not $AUTO_RECOVERY_ENABLED) {` and AFTER the enabled-branch's live-arg assignment →
  strips `-EnableLiveRecovery` regardless of `EnableAutonomousRecovery`/`EnableRecoveryTask`.
- Worked R11 `recovery-health-watch.ps1` `Invoke-HealthCheck`: guard `return` BEFORE
  `Write-ResumeRequest` AND `Start-ScheduledTask`. The existing
  `if ([string]$task.State -eq 'Disabled') { return }` task-state check is NOT a substitute
  (it only blocks an already-disabled installed task, not the auto-resume call).
- Assert unrelated Popen/task registrations remain present (`$TrayTaskName`, `$ProxyTaskName`,
  `$WakeTaskName`, `$AllTrayTaskName`) — no blanket disable.

## 5. Route classification — do NOT blanket-disable (R9 pattern)
For a suspected-but-uncertain launch site, scan exact patterns and classify, don't assume:
- `scripts/hermes_cron/tiktok_runner.py` (~L359 `Popen`): if scan finds `Popen`/`subprocess`
  but NO `recovery`/`agent.py`/`--dispatch`/`--enable-live-recovery`/`--resume`/`Start-Process`,
  it is a generic UNRELATED subprocess → leave untouched. If it DID dispatch recovery,
  reclassify as AUTO-RECOVERY and require its own disable + fail-closed test.

## 6. Static scan ≠ runtime proof (deployment gap)
The PowerShell `.ps1` ordering scans (R7/R8/R11) prove SOURCE-LEVEL structure only. They do
NOT prove the installed scheduled task / deployed copy would behave the same. Report R11-class
nodes as "STATIC/REGRESSION, not runtime RED→GREEN" and explicitly state the open deployment
risk (whether `TikTokScheduleRecoveryHealth` is installed and would fire `Start-ScheduledTask`).
Never claim the Python scan is a PowerShell runtime mock.

## 7. autocrlf false-positive — a "M" that is NOT a change
`git status --short` can show ` M <file>` while `git diff`, `git diff HEAD`, and
`git hash-object <file>` == `git rev-parse HEAD:<file>` all confirm byte-identical content
(`core.autocrlf=true` leaves the index/working tree stat-dirty). Do NOT treat such a file as a
real change; explicitly record "stat-dirty, byte-identical to HEAD — not a real edit."
(Worked: we confirmed `python_runner/flows/recovery_handlers.py` flagged `M` but blob SHA matched HEAD.)
Contrast with a REAL out-of-allowlist change (section 1) — the two must be distinguished.

## 8. Exit-code propagation (silent fail-open at CLI)
`if __name__ == "__main__": main()` returns the int but the PROCESS exit code is 0.
Fail-closed at the function level (returns 1) is satisfied, but CLI exit status is 0 when
disabled → inconsistent with `recovery_runtime.py`/`recovery_supervisor.py` which use
`raise SystemExit(main())`. Note as a MINOR: wrap the agent `__main__` as
`raise SystemExit(main())` for consistency.

## 9. Task-5 typed-recovery correctness (independent of disable)
When the change also fixes a typed popup recovery (e.g. PackageInstaller deny before focus
failure): verify the new route is inserted BEFORE the focus-failure branch; it calls the
EXISTING typed handler with a `detected_screen` value matching the handler's guard constant
(`PACKAGEINSTALLER_DIALOG_SCREEN = "packageinstaller/system-dialog"`); fresh post-action
recapture + TikTok-foreground recheck; fail-closed when handler-false / popup-persists /
recapture-unavailable. The fixture must be a real sanitized XML (package identity, deny
resource-id, bounds) — NOT a reused CAPTCHA image, NOT fabricated labels.
