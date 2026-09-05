# ONE-SHOT Watcher: Tu dong restart Hermes Gateway khi toan bo session AI idle
Remove-Item Env:\_HERMES_GATEWAY -ErrorAction SilentlyContinue
$env:_HERMES_GATEWAY = $null

$stateFile = "$env:LOCALAPPDATA\hermes\gateway_state.json"
$logFile   = "$env:LOCALAPPDATA\hermes\logs\idle_restart.log"
$defaultPythonw = "$env:APPDATA\uv\python\cpython-3.11-windows-x86_64-none\pythonw.exe"

function Log-Msg($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$timestamp] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

Log-Msg "Bắt đầu ONE-SHOT watcher tự động restart Gateway khi idle (PID watcher: $PID)..."

$requiredIdleChecks = 8   # 8 lần kiểm tra liên tiếp x 2s = 16 giây
$maxWaitSeconds = 600     # Timeout tối đa 10 phút nếu bot bận liên tục
$startTime = [DateTime]::UtcNow
$idleCount = 0
$cachedPythonw = $null

while ($true) {
    if (([DateTime]::UtcNow - $startTime).TotalSeconds -gt $maxWaitSeconds) {
        Log-Msg "HẾT THỜI GIAN CHỜ ($maxWaitSeconds giây) - Gateway không đạt trạng thái idle. Huỷ bỏ restart."
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

            # Stop tiến trình gateway hiện tại và đợi giải phóng tài nguyên
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
                Wait-Process -Id $targetPid -Timeout 10 -ErrorAction SilentlyContinue
            } catch {}

            # Chờ 2 giây đảm bảo file lock giải phóng hoàn toàn
            Start-Sleep -Seconds 2

            # Khởi động lại Gateway bằng Start-Process và kiểm chứng
            $newProc = Start-Process $pythonwExe -ArgumentList "-m hermes_cli.main gateway run" -WindowStyle Hidden -PassThru
            Start-Sleep -Seconds 2
            if ($newProc -and !$newProc.HasExited) {
                Log-Msg "Gateway đã được khởi động lại thành công (PID mới: $($newProc.Id)). Watcher kết thúc."
                exit 0
            } else {
                Log-Msg "CẢNH BÁO: Tiến trình Gateway khởi động thất bại hoặc đã thoát sớm."
                exit 1
            }
        }
    } else {
        if ($idleCount -gt 0) {
            Log-Msg "Phát hiện active agents ($activeWork) hoặc gateway_state ($gwState). Reset bộ đếm về 0."
        }
        $idleCount = 0
    }
}
