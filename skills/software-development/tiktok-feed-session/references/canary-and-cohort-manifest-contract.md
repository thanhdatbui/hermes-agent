# Canary Test & Cohort Manifest Contract in Feed Session

## Context & Root Cause
When running an ad-hoc canary test or targeted machine recovery:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

Environment variables `$env:TIKTOK_FEED_ASSIGNMENT_MANIFEST` and `$env:TIKTOK_FEED_WORKER_ID` are typically set in the shell/host for assignment validation.

### Cohort Contract Rule in Python Runner
In `multi_machine_feed_session.py` (`_apply_cohort_identity`), any presence of `_assignment_manifest` or `_worker_id` in config classifies the execution as cohort-bound.
If `_cohort_artifact` is missing, Python immediately raises:
`RuntimeError: cohort artifact and assignment manifest are both required for a live cohort child`

### Launcher Resolution
In `run-feed-session.ps1`, PowerShell performs worker preflight assertions via `AssignmentManifest.load`, but MUST ONLY append `--assignment-manifest` and `--worker-id` to the Python arguments if `$CohortArtifact` is present:
```powershell
if ($CohortArtifact) {
    $arguments += "--cohort-artifact", $CohortArtifact
    if ($AssignmentManifest) {
        $arguments += "--assignment-manifest", $AssignmentManifest
    }
    if ($WorkerId) {
        $arguments += "--worker-id", $WorkerId
    }
}
```
This keeps ad-hoc canary and single-machine recovery runs strictly in standalone execution mode while preserving full cohort contract enforcement during scheduled Hermes Cron runs.
