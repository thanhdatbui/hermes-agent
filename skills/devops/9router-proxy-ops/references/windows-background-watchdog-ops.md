# Windows Background Watchdog & Silent Execution for 9Router / OmniRoute

## Architecture & Startup Structure

Both services are configured to run silently in the background without taskbar windows or console dialogs:

| Service | Port | Startup VBS (`shell:startup`) | Supervisor Script | Main Entry |
|---|---|---|---|---|
| **9Router** | `:20128` | `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\9router.vbs` | `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1` | `node.exe server.js` |
| **OmniRoute** | `:20129` | `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\omniroute_watchdog.vbs` | `C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1` | `node.exe scripts/dev/run-next.mjs start` |

The VBS wrappers launch PowerShell with `-WindowStyle Hidden`, and the watchdog scripts start Node with `CreateNoWindow = $true` and `WindowStyle = Hidden`.

---

## Symptom: Visible CMD / Terminal Window on Taskbar

If an OmniRoute or 9Router window appears on the taskbar:
- The service is usually **already running hidden** under its background watchdog.
- A secondary manual foreground terminal (`cmd.exe /k cd /d C:\Users\Kibe\OmniRoute && set PORT=20129 && npm run dev`) was launched from Explorer/Desktop.

### Diagnosis & Fix:

1. **Check listening ports and PIDs**:
   ```bash
   netstat -ano | grep 2012
   ```

2. **Inspect process hierarchy**:
   ```bash
   wmic process where "Name like 'cmd%' or Name like 'node%' or Name like 'power%'" get ProcessId,ParentProcessId,Name,CommandLine
   ```
   - Watchdog-supervised background Node process will have a parent PowerShell process running `*watchdog.ps1`.
   - Visible window will be a `cmd.exe` process (often parented by `explorer.exe`).

3. **Terminate only the visible foreground CMD window**:
   ```bash
   cmd.exe /c "taskkill /F /PID <cmd_pid>"
   ```

4. **Verify background service health**:
   ```bash
   curl -s http://127.0.0.1:20129/api/health
   curl -s http://127.0.0.1:20128/api/health
   ```
