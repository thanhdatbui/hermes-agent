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

# Launch fresh gateway via official VBS wrapper
"[$timestamp] Spawning fresh gateway via Hermes_Gateway.vbs..." | Out-File -FilePath $logFile -Append -Encoding utf8
Start-Process wscript.exe "C:\Users\Kibe\AppData\Local\hermes\gateway-service\Hermes_Gateway.vbs"
"[$timestamp] Restart script completed successfully." | Out-File -FilePath $logFile -Append -Encoding utf8
