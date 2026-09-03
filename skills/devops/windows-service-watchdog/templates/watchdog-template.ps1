# Windows Service Watchdog Template

**Usage**: Copy this file, replace `<PLACEHOLDERS>`, and save as `<service>_watchdog.ps1`

```powershell
<#
.SYNOPSIS
    Resilient watchdog for <ServiceName> on port <PORT>.
    Enforces single instance, cleans up child processes, implements failure thresholds.
#>

$ErrorActionPreference = "SilentlyContinue"

# === CONFIGURATION (REPLACE THESE) ===
$Port = <PORT>                          # e.g., 20129
$HostAddr = "127.0.0.1"
$NodeExe = "C:\Program Files\nodejs\node.exe"
$AppDir = "<ABSOLUTE_PATH_TO_APP_DIR>"  # e.g., C:\Users\Kibe\OmniRoute
$Launcher = "<LAUNCHER_SCRIPT>"         # e.g., scripts/dev/run-next.mjs
$LogDir = "C:\Users\Kibe\AppData\Roaming\<service>\logs"
$LogFile = Join-Path $LogDir "watchdog.log"
$StopFile = "C:\Users\Kibe\AppData\Roaming\<service>\watchdog.stop"
$MutexName = "Local\<ServiceName>_Supervisor_Mutex_v1"

# Thresholds (tune per service)
$CheckIntervalSec = 10
$MaxConsecutiveFailures = 3
$MaxStartupWaitSec = 30
$StartupPollIntervalSec = 3

# Environment variables for the service process
$EnvVars = @{
    "PORT" = "$Port"
    # Add service-specific env vars here
}

# === END CONFIGURATION ===

if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log([string]$Message) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    try {
        if ((Test-Path -LiteralPath $LogFile) -and ((Get-Item -LiteralPath $LogFile).Length -gt 2MB)) {
            Move-Item -LiteralPath $LogFile -Destination ($LogFile + ".old") -Force
        }
        Add-Content -LiteralPath $LogFile -Value "[$timestamp] $Message" -Encoding UTF8
    } catch {}
}

# Single-instance mutex
$mutex = $null
$createdNew = $false
try {
    $mutex = New-Object System.Threading.Mutex($true, $MutexName, [ref]$createdNew)
    if (-not $createdNew) {
        Write-Log "Another <ServiceName> watchdog instance is already running. Exiting duplicate."
        exit 0
    }
} catch {
    Write-Log "Mutex initialization failed: $_"
}

function Test-ServiceAlive {
    $tcp = $null
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $async = $tcp.BeginConnect($HostAddr, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1500, $false) -or -not $tcp.Connected) {
            return $false
        }
        $tcp.EndConnect($async)
        $tcp.Close()
        $tcp = $null

        # REPLACE: Use your service's actual health endpoint
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://${HostAddr}:${Port}/api/health" -TimeoutSec 5
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    } finally {
        if ($tcp) { try { $tcp.Close() } catch {} }
    }
}

function Get-ServiceProcesses {
    $processes = [System.Collections.Generic.List[PSObject]]::new()
    try {
        # 1. Find processes by command line signature
        $nodes = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*$Launcher*" }
        if ($nodes) {
            foreach ($node in $nodes) { $processes.Add($node) }
            # 2. Find child processes
            $nodePids = @($nodes | ForEach-Object { [int]$_.ProcessId })
            if ($nodePids.Count -gt 0) {
                $children = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                    Where-Object { $nodePids -contains [int]$_.ParentProcessId }
                if ($children) { foreach ($child in $children) { $processes.Add($child) } }
            }
        }

        # 3. Check port ownership
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                $pId = [int]$conn.OwningProcess
                if ($pId -gt 0 -and $pId -ne $PID) {
                    $p = Get-CimInstance Win32_Process -Filter "ProcessId = $pId" -ErrorAction SilentlyContinue
                    if ($p -and ($p.Name -eq "node.exe" -or $p.CommandLine -like "*$Launcher*")) {
                        $processes.Add($p)
                    }
                }
            }
        }
    } catch {
        Write-Log "Error querying <ServiceName> processes: $_"
    }

    # Deduplicate by ProcessId
    $uniqueMap = @{}
    $result = [System.Collections.Generic.List[PSObject]]::new()
    foreach ($item in $processes) {
        if (-not $uniqueMap.ContainsKey($item.ProcessId)) {
            $uniqueMap[$item.ProcessId] = $true
            $result.Add($item)
        }
    }
    return $result
}

function Stop-ServiceProcesses {
    $procs = Get-ServiceProcesses
    if (-not $procs -or $procs.Count -eq 0) { return }

    Write-Log "Terminating $($procs.Count) existing <ServiceName> process(es)..."
    foreach ($proc in $procs) {
        try {
            Write-Log "Stopping PID $($proc.ProcessId) ($($proc.Name))..."
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Log "Failed to stop PID $($proc.ProcessId): $_"
        }
    }

    # Wait up to 5s for full exit
    $timeout = 5
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $timeout) {
        $remaining = Get-ServiceProcesses
        if (-not $remaining -or $remaining.Count -eq 0) { break }
        Start-Sleep -Milliseconds 500
    }
    $stopwatch.Stop()

    $remaining = Get-ServiceProcesses
    if ($remaining -and $remaining.Count -gt 0) {
        Write-Log "Warning: $($remaining.Count) process(es) still lingering (PIDs: $(($remaining | ForEach-Object { $_.ProcessId }) -join ', '))."
    } else {
        Write-Log "All existing <ServiceName> processes stopped cleanly."
    }
}

function Start-Service {
    if (Test-ServiceAlive) {
        Write-Log "<ServiceName> is already UP and healthy on port $Port. Skipping start."
        return $true
    }

    Stop-ServiceProcesses
    Start-Sleep -Seconds 1

    Write-Log "<ServiceName> unavailable on port $Port. Starting production runtime..."
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $NodeExe
        $psi.Arguments = "$Launcher start"
        $psi.WorkingDirectory = $AppDir
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
        $psi.CreateNoWindow = $true
        $psi.UseShellExecute = $false
        foreach ($kv in $EnvVars.GetEnumerator()) {
            $psi.EnvironmentVariables[$kv.Key] = $kv.Value
        }

        $process = [System.Diagnostics.Process]::Start($psi)
        if (-not $process) {
            Write-Log "Failed to launch <ServiceName> process (Process.Start returned null)."
            return $false
        }

        $startedPid = $process.Id
        Write-Log "Started <ServiceName> launcher PID $startedPid; waiting for health (grace: up to $MaxStartupWaitSec s)..."

        $healthy = $false
        $elapsed = 0
        while ($elapsed -lt $MaxStartupWaitSec) {
            Start-Sleep -Seconds $StartupPollIntervalSec
            $elapsed += $StartupPollIntervalSec

            if ($process.HasExited) {
                Write-Log "<ServiceName> process (PID $startedPid) exited prematurely with exit code $($process.ExitCode) after $elapsed seconds."
                return $false
            }

            if (Test-ServiceAlive) {
                $healthy = $true
                Write-Log "<ServiceName> is UP and healthy on port $Port (ready in $elapsed seconds, PID $startedPid)."
                break
            } else {
                Write-Log "<ServiceName> PID $startedPid initializing... (${elapsed}s/${MaxStartupWaitSec}s)"
            }
        }

        if (-not $healthy) {
            Write-Log "<ServiceName> launch did not become healthy within $MaxStartupWaitSec seconds (PID $startedPid)."
            return $false
        }
        return $true
    } catch {
        Write-Log "Failed to launch <ServiceName>: $_"
        return $false
    }
}

Write-Log "<ServiceName> watchdog active; monitoring port $Port (threshold: $MaxConsecutiveFailures failures, check: ${CheckIntervalSec}s, startup grace: ${MaxStartupWaitSec}s)."

$consecutiveFailures = 0

try {
    # Boot-time check
    if (-not (Test-ServiceAlive)) {
        Write-Log "<ServiceName> not responding at watchdog startup. Starting..."
        $null = Start-Service
    } else {
        Write-Log "<ServiceName> is currently active and healthy on port $Port."
    }

    while ($true) {
        if (Test-Path -LiteralPath $StopFile) {
            Remove-Item -LiteralPath $StopFile -Force
            Write-Log "Stop signal detected; watchdog exiting."
            break
        }

        $alive = Test-ServiceAlive
        if ($alive) {
            if ($consecutiveFailures -gt 0) {
                Write-Log "<ServiceName> health check passed. Resetting failure counter (was $consecutiveFailures)."
            }
            $consecutiveFailures = 0
        } else {
            $consecutiveFailures++
            Write-Log "<ServiceName> health check failed ($consecutiveFailures/$MaxConsecutiveFailures)."

            if ($consecutiveFailures -ge $MaxConsecutiveFailures) {
                Write-Log "Consecutive failure threshold reached ($consecutiveFailures/$MaxConsecutiveFailures). Restarting <ServiceName>..."
                $restartOk = Start-Service
                $consecutiveFailures = 0
                if (-not $restartOk) {
                    Write-Log "<ServiceName> restart attempt failed; watchdog will continue monitoring."
                }
            }
        }

        Start-Sleep -Seconds $CheckIntervalSec
    }
} finally {
    if ($mutex) {
        try { $mutex.ReleaseMutex(); $mutex.Dispose() } catch {}
    }
    Write-Log "<ServiceName> watchdog stopped."
}
```

---

## Quick Customization Checklist

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `<PORT>` | `20129` | Service port |
| `<ServiceName>` | `OmniRoute` | Display name in logs |
| `<ABSOLUTE_PATH_TO_APP_DIR>` | `C:\Users\Kibe\OmniRoute` | Working dir for process |
| `<LAUNCHER_SCRIPT>` | `scripts/dev/run-next.mjs` | Relative to AppDir |
| `<service>` (in paths) | `omniroute` | Lowercase, no spaces |
| Health endpoint | `/api/health` | Update in `Test-ServiceAlive` |
| `$EnvVars` hashtable | Add service-specific vars | Copy from your launch config |
| `$MaxStartupWaitSec` | `30` | Next.js cold = 30s, simple Node = 10s |
| `$MaxConsecutiveFailures` | `3` | Adjust for flakiness tolerance |