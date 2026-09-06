# ONE-SHOT Watcher: Tu dong restart Hermes Gateway khi toan bo session AI idle
Remove-Item Env:\_HERMES_GATEWAY -ErrorAction SilentlyContinue
$env:_HERMES_GATEWAY = $null

$hermesHome = Join-Path $env:LOCALAPPDATA "hermes"
$stateFile = Join-Path $hermesHome "gateway_state.json"
$logFile   = Join-Path $hermesHome "logs\idle_restart.log"
$defaultPythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (!$defaultPythonw) {
    $defaultPythonw = Join-Path $hermesHome "hermes-agent\venv\Scripts\pythonw.exe"
}

function Log-Msg($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$timestamp] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

Log-Msg "=== Bat dau ONE-SHOT Watcher restart Hermes Gateway khi idle (PID: $PID) ==="

$requiredIdleChecks = 6 # 6 lan x 2s = 12 giay khong co turn AI nao
$idleCount = 0
$cachedPythonw = $null
$maxWaitSeconds = 10800 # 3 tieng timeout
$startTime = [DateTime]::UtcNow

while ($true) {
    if (([DateTime]::UtcNow - $startTime).TotalSeconds -gt $maxWaitSeconds) {
        Log-Msg "Het thoi gian cho ($maxWaitSeconds giay) - Huy bo restart."
        exit 1
    }

    Start-Sleep -Seconds 2

    if (!(Test-Path $stateFile)) {
        continue
    }

    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        $targetPid = $state.pid
        $activeWork = [int]$state.active_agents
        $gwState = $state.gateway_state
    } catch {
        continue
    }

    if (!$cachedPythonw -and $targetPid) {
        try {
            $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
            if ($procInfo -and $procInfo.ExecutablePath) {
                $cachedPythonw = $procInfo.ExecutablePath
            }
        } catch {}
    }

    if ($gwState -eq "running" -and $activeWork -eq 0) {
        $idleCount++
        Log-Msg "Phat hien Gateway idle ($idleCount/$requiredIdleChecks)..."
        if ($idleCount -ge $requiredIdleChecks) {
            Log-Msg "Gateway idle lien tuc 12s. Thuc hien restart..."

            $pythonwExe = $cachedPythonw
            if (!$pythonwExe) {
                $pythonwExe = $defaultPythonw
            }

            # Dung gateway cu
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            } catch {}

            Start-Sleep -Seconds 2

            # Khoi dong lai Gateway
            Start-Process $pythonwExe -ArgumentList "-m hermes_cli.main gateway run" -WindowStyle Hidden

            Log-Msg "Gateway da duoc khoi dong lai thanh cong. Watcher ket thuc."
            exit 0
        }
    } else {
        if ($idleCount -gt 0) {
            Log-Msg "Phat hien active work ($activeWork agents). Reset bo dem..."
        }
        $idleCount = 0
    }
}
