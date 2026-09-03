Start-Sleep -Seconds 3
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*gateway run*" -and $_.Name -like "*python*" }
foreach ($p in $procs) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Start-Process wscript.exe "C:\Users\Kibe\AppData\Local\hermes\gateway-service\Hermes_Gateway.vbs"
