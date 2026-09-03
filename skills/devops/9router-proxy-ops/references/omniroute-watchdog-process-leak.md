# OmniRoute Watchdog Process Leak — Runbook

**Symptom**: Dashboard inaccessible from LAN (`192.168.x.x:20129`), `curl` hangs or times out. `netstat` shows port 20129 LISTENING but many `ESTABLISHED` connections from LAN clients that never complete.

**Root cause**: The watchdog script (`C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`) only checks TCP port + `/api/health` HTTP 200. When Node (`scripts/dev/run-next.mjs start`) is slow to bind (8s wait in script) or the health endpoint is slow under load, the watchdog treats it as "down" and spawns a **new Node process** every 10s. Each spawn leaves the previous process orphaned (still holding memory, not listening on port). After hours → **40+ node.exe processes**, 16-18GB RAM, machine thrashing.

**Evidence**:
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run-next.mjs*' } | Measure-Object
# Count = 42 (all zombie)
```

**Fix sequence**:
1. Kill watchdog parent: `Stop-Process -Id <watchdog_PID> -Force` (find via `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*omniroute_watchdog.ps1*' }`)
2. Kill all zombie nodes: `Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -like '*run-next.mjs*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }`
3. Verify port free: `netstat -ano | findstr :20129` → should be empty
4. Relaunch watchdog cleanly:
```powershell
powershell -Command "$psi=New-Object System.Diagnostics.ProcessStartInfo; $psi.FileName='powershell.exe'; $psi.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1'; $psi.WindowStyle=[System.Diagnostics.ProcessWindowStyle]::Hidden; $psi.CreateNoWindow=$true; $psi.UseShellExecute=$true; [System.Diagnostics.Process]::Start($psi)"
```
5. Wait 15s, verify: `curl -s http://127.0.0.1:20129/api/health` → `{"status":"ok"...}`

**Long-term fix needed in watchdog**: Before spawning, check if a `run-next.mjs` process already exists (by command line). Only spawn if truly zero instances. Current logic only checks port ownership, which races with slow startup.

**Related paths**:
- Watchdog: `C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`
- Logs: `C:\Users\Kibe\AppData\Roaming\omniroute\logs\watchdog.log`
- Launcher: `C:\Users\Kibe\OmniRoute\scripts\dev\run-next.mjs`
- 9Router watchdog (similar pattern, port 20128): `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1`