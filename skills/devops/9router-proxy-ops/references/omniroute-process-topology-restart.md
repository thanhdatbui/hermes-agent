# OmniRoute Windows Dual-Port Process Topology & Restart Verification

## 1. Port vs Process Architecture on Host
- **Port 20128**: 9Router / Next.js dev routing process (`node.exe server.js` or standalone next).
- **Port 20129**: OmniRoute Core Production Runtime (`node.exe scripts/dev/run-next.mjs start`).
- **Supervision**: Supervised by `omniroute_watchdog.ps1` (PowerShell supervisor with mutex `Local\OmniRoute_Supervisor_Mutex_v1`).

## 2. Common Mistake: Restarting the Wrong Node Process
- Do NOT assume killing `server.js` reloads OmniRoute port 20129.
- `server.js` often binds port 20128 or acts as secondary service.
- The actual active listener for 20129 is `scripts/dev/run-next.mjs start`.

## 3. Strict Verification Sequence for .env / Code Reloads
1. **Identify Listener PID**:
   ```powershell
   Get-NetTCPConnection -LocalPort 20129 -State Listen | Select-Object OwningProcess
   ```
2. **Inspect Process Details**:
   ```powershell
   Get-CimInstance Win32_Process -Filter "ProcessId = <PID>" | Select-Object ProcessId,CreationDate,CommandLine
   ```
3. **Compare Timestamp vs .env Edit Timestamp**:
   - Verify `Process.CreationDate > File.LastWriteTime(.env)`.
   - If `Process.CreationDate` is older than `.env`, the running process has NOT loaded the new environment variables.
4. **Clean Restart via Watchdog or Process Termination**:
   - Terminate the active PID holding 20129 (`Stop-Process -Id <PID> -Force`).
   - Allow `omniroute_watchdog.ps1` to auto-restart the instance cleanly.
   - Check `watchdog.log` (`C:\Users\Kibe\AppData\Roaming\omniroute\logs\watchdog.log`) for:
     `OmniRoute is UP and healthy on port 20129 (ready in N seconds, PID ...)`.
5. **Verify Endpoint Health & Live Models**:
   - `http://127.0.0.1:20129/api/health` -> `{"status":"ok"}`
   - `http://127.0.0.1:20129/v1/models` -> verify model count > 2000.

## 4. Watchdog Hung Process Handling & Thresholds
- **Pitfall - PID Alive Deadlock**: If OmniRoute event loop hangs or deadlocks, `/api/health` fails but `node.exe` is still in process list. If the watchdog resets failure counts on `Test-OmniRouteProcessAlive`, it will NEVER restart the hung instance, taking ~11 minutes until OS crash.
- **Rule**: Consecutive `/api/health` failures must trigger a restart regardless of whether the PID exists. Threshold is set to `$MaxConsecutiveFailures = 4` (at 15s interval = 60s total detection).
- **Graceful Watchdog Stop/Reload**: Create `$env:APPDATA\omniroute\watchdog.stop`. Watchdog detects file, removes it, and exits cleanly. Relaunch via `Startup\omniroute_watchdog.vbs` or `powershell.exe -File omniroute_watchdog.ps1`.

## 5. Hermes Client Retry Tuning during Proxy Restarts
- Default `agent.api_max_retries: 3` only waits ~20–30s before dropping all sessions and aborting turns with errors.
- Set `agent.api_max_retries: 10` in `~/.hermes/config.yaml` to extend jittered backoff to ~5–6 minutes (delay capped at 60s). Hermes calls `agent._touch_activity()` every 30s during backoff to maintain gateway keep-alive, allowing sessions to seamlessly wait for OmniRoute restart without user re-prompting.
- **9Router Free Fallback Warning**: `9r-free` / `openrouter-free` routes to `cohere/north-mini-code:free` which lacks tool calling support and should NOT be used as an agentic fallback.

## 6. Local Fallback Architectures: Antigravity IDE vs Cockpit Tools
- **Antigravity IDE (`ag_cli.py`)**: Electron GUI IDE (`antigravity-ide.cmd chat -m ask|agent`), NOT an OpenAI HTTP API server. Cannot be configured in `fallback_providers` or `providers` for Hermes agentic loops.
- **Antigravity Cockpit (`cockpit-tools.exe`)**: Runs a local OpenAI-compatible endpoint on port `60818` (`http://127.0.0.1:60818/v1`) using `COCKPIT_API_KEY` (`agt_codex_...`). It rotates Codex accounts from `~/.antigravity_cockpit/codex_accounts.json`. It CAN serve as a secondary local fallback if Cockpit Tools is running.
- **Direct Account Status**: Direct Codex free accounts hit quota limit 429 (`usage_limit_reached`); OpenCode Go is expired (403) and free models suffer severe queue latency.
