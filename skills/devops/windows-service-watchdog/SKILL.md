---
name: windows-service-watchdog
description: Patterns and verification checklist for building resilient Windows watchdog scripts that supervise long-running services — single-instance enforcement, child process cleanup, consecutive failure thresholds, startup grace periods, and live verification.
category: devops
tags: [watchdog, process-supervision, powershell, windows, mutex, process-cleanup, health-checks, restart-thresholds]
---

# Windows Service Watchdog / Process Supervision

**Trigger**: Any task involving managing a long-running Windows service/process via a watchdog script (PowerShell/Batch) that must:
- Enforce single-instance execution (no duplicate watchdogs)
- Track and clean up child processes to prevent accumulation
- Implement consecutive failure thresholds before restart
- Provide clean process termination with grace periods before restart
- Log structured evidence for verification

---

## Core Pattern

### 1. Single-Instance Lock (Mutex with Safe Release)
```powershell
$MutexName = "Local\YourService_Supervisor_Mutex_v1"
$mutex = $null
$hasMutex = $false
try {
    $mutex = New-Object System.Threading.Mutex($true, $MutexName, [ref]$hasMutex)
    if (-not $hasMutex) {
        Write-Log "Another watchdog instance is already active. Exiting duplicate."
        exit 0  # Triggers finally block; $hasMutex guard prevents unsynchronized release error
    }
} catch {
    Write-Log "Mutex initialization failed: $_. Cannot guarantee single instance. Exiting."
    exit 1
}

# ... watchdog loop ...

finally {
    if ($mutex -and $hasMutex) {
        try {
            $mutex.ReleaseMutex()
            $mutex.Dispose()
        } catch {}
    }
    Write-Log "Watchdog stopped."
}
```

### 2. Dynamic Environment Paths & Portable Fallbacks
Never hardcode `C:\Users\<user>\...`. Use environment variables with dynamic fallback resolution:
```powershell
$NodeExe = "C:\Program Files\nodejs\node.exe"
if (-not (Test-Path $NodeExe)) {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) { $NodeExe = $nodeCmd.Source }
}

$AppDir = "$env:USERPROFILE\YourApp"
if (-not (Test-Path $AppDir)) {
    $fallback = "$env:LOCALAPPDATA\YourApp"
    if (Test-Path $fallback) { $AppDir = $fallback }
}

$LogDir = "$env:APPDATA\YourService\logs"
$LogFile = Join-Path $LogDir "watchdog.log"
$StopFile = "$env:APPDATA\YourService\watchdog.stop"
```

In companion `.vbs` startup launchers:
```vbscript
Option Explicit
Dim WshShell, appData, scriptPath
Set WshShell = CreateObject("WScript.Shell")
appData = WshShell.ExpandEnvironmentStrings("%APPDATA%")
scriptPath = appData & "\YourService\watchdog.ps1"
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptPath & """", 0, False
Set WshShell = Nothing
```

### 3. Streamlined Health Check (Direct HTTP)
Avoid redundant raw TCP socket connects before HTTP requests; `Invoke-WebRequest` tests socket connectivity and HTTP status in one operation:
```powershell
function Test-ServiceAlive {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://${HostAddr}:${Port}/api/health" -TimeoutSec 5
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
}
```

### 4. Process Discovery & Cleanup
```powershell
function Get-ServiceProcesses {
    # 1. Find processes by command line signature (e.g., "run-next.mjs start")
    # 2. Find child processes via ParentProcessId
    # 3. Check port ownership (Get-NetTCPConnection)
    # Return deduplicated list by ProcessId
}

function Stop-ServiceProcesses {
    $procs = Get-ServiceProcesses
    foreach ($proc in $procs) { Stop-Process -Id $proc.ProcessId -Force }
    # Wait up to N seconds for exit
}
```

