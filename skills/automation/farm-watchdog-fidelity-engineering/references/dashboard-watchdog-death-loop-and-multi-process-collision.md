# Multi-Process Socket Collision & Watchdog Death-Loop on Large SQLite Dashboards

## 1. Context & Incident Overview (2026-10-29)
When a local web dashboard (`tiktok_dashboard.py` on port 1905) serving heavy SQLite aggregations (>130k snapshot rows) is guarded by a PowerShell background watchdog (`tiktok_dashboard_watchdog.ps1`), an aggressive health-check combined with multi-process socket binding (`SO_REUSEADDR`) can cause catastrophic service flapping and connection timeouts.

---

## 2. Core Root Causes

### 1. Incomplete Process Tree Termination on Windows (`pythonw.exe` vs `python.exe`)
- In Python virtual environments on Windows, launching via `pythonw.exe` creates a lightweight shim launcher that spawns the real base `python.exe`.
- When a PowerShell watchdog attempts to kill the stuck listener via `Get-NetTCPConnection -LocalPort 1905` and `Stop-Process -Id $_.OwningProcess`, it only terminates the child process holding the socket. The parent `pythonw.exe` remains alive.
- When the watchdog relaunches the service via a VBS wrapper (`start_tiktok_dashboard_hidden.vbs`), new instances of `pythonw.exe` and `python.exe` are created.

### 2. Multi-Process `SO_REUSEADDR` Socket Hijacking
- `ThreadingHTTPServer` on Python sets `allow_reuse_address = True` (`SO_REUSEADDR`).
- On Windows, multiple processes can call `bind()` on the exact same port (1905).
- Windows nondeterministically routes incoming TCP handshakes among the listening sockets. If one process is in a deadlock, zombie, or un-serviced state, all requests routed to its socket hang until client timeout.

### 3. Aggressive Watchdog Health-Check vs Cold-Cache Query Latency & Boot Storm
- When database snapshots grow large (e.g. 130k rows), aggregating historical data with window functions (`ROW_NUMBER() OVER (...)`) takes 4–6+ seconds when cache is cold (and 8–12+ seconds during post-boot I/O contention when 20+ automation runners start simultaneously).
- If the watchdog configures a tight timeout (`$TimeoutSeconds = 8`) and polls an uncached heavy aggregation endpoint (`/api/data` with 15s TTL), any concurrent I/O load causes the health-check to exceed 8s.
- In PowerShell, `.NET WebRequest` without stream draining exhausts the default connection limit (2 connections per host), causing all subsequent checks to fail.
- **Boot Storm Death Loop:** Right after host reset/reboot, the watchdog fires after 60s, hits cold cache + boot I/O spikes, assumes dead, kills the process 3 times in 3 minutes, then enters circuit-breaker sleep (300s). During the entire 10–15 min window post-reset, user access fails (`ERR_CONNECTION_REFUSED` / timed out).

### 4. Domain Isolation Deficit (Farm Automation vs Web Dashboard)
- Farm runners (`run-feed-session.ps1` via `tiktok_runner.py`) and Web Dashboards are 100% decoupled systems.
- When a dashboard service flaps, it does NOT imply farm devices are halted. Similarly, failures in staging/batch pickers (`phase9-staging-picker`) do not impact operational runners that run with *"No picker / manifest dependency"*.

---

## 3. Engineering Invariants & Remediation

1. **Process Tree Kill Protocol:**
   Always terminate the entire process hierarchy matching the application command-line:
   ```python
   for p in psutil.process_iter(['pid', 'name', 'cmdline']):
       if 'tiktok_dashboard.py' in ' '.join(p.info['cmdline'] or []):
           p.kill()
   ```

2. **Deduplicate Startup Launchers:**
   Audit `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` to ensure only one canonical startup shortcut exists. Remove duplicate wrappers (e.g. `start_tiktok_dashboard.vbs` vs `tiktok_dashboard_1905.vbs`).

3. **Cache Duration Alignment for Heavy Read Replicas:**
   Set `_CACHE_TTL` to at least 180s–300s (3–5 minutes) on dashboards aggregating large analytical tables, rather than short 15s expirations.

4. **Watchdog Resilience & Post-Boot Grace Period:**
   - **Lightweight Probe Target:** Watchdog HTTP probes should target a lightweight ping endpoint (e.g. `/` or `/healthz`) rather than expensive multi-second analytical endpoints (`/api/data`). If analytical routes must be probed, timeout must be set to $\ge 25$s.
   - **Boot Grace Period:** When starting via Windows Startup, watchdog must implement an initial boot grace period (`Start-Sleep -Seconds 180` before first check) to allow disk I/O, background runners, and cold cache queries to settle.
   - Always log `$_.Exception.Message` rather than swallowing exceptions in `catch { $isHealthy = $false }`.
   - Implement exponential backoff after restart attempts to avoid rapid flapping.
