# Kill all orphaned GPM Chrome and driver processes safely without touching CDP 9222
Get-Process | Where-Object { $_.ProcessName -match 'gpmdriver|chromedriver' } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match 'GPMLogin|--remote-debugging-port' -and $_.CommandLine -notmatch '9222' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "Cleaned all orphaned GPM Chrome processes."
