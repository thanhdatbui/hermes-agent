# ONE-SHOT Watcher: Tu dong restart Hermes Gateway khi toan bo session AI idle
Remove-Item Env:\_HERMES_GATEWAY -ErrorAction SilentlyContinue
$env:_HERMES_GATEWAY = $null

$stateFile = "C:\Users\Kibe\AppData\Local\hermes\gateway_state.json"
$logFile   = "C:\Users\Kibe\AppData\Local\hermes\logs\idle_restart.log"
$defaultPythonw = "C:\Users\Kibe\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\pythonw.exe"

function Log-Msg($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$timestamp] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

Log-Msg "Bắt đầu ONE-SHOT watcher tự động restart Gateway khi idle (PID watcher: $PID)..."

$requiredIdleChecks = 8   # 8 lần kiểm tra liên tiếp x 2s = 16 giây
$idleCount = 0
$cachedPythonw = $null

while ($true) {
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

    # Cache duong dan executable cua gateway neu chua co
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
        Log-Msg "Phát hiện idle ($idleCount/$requiredIdleChecks)..."
        if ($idleCount -ge $requiredIdleChecks) {
            Log-Msg "Gateway idle liên tục 16s. Thực hiện restart..."

            $pythonwExe = $cachedPythonw
            if (!$pythonwExe) {
                try {
                    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
                    if ($procInfo -and $procInfo.ExecutablePath) {
                        $pythonwExe = $procInfo.ExecutablePath
                    }
                } catch {}
            }
            if (!$pythonwExe) {
                $pythonwExe = $defaultPythonw
            }

            # Stop tiến trình gateway hiện tại
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            } catch {}

            # Chờ 2 giây
            Start-Sleep -Seconds 2

            # Khởi động lại Gateway bằng Start-Process
            Start-Process $pythonwExe -ArgumentList "-m hermes_cli.main gateway run" -WindowStyle Hidden

            Log-Msg "Gateway đã được khởi động lại thành công. Watcher kết thúc."
            exit 0
        }
    } else {
        if ($idleCount -gt 0) {
            Log-Msg "Phát hiện active agents ($activeWork) hoặc gateway_state ($gwState). Reset bộ đếm về 0."
        }
        $idleCount = 0
    }
}
