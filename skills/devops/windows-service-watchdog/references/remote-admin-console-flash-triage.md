# Remote Admin-PC console-flash triage

Use this reference when a secondary Windows farm host intermittently flashes a black CMD/Python window and the triggering job is not yet known.

## Evidence sequence

1. **Confirm target**
   - Use the repository's fixed-target SSH wrapper, not an arbitrary host/IP override.
   - Run `hostname`; retain the wrapper correlation ID and remote hostname.

2. **Enumerate scheduled task actions**
   - List non-Microsoft tasks and their `Execute`/`Arguments` fields.
   - Prioritize `python.exe`, `cmd.exe`, `.bat`, and unhidden PowerShell actions.
   - A task using `wscript.exe //B //Nologo` is only a candidate for headless execution; inspect the VBS-launched command if needed (e.g. if the VBScript calls `python` instead of `pythonw.exe`, Windows allocates a console subsystem process and briefly flashes conhost before hiding).

3. **Inspect repetition, trigger metadata, and execution history**
   - Check `StartBoundary`, enabled state, and repetition interval for suspicious 2–15 minute tasks.
   - Run `Get-ScheduledTaskInfo` sorted by `LastRunTime -Descending` to see what tasks *actually ran* during the recent window (e.g. within last 1–4 hours). An obvious unhidden task may be `Disabled` with a stale execution date from days/weeks ago.
   - Do not disable or remove a task based only on its label.

4. **Capture a process snapshot**
   - Query `Win32_Process` for `python`, `powershell`, `cmd`, `wscript`, `cscript`, and `conhost`, including `ProcessId`, `ParentProcessId`, `Name`, and `CommandLine`.
   - Correlate the process command line with the scheduled action. A bare `conhost.exe` is evidence of a console host, not attribution.

5. **Classify native-host noise**
   - Chrome/Claude native messaging may appear as `cmd.exe /d /s /c ... chrome-native-host.exe ... \\.\pipe\chrome.nativeMessaging...`.
   - These are normal browser integration processes and should not be blamed for a farm cron popup without a matching timestamp/parent chain.

6. **Handle negative evidence correctly**
   - If the obvious Python task is already disabled and registered Taadaa tasks use hidden VBS wrappers, state that explicitly.
   - Continue with Task Scheduler history, event timestamps, or a capture taken during the flash. Do not claim the issue is fixed from a snapshot that only shows the task is disabled.

## Safe interpretation

- The secondary host can run its own Hermes scheduler independently of the controller. Controller-side cron listings do not prove what is running on Admin-PC.
- A read-only investigation may stop at **blocked with evidence** when there is no live correlation. It must not invent a culprit or recommend pausing unrelated cron jobs.
- Use bounded, event-driven snapshots; avoid indefinite sleep/`ps`/`pgrep` polling loops.

## Reusable PowerShell probes (run through the fixed SSH wrapper)

```powershell
# Non-Microsoft scheduled tasks and actions
Get-ScheduledTask |
  Where-Object { $_.State -ne 'Disabled' -and $_.TaskPath -notlike '\\Microsoft*' } |
  ForEach-Object {
    $task = $_
    $task.Actions | ForEach-Object {
      [PSCustomObject]@{
        TaskName = $task.TaskName
        State = $task.State
        Execute = $_.Execute
        Arguments = $_.Arguments
      }
    }
  }

# Process attribution snapshot
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match 'python|powershell|cmd|wscript|cscript|conhost' } |
  Select-Object ProcessId, ParentProcessId, Name, CommandLine

# Tasks that actually ran recently (filter last N hours to distinguish active triggers from disabled ones)
Get-ScheduledTask |
  Get-ScheduledTaskInfo |
  Where-Object { $_.LastRunTime -gt (Get-Date).AddHours(-4) } |
  Sort-Object LastRunTime -Descending |
  Select-Object TaskName, LastRunTime, LastTaskResult
```

These probes are diagnostic only. Apply a fix only after positive attribution and a focused verification plan.