# Delayed Gateway Restart (Detached)
# Tu dong restart Hermes Gateway detached sau khi hoan tat phan hoi Telegram
Remove-Item Env:\_HERMES_GATEWAY -ErrorAction SilentlyContinue

$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }
$stateFile  = Join-Path $hermesHome "gateway_state.json"
$logFile    = Join-Path $hermesHome "logs\idle_restart.log"

function Log-Msg($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$timestamp] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

# Tim interpreter pythonw phu hop (uu tien venv hermes, sau do den PATH va uv)
$pythonwCandidates = @(
    (Join-Path $hermesHome "hermes-agent\venv\Scripts\pythonw.exe"),
    (Join-Path $env:APPDATA "uv\python\cpython-3.11-windows-x86_64-none\pythonw.exe")
)
$resolvedPythonw = $null
foreach ($cand in $pythonwCandidates) {
    if (Test-Path $cand) {
        $resolvedPythonw = $cand
        break
    }
}
if (!$resolvedPythonw) {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd -and (Test-Path $cmd.Source)) {
        $resolvedPythonw = $cmd.Source
    }
}

if (!$resolvedPythonw -or !(Test-Path $resolvedPythonw)) {
    Log-Msg "Loi nghiem trong: Khong tim thay interpreter pythonw.exe hop le tren he thong. Huy bo restart."
    exit 1
}

Log-Msg "=== Kich hoat delayed-restart.ps1 (PID: $PID) - Cho 6s de Gateway hoan tat phan hoi turn hien tai ==="
Start-Sleep -Seconds 6

$targetPid = $null
if (Test-Path $stateFile) {
    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        $targetPid = $state.pid
    } catch {}
}

# Neu khong doc duoc tu state.db, tim tien trinh gateway run qua CIM
if (!$targetPid) {
    $gwProc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { 
        $_.Name -like "pythonw*" -and $_.CommandLine -like "*gateway*run*" 
    } | Select-Object -First 1
    if ($gwProc) {
        $targetPid = $gwProc.ProcessId
    }
}

if ($targetPid) {
    Log-Msg "Dang kiem tra va dung Gateway cu (PID: $targetPid)..."
    try {
        $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
        if ($procInfo -and ($procInfo.CommandLine -like "*gateway*run*" -or $procInfo.Name -like "pythonw*")) {
            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            Log-Msg "Da gui lenh dung Gateway PID: $targetPid."
        } else {
            Log-Msg "Canh bao: PID $targetPid khong phai Gateway hop le, bo qua kill."
        }
    } catch {
        Log-Msg "Loi khi dung process ${targetPid}: $_"
    }
} else {
    Log-Msg "Khong tim thay Gateway PID cu de dung, tiep tuc khoi dong moi."
}

Start-Sleep -Seconds 2

Log-Msg "Dang khoi dong lai Gateway bang $resolvedPythonw..."
try {
    $argsList = @("-m", "hermes_cli.main", "gateway", "run")
    $newProc = Start-Process $resolvedPythonw -ArgumentList $argsList -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    if ($newProc -and !$newProc.HasExited) {
        Log-Msg "Gateway da duoc khoi dong lai thanh cong tu delayed-restart.ps1 (PID moi: $($newProc.Id))."
        exit 0
    } else {
        Log-Msg "Loi: Tien trinh Gateway moi da thoat som sau khi start."
        exit 1
    }
} catch {
    Log-Msg "Loi khi khoi dong lai Gateway: $_"
    exit 1
}
