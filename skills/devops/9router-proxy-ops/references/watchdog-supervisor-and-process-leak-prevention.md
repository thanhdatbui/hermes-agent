# Watchdog Supervisor & Process Accumulation Prevention (9Router & OmniRoute)

## Context & Architecture
9Router (`:20128`) and OmniRoute (`:20129`) run as long-lived Node.js services supervised by Windows PowerShell watchdogs:
- 9Router watchdog: `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1`
- OmniRoute watchdog: `C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`
- Canonical tool configs & supervisor scripts repository: `D:\OneDrive\AI-Tools\tools\omniroute\` and `D:\OneDrive\AI-Tools\tools\9router\`

## Root Cause of Process Accumulation Storms
When a service takes time to start (e.g. Next.js building/loading chunks) or temporarily slows down under heavy load, health checks (`/api/health`) may timeout or fail for several seconds.
A naive watchdog that checks port/health every 10s and immediately spawns a new `node.exe` process without checking whether existing Node processes are already running causes:
1. Multiple Node processes running concurrently, fighting over ports and SQLite database files.
2. Exponential memory leak / thrashing (e.g. 40+ Node instances taking 16-18GB RAM).
3. Total server freeze and network unavailability on LAN/IP interfaces.

## Watchdog Invariants
Every supervisor script MUST enforce:
1. **Single-Instance Mutex:** Use `System.Threading.Mutex` so duplicate watchdog scripts exit immediately.
2. **AppDir Pre-Flight Guard:** Validate `Test-Path $AppDir` before attempting process launch. If missing, log error and abort start rather than entering an infinite spawn loop.
3. **Pre-spawn Process Inspection:** Before calling `Start-Process`, query existing Node processes by command line (`run-next.mjs` / `server.js`).
4. **Clean Termination Before Restart:** If a service is deemed unresponsive, all old/hung child processes and port-holding PIDs must be terminated cleanly (with grace period before SIGKILL) BEFORE launching a new instance.
5. **Consecutive Failure Threshold:** Require at least 3 consecutive failed health probes (e.g. 3 x 10s = 30s) before declaring the service dead.
6. **Adequate Startup Grace Period:** After launching a new process, poll `/api/health` with a realistic timeout (e.g. 30 seconds, polling every 3s) rather than immediately failing in 8 seconds.

## Canonical Launcher References
- **9Router launcher:** `tools/9router/9router.vbs` (invokes `%APPDATA%\9router\9router_watchdog.ps1`). Startup shortcut should point to `9router.vbs`.
- **OmniRoute launcher:** `tools/omniroute/omniroute_watchdog.vbs` (invokes `%APPDATA%\omniroute\omniroute_watchdog.ps1`). Startup shortcut points to `omniroute_watchdog.vbs`.

## Tool Config Sync Invariant
Whenever modifying supervisor scripts, proxy configs, or startup launchers in `AppData\Roaming\...`, ALWAYS mirror/sync changes into `D:\OneDrive\AI-Tools\tools\<tool-name>\` so configurations are tracked in the AI-Tools repository.
