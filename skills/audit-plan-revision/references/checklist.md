# Worked example — adding route R11 to an auto-recovery disable plan

This is the concrete pattern from a real session: a plan enumerated auto-recovery
routes R1-R10 and a newly discovered PowerShell health-watcher route had to be
woven in everywhere.

## Source grounding (read-only)

`scripts/recovery-health-watch.ps1`, `function Invoke-HealthCheck` (~L512-534):
after guarded stale-worker stop `if (-not (Stop-TargetWorker $lease)) { return }`
(~L527) and `if (-not (Fence-Lease $lease)) { return }` (~L529), it calls
`Write-ResumeRequest -Path $resumeRequestFullPath ...` (~L533) then
`Start-ScheduledTask -TaskName $RecoveryTaskName` (~L534). This is an
auto-resume / scheduler bypass independent of `ai_recovery/agent.py` and of
`run-schedule-recovery-watch.ps1`. Registration source:
`scripts/register-scheduler-task.ps1` defines `$RecoveryHealthTaskName =
"TikTokScheduleRecoveryHealth"` (~L33-36) — do NOT blanket-disable unrelated
scheduler/proxy tasks.

## Places that had to be updated for scope coherence

1. Route table — add R11 row (source locator, symbol, mechanism, required verification).
2. Route Verification Matrix — add R11 static scan + named test
   `test_healthwatch_disabled_no_resume_request`; explicitly a STATIC/REGRESSION node.
3. Scope note "may only edit sites tagged AUTO-RECOVERY (R1-R10)" → R1-R11.
4. Route-discovery gate "enumerate all AUTO-RECOVERY routes R1-R10" → R1-R11;
   "re-scan R1-R10" → R1-R11.
5. Fail-Closed Entrypoint clause — list recovery-health-watch.ps1 as an extra
   independent launch/auto-resume route (Task 9 Steps 3-4, Step 6).
6. Shared Disabled-State Mechanism — PowerShell sub-bullet becomes R7/R8/R11;
   define `$AUTO_RECOVERY_ENABLED = $false` in all three scripts; note the
   existing `Get-ScheduledTask ... if State -eq 'Disabled' { return }` is a
   task-state check, NOT an emergency-stop — add an early short-circuit BEFORE
   Write-ResumeRequest/Start-ScheduledTask too.
7. Task 9 — heading "R5-R11"; exact-files list adds recovery-health-watch.ps1;
   add Step 6 (R11), renumber RED→GREEN to Step 7; exact-tests list adds the
   R11 static test; planned-new-files inventory adds
   `test_recovery_healthwatch_disable.py`.
8. Task 8 / handoff — rerun list adds the R11 test; "R5-R10" → "R5-R11";
   acceptance-criteria PowerShell bullet enumerates all three scripts.

## Verification that no contradictions remain

`grep -nE 'R1-R10|R5-R10|R5.R10' plan.md` → NONE_FOUND.

## Key discipline reminders

- R11 test inspects `.ps1` TEXT/ORDERING only — it does NOT run PowerShell and
  does NOT mock Start-ScheduledTask. Label it static, not runtime.
- Installed-task runtime behavior of TikTokScheduleRecoveryHealth is NOT PROVEN
  by the offline plan — deployment-gap risk, stated explicitly, never "passed".
- Documentation-only: only the plan `.md` was edited; no code/test/policy/commit.