### 5. Consecutive Failure Threshold
```powershell
$MaxConsecutiveFailures = 3
$CheckIntervalSec = 10

$consecutiveFailures = 0
while ($true) {
    if (Test-ServiceAlive) { $consecutiveFailures = 0 }
    else {
        $consecutiveFailures++
        if ($consecutiveFailures -ge $MaxConsecutiveFailures) {
            Restart-Service
            $consecutiveFailures = 0
        }
    }
    Start-Sleep -Seconds $CheckIntervalSec
}
```

### 6. Startup Grace Period with Polling
```powershell
$MaxStartupWaitSec = 30
$StartupPollIntervalSec = 3

$process = [System.Diagnostics.Process]::Start($psi)
$elapsed = 0
while ($elapsed -lt $MaxStartupWaitSec) {
    Start-Sleep -Seconds $StartupPollIntervalSec
    $elapsed += $StartupPollIntervalSec
    if ($process.HasExited) { return $false }
    if (Test-ServiceAlive) { return $true }
}
return $false  # Timed out
```

---

## Verification Checklist (Live Proof)

| Check | Command | Expected |
|-------|---------|----------|
| Syntax | `[System.Management.Automation.Language.Parser]::ParseFile(...)` | 0 errors |
| Single watchdog process | `Get-CimInstance Win32_Process \| Where { $_.CommandLine -like '*watchdog.ps1*' }` | Exactly 1 |
| Single service process | `Get-CimInstance Win32_Process \| Where { $_.CommandLine -like '*service-signature*' }` | Exactly 1 |
| Port ownership | `Get-NetTCPConnection -State Listen \| Where LocalPort -eq PORT` | 1 process owns port |
| Health endpoint | `Invoke-WebRequest http://127.0.0.1:PORT/health` | HTTP 200 |
| Duplicate prevention | Launch 2nd watchdog instance | Logs "already running", exits |
| Auto-recovery | `Stop-Process -Id <service-pid> -Force` | Watchdog restarts within threshold |

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Multiple watchdogs started via Startup folder + manual launch | Mutex on `Local\` namespace (per-session) prevents both |
| Mutex initialization throws exception | In `catch` block, log error and `exit 1` immediately so no watchdog runs unshielded |
| Application root path missing during restart attempt | Validate `Test-Path $AppDir` before stopping processes or attempting launch; abort restart if absent |
| `ReleaseMutex()` called on duplicate exit throws ApplicationException | Track `$hasMutex` boolean; only call `ReleaseMutex()` if `$mutex -and $hasMutex` |
| Hardcoded `C:\Users\<user>` breaks across profiles or machines | Use `$env:APPDATA`, `$env:LOCALAPPDATA`, `$env:USERPROFILE` and `%APPDATA%` in VBS |
| Redundant TCP connect before HTTP check causes socket churn | Call `Invoke-WebRequest -UseBasicParsing` directly with a 5s timeout |
| Hardcoded API keys in startup/service scripts | Resolve keys from environment or parse `.env` dynamically on launch |
| Zombie child processes (esbuild, conhost) accumulate | Include child process lookup by `ParentProcessId` |
| Port stuck in TIME_WAIT after kill | `Start-Sleep 1` after `Stop-ServiceProcesses` before restart |
| Health check passes but service not fully ready | Poll health endpoint, don't just check TCP port |
| Watchdog stops but leaves service running | Stop file (`watchdog.stop`) signals graceful shutdown; `finally` block releases mutex |
| Fixed 8s startup timeout too short for cold Next.js builds | Use configurable grace period (30s) with progress logging |
| Restart loop on flaky health checks | Consecutive failure threshold (3) filters transient blips |
| Variable name `$pId` collides with read-only `$PID` | PowerShell variables are case-insensitive; assigning `$pId = ...` throws `SessionStateUnauthorizedAccessException`. Use `$owningPid`, `$targetPid`, or `$procId` |

---

## References

- `references/omniroute-watchdog-case-study.md` — Full reproduction of the OmniRoute watchdog fix (this session)
- `references/9router-watchdog-comparison.md` — Comparison with 9Router watchdog patterns