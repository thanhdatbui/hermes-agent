# Watchdog Verification Script

**Usage**: Run this script to verify a watchdog + service pair is operating correctly.

```powershell
<#
.SYNOPSIS
    Verify watchdog + service health. Run after deploying a new watchdog or after changes.
    
.DESCRIPTION
    Checks:
    1. PowerShell syntax of watchdog script
    2. Exactly 1 watchdog process running
    3. Exactly 1 service process running (by command-line signature)
    4. Port owned by single service process
    5. Health endpoint returns HTTP 200
    6. Duplicate watchdog prevention works
    7. Auto-recovery after service kill (optional, interactive)
#>

param(
    [string]$WatchdogPath = "C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1",
    [string]$ServiceName = "OmniRoute",
    [int]$Port = 20129,
    [string]$LauncherSignature = "run-next.mjs",
    [string]$HealthEndpoint = "/api/health",
    [switch]$TestRecovery
)

$ErrorActionPreference = "Stop"

function Write-Header($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Pass($msg) { Write-Host "  [PASS] $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }

$allPassed = $true

# 1. Syntax check
Write-Header "1. PowerShell Syntax Check"
try {
    $errors = $null
    $tokens = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile($WatchdogPath, [ref]$tokens, [ref]$errors)
    if ($errors.Count -eq 0) { Write-Pass "Syntax OK (0 errors)" }
    else {
        Write-Fail "Syntax errors: $($errors.Count)"
        $errors | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        $allPassed = $false
    }
} catch {
    Write-Fail "Syntax check failed: $_"
    $allPassed = $false
}

# 2. Watchdog process count
Write-Header "2. Watchdog Process Count"
$watchdogs = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$(Split-Path $WatchdogPath -Leaf)*" -and $_.CommandLine -notlike "*bash*" }
if ($watchdogs.Count -eq 1) {
    Write-Pass "Exactly 1 watchdog process (PID $($watchdogs[0].ProcessId))"
} elseif ($watchdogs.Count -eq 0) {
    Write-Fail "NO watchdog process found!"
    $allPassed = $false
} else {
    Write-Fail "$($watchdogs.Count) watchdog processes found (expected 1):"
    $watchdogs | ForEach-Object { Write-Host "    PID $($_.ProcessId)" -ForegroundColor Red }
    $allPassed = $false
}

# 3. Service process count
Write-Header "3. Service Process Count"
$services = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$LauncherSignature*" }
if ($services.Count -eq 1) {
    Write-Pass "Exactly 1 service process (PID $($services[0].ProcessId))"
} elseif ($services.Count -eq 0) {
    Write-Fail "NO service process found!"
    $allPassed = $false
} else {
    Write-Fail "$($services.Count) service processes found (expected 1):"
    $services | ForEach-Object { Write-Host "    PID $($_.ProcessId) - $($_.CommandLine)" -ForegroundColor Red }
    $allPassed = $false
}

# 4. Port ownership
Write-Header "4. Port Ownership"
$connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $Port }
if ($connections.Count -eq 1) {
    $owner = $connections[0].OwningProcess
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $owner" -ErrorAction SilentlyContinue
    if ($proc -and $services.ProcessId -contains $owner) {
        Write-Pass "Port $Port owned by service PID $owner"
    } else {
        Write-Warn "Port $Port owned by PID $owner (not the expected service process)"
    }
} elseif ($connections.Count -eq 0) {
    Write-Fail "Port $Port NOT LISTENING"
    $allPassed = $false
} else {
    Write-Fail "Port $Port has $($connections.Count) listeners (expected 1)"
    $allPassed = $false
}

# 5. Health endpoint
Write-Header "5. Health Endpoint"
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port$HealthEndpoint" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Pass "HTTP 200 - $($response.Content | ConvertFrom-Json | Select-Object -ExpandProperty status)"
    } else {
        Write-Fail "HTTP $($response.StatusCode)"
        $allPassed = $false
    }
} catch {
    Write-Fail "Health check failed: $_"
    $allPassed = $false
}

# 6. Duplicate prevention
Write-Header "6. Duplicate Watchdog Prevention"
Write-Host "  Launching 2nd watchdog instance..." -NoNewline
$proc = Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $WatchdogPath" -PassThru
Start-Sleep -Seconds 2
$watchdogsAfter = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$(Split-Path $WatchdogPath -Leaf)*" -and $_.CommandLine -notlike "*bash*" }
# Kill the test instance
Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if ($watchdogsAfter.Count -eq 1) {
    Write-Pass " Duplicate correctly rejected (still 1 watchdog)"
} else {
    Write-Fail " Duplicate NOT rejected ($($watchdogsAfter.Count) watchdogs)"
    $allPassed = $false
}

# 7. Auto-recovery test (optional)
if ($TestRecovery) {
    Write-Header "7. Auto-Recovery Test (Kill Service → Watchdog Restarts)"
    if ($services.Count -eq 1) {
        $svcPid = $services[0].ProcessId
        Write-Host "  Killing service PID $svcPid..."
        Stop-Process -Id $svcPid -Force -ErrorAction SilentlyContinue
        
        $maxWait = 60  # 3 failures × 10s + 30s startup
        $started = Get-Date
        $recovered = $false
        
        while ((Get-Date) - $started -lt [TimeSpan]::FromSeconds($maxWait)) {
            Start-Sleep -Seconds 5
            $newServices = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue |
                Where-Object { $_.CommandLine -like "*$LauncherSignature*" }
            if ($newServices.Count -eq 1 -and $newServices[0].ProcessId -ne $svcPid) {
                try {
                    $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port$HealthEndpoint" -TimeoutSec 3
                    if ($resp.StatusCode -eq 200) {
                        Write-Pass " Service recovered (new PID $($newServices[0].ProcessId)) in $([int]((Get-Date) - $started).TotalSeconds)s"
                        $recovered = $true
                        break
                    }
                } catch {}
            }
        }
        
        if (-not $recovered) {
            Write-Fail " Service did NOT recover within ${maxWait}s"
            $allPassed = $false
        }
    }
}

# Summary
Write-Header "SUMMARY"
if ($allPassed) {
    Write-Pass "ALL CHECKS PASSED"
    exit 0
} else {
    Write-Fail "SOME CHECKS FAILED"
    exit 1
}
```

---

## Usage Examples

```powershell
# Basic verification
.\scripts\verify-watchdog.ps1

# With custom parameters for different service
.\scripts\verify-watchdog.ps1 `
  -WatchdogPath "C:\path\to\my_watchdog.ps1" `
  -ServiceName "MyService" `
  -Port 8080 `
  -LauncherSignature "my-server.js" `
  -HealthEndpoint "/health"

# Full test including recovery (takes ~60s)
.\scripts\verify-watchdog.ps1 -TestRecovery
```

---

## Expected Output (All Pass)

```
=== 1. PowerShell Syntax Check ===
  [PASS] Syntax OK (0 errors)

=== 2. Watchdog Process Count ===
  [PASS] Exactly 1 watchdog process (PID 238032)

=== 3. Service Process Count ===
  [PASS] Exactly 1 service process (PID 178124)

=== 4. Port Ownership ===
  [PASS] Port 20129 owned by service PID 178124

=== 5. Health Endpoint ===
  [PASS] HTTP 200 - ok

=== 6. Duplicate Watchdog Prevention ===
  [PASS] Duplicate correctly rejected (still 1 watchdog)

=== SUMMARY ===
  [PASS] ALL CHECKS PASSED
```