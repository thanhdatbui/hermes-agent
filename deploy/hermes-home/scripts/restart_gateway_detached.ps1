# Wait 5 seconds so Hermes Gateway finishes sending the Telegram response
Start-Sleep -Seconds 5

$logFile = "C:\Users\Kibe\AppData\Local\hermes\logs\restart_gateway.log"
$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
"[$timestamp] Starting detached gateway restart sequence..." | Out-File -FilePath $logFile -Append -Encoding utf8

# Kill old gateway processes
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*gateway run*" -and ($_.Name -like "*python*" -or $_.Name -like "*pythonw*") }
foreach ($p in $procs) {
    "[$timestamp] Stopping process $($p.ProcessId) ($($p.Name))..." | Out-File -FilePath $logFile -Append -Encoding utf8
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# Sync config from repo to AppData
"[$timestamp] Syncing config.yaml from deploy repo..." | Out-File -FilePath $logFile -Append -Encoding utf8
$srcCfg = "D:\Taadaa\Hermes\deploy\hermes-home\config.yaml"
$dstCfg = "C:\Users\Kibe\AppData\Local\hermes\config.yaml"
if ((Test-Path $dstCfg) -and ((Get-FileHash $srcCfg).Hash -ne (Get-FileHash $dstCfg).Hash)) {
    "[$timestamp] WARNING: runtime config differs from repo template; backing up to config.yaml.bak and logging diff." | Out-File -FilePath $logFile -Append -Encoding utf8
    Copy-Item $dstCfg "$dstCfg.bak" -Force
    Compare-Object (Get-Content $dstCfg) (Get-Content $srcCfg) | Out-String | Out-File -FilePath $logFile -Append -Encoding utf8
}
Copy-Item $srcCfg $dstCfg -Force

# Launch fresh gateway via official VBS wrapper
"[$timestamp] Spawning fresh gateway via Hermes_Gateway.vbs..." | Out-File -FilePath $logFile -Append -Encoding utf8
Start-Process wscript.exe "C:\Users\Kibe\AppData\Local\hermes\gateway-service\Hermes_Gateway.vbs"
"[$timestamp] Restart script completed successfully." | Out-File -FilePath $logFile -Append -Encoding utf8
