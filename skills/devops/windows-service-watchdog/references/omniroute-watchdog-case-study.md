# OmniRoute Watchdog Fix — Case Study

**Session**: Fix C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1 (2026-09-02)

---

## Problem State (Before Fix)

### Symptoms
- Multiple `node.exe` processes running `scripts/dev/run-next.mjs start` accumulating over time
- Multiple watchdog PowerShell instances running simultaneously (Startup VBS + manual launches)
- Port 20129 served by orphaned/stale processes while watchdog kept spawning new ones
- Fixed 8-second startup timeout too short for cold Next.js Turbopack builds (frequent "did not become healthy within 8 seconds")
- No consecutive failure threshold — single health check failure triggered immediate restart attempt
- No process cleanup before restart — old processes left running

### Evidence from Logs (watchdog.log)
```
[2026-09-01 04:11:25] OmniRoute unavailable... Starting... PID 109608
[2026-09-01 04:11:34] ...did not become healthy within 8 seconds
[2026-09-01 04:11:46] OmniRoute unavailable... Starting... PID 111308  (NEW process, old still running!)
[2026-09-01 04:11:55] ...did not become healthy within 8 seconds
```
> **Root cause**: Watchdog didn't kill previous failed process before starting new one.

---

## Fix Applied

### 1. Mutex Single-Instance Enforcement
```powershell
$MutexName = "Local\OmniRoute_Supervisor_Mutex_v1"
$mutex = New-Object System.Threading.Mutex($true, $MutexName, [ref]$createdNew)
if (-not $createdNew) {
    Write-Log "Another OmniRoute watchdog instance is already running. Exiting duplicate."
    exit 0
}
```

### 2. Comprehensive Process Discovery (`Get-OmniRouteProcesses`)
```powershell
function Get-OmniRouteProcesses {
    $processes = [System.Collections.Generic.List[PSObject]]::new()
    # 1. Find node processes by command line signature
    $nodes = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" |
        Where-Object { $_.CommandLine -like "*$Launcher*" -or $_.CommandLine -like "*run-next.mjs*" }
    # 2. Find children by ParentProcessId
    $nodePids = @($nodes | ForEach-Object { [int]$_.ProcessId })
    $children = Get-CimInstance Win32_Process |
        Where-Object { $nodePids -contains [int]$_.ParentProcessId }
    # 3. Check port ownership (Get-NetTCPConnection)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen
    # Return deduplicated by ProcessId
}
```

### 3. Clean Termination with Grace Period (`Stop-OmniRouteProcesses`)
```powershell
function Stop-OmniRouteProcesses {
    $procs = Get-OmniRouteProcesses
    foreach ($proc in $procs) { Stop-Process -Id $proc.ProcessId -Force }
    # Wait up to 5s for full exit
    $timeout = 5; $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $timeout) {
        $remaining = Get-OmniRouteProcesses
        if (-not $remaining -or $remaining.Count -eq 0) { break }
        Start-Sleep -Milliseconds 500
    }
}
```

### 4. Configurable Thresholds & Intervals
```powershell
$CheckIntervalSec = 10
$MaxConsecutiveFailures = 3      # 30s of failures before restart
$MaxStartupWaitSec = 30          # Up to 30s for cold start
$StartupPollIntervalSec = 3      # Check every 3s
```

### 5. Startup Grace Polling with Progress Logging
```powershell
$elapsed = 0
while ($elapsed -lt $MaxStartupWaitSec) {
    Start-Sleep -Seconds $StartupPollIntervalSec
    $elapsed += $StartupPollIntervalSec
    if ($process.HasExited) { Write-Log "...exited prematurely"; return $false }
    if (Test-OmniRouteAlive) { Write-Log "...UP and healthy (ready in $elapsed s)"; return $true }
    Write-Log "OmniRoute PID $startedPid initializing... (${elapsed}s/${MaxStartupWaitSec}s)"
}
```

### 6. Pre-Start Health Check
```powershell
if (Test-OmniRouteAlive) {
    Write-Log "OmniRoute is already UP and healthy. Skipping start."
    return $true
}
```

### 7. Consecutive Failure Logic
```powershell
$consecutiveFailures = 0
while ($true) {
    $alive = Test-OmniRouteAlive
    if ($alive) { $consecutiveFailures = 0 }
    else {
        $consecutiveFailures++
        if ($consecutiveFailures -ge $MaxConsecutiveFailures) {
            $restartOk = Start-OmniRoute
            $consecutiveFailures = 0  # Reset after attempt
        }
    }
    Start-Sleep -Seconds $CheckIntervalSec
}
```

---

## Verification Results (Live)

### After Fix Deployment
```
=== NODE PROCESSES ===
ProcessId ParentProcessId CommandLine
178124    238032          "C:\Program Files\nodejs\node.exe" scripts/dev/run-next.mjs start
# EXACTLY 1 OmniRoute process

=== WATCHDOG PROCESSES ===
ProcessId ParentProcessId CommandLine
238032    178320          "...omniroute_watchdog.ps1"
# EXACTLY 1 watchdog process

=== PORT OWNERSHIP ===
LocalAddress LocalPort OwningProcess
0.0.0.0      20129       178124
# Single process owns the port

=== HEALTH CHECK ===
Status: 200
```

### Recovery Test (Kill Process → Watchdog Recovers)
```
[2026-09-02 14:15:27] OmniRoute health check failed (1/3)
[2026-09-02 14:15:38] OmniRoute health check failed (2/3)
[2026-09-02 14:15:50] OmniRoute health check failed (3/3)
[2026-09-02 14:15:50] Consecutive failure threshold reached (3/3). Restarting OmniRoute...
[2026-09-02 14:15:54] Started OmniRoute launcher PID 178124; waiting for health check...
[2026-09-02 14:16:16] OmniRoute is UP and healthy on port 20129 (ready in 15 seconds, PID 178124)
```

### Duplicate Watchdog Prevention Test
```
[2026-09-02 14:22:21] Another OmniRoute watchdog instance is already running. Exiting duplicate.
```

---

## Key Takeaways

1. **Always discover by command-line signature + port ownership + child processes** — PID alone is fragile
2. **Mutex on `Local\` namespace** prevents both Startup folder and manual launches from colliding
3. **Consecutive failure threshold (3 × 10s = 30s)** filters transient network blips
4. **30s startup grace with 3s polling** handles cold Next.js/Turbopack builds
5. **Log every state transition** with timestamps and PIDs for post-mortem verification
6. **Stop file pattern** (`watchdog.stop`) enables graceful shutdown from external triggers