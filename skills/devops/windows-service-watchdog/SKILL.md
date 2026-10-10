---
name: windows-service-watchdog
description: Patterns and verification checklist for building resilient Windows watchdog and auto-healing scripts (PowerShell, Python, Batch) that supervise long-running services or hardware pools — single-instance enforcement, anti-flapping cooldowns, rate limits, child process cleanup, consecutive failure thresholds, and live verification.
category: devops
tags: [watchdog, process-supervision, powershell, python, windows, mutex, msvcrt, auto-healer, cooldown, rate-limit, health-checks, restart-thresholds]
---

# Windows Service Watchdog / Process Supervision

**Trigger**: Any task involving managing a long-running Windows service/process via a watchdog script (PowerShell/Batch) that must:
- Enforce single-instance execution (no duplicate watchdogs)
- Track and clean up child processes to prevent accumulation
- Implement consecutive failure thresholds before restart
- Provide clean process termination with grace periods before restart
- Log structured evidence for verification

---

## Core Pattern

### OmniRoute provider-error isolation, hard-down restart gate & hung event-loop ceiling
For a local proxy supervising an account pool, upstream account errors must remain at request/routing scope. A provider 401/403/429, expired OAuth token, cooldown, breaker, or `ALL_TARGETS_SKIPPED` must not by itself restart the whole proxy process. Keep `/api/health` minimal and independent of provider pools, DB, token refresh, and upstream calls.

Use two separate signals:

- **Liveness:** process/listener ownership for the exact target port and command signature.
- **Health/readiness:** HTTP response from `/api/health` or a deeper readiness endpoint.

**Restart Policy (Dual Thresholds):**
1. **Hard-down (Process/Socket absent):** If the matching process or listener disappears, restart after short consecutive failures (e.g. 2–3 checks = 30s).
2. **Transient degradation:** If HTTP health fails 1–2 times while PID/listener is active (e.g. during heavy LLM bursts), log `health_degraded` without restarting.
3. **Hung/Deadlock Ceiling (CRITICAL):** Do NOT unconditionally reset the failure counter to 0 when the process is alive. If `/api/health` fails consecutively for >= $N$ checks (e.g. 8–10 checks = 2–3 minutes) despite PID/listener being present, the Node.js/Python event loop is deadlocked/frozen (zombie process). The watchdog MUST terminate (`Stop-Process -Force`) and restart. Otherwise, an unresponsive service hangs for 10+ minutes until OS fast-fail (0xC0000409).

### Client-Side (Hermes Agent) Resilience against Local Proxy Restarts
When a local LLM proxy (OmniRoute/9Router) restarts, Hermes sessions risk failing immediately if retry bounds are too low:
- **`agent.api_max_retries`:** Default is `3` (backoff ~20–30s total). For local proxies with watchdogs, set `agent.api_max_retries: 10` or `12` in `~/.hermes/config.yaml`. With a 60s max delay cap and internal 30s `_touch_activity`, this extends the retry window to ~5–10 minutes, allowing Hermes to patiently await proxy recovery without erroring out active chat sessions.
- **Fallback Provider Isolation:** Fallback providers in `config.yaml` (`fallback_providers`) must NEVER point back to the same local proxy (e.g. primary `omni` and fallback `custom:omni`). Fallbacks must route to an independent secondary proxy (e.g. 9Router on a separate port) or direct upstream API keys.

Required offline cases before deployment:

1. Provider 401/expired response -> request/target failure only; no process restart.
2. Health timeout/non-200 + matching PID/listener alive -> degraded log; no restart.
3. Matching PID/listener absent after threshold -> restart path.
4. After restart, enforce startup grace and verify the new PID owns the target listener before declaring healthy.

See `references/omniroute-watchdog-case-study.md` for the evidence pattern and patch contract.

### 1. Single-Instance Lock (Mutex with Safe Release)
```powershell
$MutexName = "Local\YourService_Supervisor_Mutex_v1"
$mutex = $null
$hasMutex = $false
try {
    $mutex = New-Object System.Threading.Mutex($true, $MutexName, [ref]$hasMutex)
    if (-not $hasMutex) {
        Write-Log "Another watchdog instance is already active. Exiting duplicate."
        exit 0  # Triggers finally block; $hasMutex guard prevents unsynchronized release error
    }
} catch {
    Write-Log "Mutex initialization failed: $_. Cannot guarantee single instance. Exiting."
    exit 1
}

# ... watchdog loop ...

finally {
    if ($mutex -and $hasMutex) {
        try {
            $mutex.ReleaseMutex()
            $mutex.Dispose()
        } catch {}
    }
    Write-Log "Watchdog stopped."
}
```

### 2. Dynamic Environment Paths & Portable Fallbacks
Never hardcode `C:\Users\<user>\...`. Use environment variables with dynamic fallback resolution:
```powershell
$NodeExe = "C:\Program Files\nodejs\node.exe"
if (-not (Test-Path $NodeExe)) {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) { $NodeExe = $nodeCmd.Source }
}

$AppDir = "$env:USERPROFILE\YourApp"
if (-not (Test-Path $AppDir)) {
    $fallback = "$env:LOCALAPPDATA\YourApp"
    if (Test-Path $fallback) { $AppDir = $fallback }
}

$LogDir = "$env:APPDATA\YourService\logs"
$LogFile = Join-Path $LogDir "watchdog.log"
$StopFile = "$env:APPDATA\YourService\watchdog.stop"
```

In companion `.vbs` startup launchers:
```vbscript
Option Explicit
Dim WshShell, appData, scriptPath
Set WshShell = CreateObject("WScript.Shell")
appData = WshShell.ExpandEnvironmentStrings("%APPDATA%")
scriptPath = appData & "\YourService\watchdog.ps1"
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptPath & """", 0, False
Set WshShell = Nothing
```

### 2b. Reboot-time console window triage (headless startup)
When a Windows host shows a black Python/CMD window immediately after boot, do not kill workers blindly. First collect O(1) evidence over SSH: `Win32_Process` command lines and parent PIDs, `Win32_StartupCommand`, the interactive Startup folder, and scheduled-task actions. Distinguish the normal venv launcher parent/child pair from a real duplicate; the venv `python.exe` may start the base Python child with the same command line.

If the Startup entry is a `.vbs` launcher but its Python watchdog calls another console-subsystem executable with plain `subprocess.run()`/`Popen()`, patch that exact call with `creationflags=subprocess.CREATE_NO_WINDOW` plus `stdout=DEVNULL` and `stderr=STDOUT`. Make a timestamped backup, require an exact one-anchor replacement, run remote `python -m py_compile`, and verify the patched line plus `MainWindowHandle = 0`. Preserve active downloader/render/gateway workers unless the user explicitly asks to stop them. A failed remote desktop screenshot API is not proof that the fix failed; use process/window-handle and syntax evidence and report the capture limitation separately.

See `references/remote-windows-startup-console-triage.md` for the bounded SSH commands and patch contract.

### 3. Streamlined Health Check (Stream-Safe HTTP & Singleton Client)
Avoid bare `Invoke-WebRequest` in PowerShell 5.1 for long-running watchdogs. While `Invoke-WebRequest -TimeoutSec` tests socket connectivity, in Windows PowerShell 5.1 (`System.Net.HttpWebRequest`), `-TimeoutSec` only sets the initial connection/header timeout; if the TCP connection establishes but the server stalls or keeps the socket open without closing the stream, `Invoke-WebRequest` hangs indefinitely on stream read. This turns the watchdog itself into a zombie process (holding an ESTABLISHED TCP connection for hours without executing subsequent iterations).

Prefer `System.Net.Http.HttpClient` with a hard timeout, or an explicit `HttpWebRequest` with both `Timeout` and `ReadWriteTimeout`.
**CRITICAL — Socket Churn Prevention:** Do NOT create and dispose `HttpClient` on every health check tick (e.g. every 15s). Repeated disposal creates hundreds of sockets in `TIME_WAIT`, causing ephemeral port churn. Maintain a script-scoped singleton `$script:HttpClient` reused across all ticks and dispose it in the script's `finally` block:
```powershell
Add-Type -AssemblyName System.Net.Http -ErrorAction SilentlyContinue

$script:HttpClient = $null
function Get-HttpClient {
    if ($null -eq $script:HttpClient) {
        $script:HttpClient = [System.Net.Http.HttpClient]::new()
        $script:HttpClient.Timeout = [System.TimeSpan]::FromSeconds(8)
    }
    return $script:HttpClient
}

function Test-ServiceAlive {
    try {
        $client = Get-HttpClient
        $res = $client.GetAsync("http://${HostAddr}:${Port}/api/health").GetAwaiter().GetResult()
        return ($res.StatusCode -eq [System.Net.HttpStatusCode]::OK)
    } catch {
        return $false
    }
}
```

### 3b. Anti-Flapping Restart Budget (Sliding Window Rate Limit)
When a service suffers from persistent infrastructure failures (such as all upstream network proxies down), restarting the process every few checks will not resolve the outage and will cause continuous thrashing, high CPU, and interrupted requests. Enforce a sliding-window restart budget (e.g. max 3 restarts within 15 minutes / 900s):
```powershell
$MaxRestartsInWindow = 3
$RestartWindowSec = 900
$script:RestartHistory = [System.Collections.Generic.List[datetime]]::new()

function Test-CanRestartService {
    $now = Get-Date
    $cutoff = $now.AddSeconds(-$RestartWindowSec)
    $recent = @($script:RestartHistory | Where-Object { $_ -ge $cutoff })
    $script:RestartHistory = [System.Collections.Generic.List[datetime]]::new()
    foreach ($t in $recent) { $script:RestartHistory.Add($t) }

    if ($script:RestartHistory.Count -ge $MaxRestartsInWindow) {
        Write-Log "anti_flapping: Restart limit reached ($($script:RestartHistory.Count)/$MaxRestartsInWindow within ${RestartWindowSec}s). Pausing restarts to avoid flapping."
        return $false
    }
    return $true
}
```

### 4. Process Discovery & Cleanup
```powershell
function Get-ServiceProcesses {
    # 1. Find processes by command line signature (e.g., "run-next.mjs start")
    # 2. Find child processes via ParentProcessId
    # 3. Check port ownership (Get-NetTCPConnection)
    # Return deduplicated list by ProcessId
}

function Stop-ServiceProcesses {
    $procs = Get-ServiceProcesses
    foreach ($proc in $procs) { Stop-Process -Id $proc.ProcessId -Force }
    # Wait up to N seconds for exit
}
```

### 5. Consecutive Failure Threshold
```powershell
$MaxConsecutiveFailures = 3
$CheckIntervalSec = 10

$consecutiveFailures = 0
while ($true) {
    if (Test-ServiceAlive) { $consecutiveFailures = 0 }
    else {
        $consecutiveFailures++
        if ($consecutiveFailures -ge $MaxConsecutiveFailures) {
            Restart-Service
            $consecutiveFailures = 0
        }
    }
    Start-Sleep -Seconds $CheckIntervalSec
}
```

### 6. Startup Grace Period with Polling
```powershell
$MaxStartupWaitSec = 30
$StartupPollIntervalSec = 3

$process = [System.Diagnostics.Process]::Start($psi)
$elapsed = 0
while ($elapsed -lt $MaxStartupWaitSec) {
    Start-Sleep -Seconds $StartupPollIntervalSec
    $elapsed += $StartupPollIntervalSec
    if ($process.HasExited) { return $false }
    if (Test-ServiceAlive) { return $true }
}
return $false  # Timed out
```

---

## Verification Checklist (Live Proof)

| Check | Command | Expected |
|-------|---------|----------|
| Syntax | `[System.Management.Automation.Language.Parser]::ParseFile(...)` | 0 errors |
| Single watchdog process | `Get-CimInstance Win32_Process \| Where { $_.CommandLine -like '*watchdog.ps1*' }` | Exactly 1 |
| Single service process | `Get-CimInstance Win32_Process \| Where { $_.CommandLine -like '*service-signature*' }` | Exactly 1 |
| Port ownership | `Get-NetTCPConnection -State Listen \| Where LocalPort -eq PORT` | 1 process owns port |
| Health endpoint | `Invoke-WebRequest http://127.0.0.1:PORT/health` | HTTP 200 |
| Duplicate prevention | Launch 2nd watchdog instance | Logs "already running", exits |
| Auto-recovery | `Stop-Process -Id <service-pid> -Force` | Watchdog restarts within threshold |
| Headless Python service | Launch directly via `pythonw.exe` from VBS `WScript.Shell.Run ..., 0, False` (omit `cmd /c`), entrypoint guards `sys.stdout/stderr is None` | Listening on port, 0 cmd/conhost visible, `curl -i http://127.0.0.1:PORT/` returns HTTP 200 (not `Empty reply`) |
| OpenSSH to remote Windows host routes commands through cmd.exe (`cat` missing, PowerShell quote unescaping) | When executing commands via `ssh <host> "<cmd>"`, the default shell on Windows OpenSSH is `cmd.exe`. Calling `cat` fails (`'cat' is not recognized`). Using `powershell -Command "..."` with `$var` unescaped gets expanded by client bash before reaching SSH, resulting in syntax errors (`Missing expression after unary operator '++'`). Fix: Use `type` to read files on remote Windows, or escape variables (`\$var`) when invoking PowerShell over SSH |

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Single-shift watchdog expanded to multi-shift lacks dynamic naming & shift-isolated state | Hardcoded shift label in report (`[LOGIN GPM ĐÊM]`) fired at midday/morning confuses user ("Gì mà h ca tối"). Furthermore, setting daily monolithic `finished: true` at noon prematurely locks out the evening shift. Fix: resolve shift dynamically via `get_current_shift_info()` and isolate completion per shift (`finished_shifts = ['TRUA']`) so evening is not blocked |
| Multiple watchdogs started via Startup folder + manual launch | Mutex on `Local\` namespace (per-session) prevents both |
| Mutex initialization throws exception | In `catch` block, log error and `exit 1` immediately so no watchdog runs unshielded |
| Application root path missing during restart attempt | Validate `Test-Path $AppDir` before stopping processes or attempting launch; abort restart if absent |
| `ReleaseMutex()` called on duplicate exit throws ApplicationException | Track `$hasMutex` boolean; only call `ReleaseMutex()` if `$mutex -and $hasMutex` |
| Hardcoded `C:\\Users\\<user>` breaks across profiles or machines | Use `$env:APPDATA`, `$env:LOCALAPPDATA`, `$env:USERPROFILE` and `%APPDATA%` in VBS |
| Hermes cron interval shorter than heal cycle spawns stacked instances | Set cron interval ≥ worst-case cycle (e.g. `*/5` not `*/1` if each heal takes 15s+); lock is fallback, not primary fix |
| Healer instance count not monitored | Before any heal run, check `Get-CimInstance Win32_Process` for existing healer instances; if > 1, a prior lock/cron misconfiguration exists |
| Redundant TCP connect before HTTP check causes socket churn | Call `Invoke-WebRequest -UseBasicParsing` directly with a 5s timeout |
| `Invoke-WebRequest -TimeoutSec` hangs indefinitely on established socket in PowerShell 5.1 | `-TimeoutSec` only sets connection timeout in .NET `HttpWebRequest`. If TCP connection succeeds but the server stalls or keeps stream open without bytes/EOF, PowerShell 5.1 hangs forever on stream `Read()` without timing out, freezing the watchdog process in RAM for hours. Fix: use `System.Net.Http.HttpClient` with task/cancellation timeout, or `HttpWebRequest` with explicit `ReadWriteTimeout` and `KeepAlive = $false`. |
| Monolithic health failure counter triggers false-positive restart during LLM burst concurrency | During multi-target combo loops or high-token bursts, `/api/health` may degrade for 30-60s while process is alive. Using a single threshold (e.g. 4 checks = 60s) restarts healthy processes and kills active chat streams. Fix: Separate two distinct counters: (1) `MaxProcessAbsentFailures = 3` (~45s) for hard-down (process/listener gone); (2) `MaxDeadlockFailures = 12` (~180s = 3m) hung ceiling when process is alive. Transient failures log `health_degraded` without restarting. |
| Singleton HttpClient disposal per tick causes socket churn (TIME_WAIT) | Creating and disposing `HttpClient` every tick (15s) creates hundreds of sockets in `TIME_WAIT`. Fix: Maintain script-scoped persistent singleton `$script:HttpClient` with `Timeout = [TimeSpan]::FromSeconds(8)` and dispose once in script `finally` block. |
| Hardcoded API keys in startup/service scripts | Resolve keys from environment or parse `.env` dynamically on launch |
| Zombie child processes (esbuild, conhost) accumulate | Include child process lookup by `ParentProcessId` |
| Port stuck in TIME_WAIT after kill | `Start-Sleep 1` after `Stop-ServiceProcesses` before restart |
| Health check passes but service not fully ready | Poll health endpoint, don't just check TCP port |
| Watchdog stops but leaves service running | Stop file (`watchdog.stop`) signals graceful shutdown; `finally` block releases mutex |
| Fixed 8s startup timeout too short for cold Next.js builds | Use configurable grace period (30s) with progress logging |
| Restart loop on flaky health checks | Consecutive failure threshold (3) filters transient blips |
| Variable name `$pId` collides with read-only `$PID` | PowerShell variables are case-insensitive; assigning `$pId = ...` throws `SessionStateUnauthorizedAccessException`. Use `$owningPid`, `$targetPid`, or `$procId` |
| Watchdog probes fail during multi-worker burst or heavy LLM load, causing false-positive restart loop of healthy service | Distinguish `service_down` (process/socket gone) vs `health_degraded` (timeout on `/api/health` while process & port listener still active). Log `health_degraded` for short blips (1–2 checks). CẤM reset biến đếm lỗi vô điều kiện về 0 khi process còn sống; phải có trần deadlock (ví dụ >=8 checks / 2–3 phút) để force-kill và restart nếu event loop bị đơ hoàn toàn |
| Unresponsive/deadlocked proxy hangs for 10+ minutes because watchdog resets failure counter on PID presence | When Node.js/Python event loop freezes (combo loop, native buffer overrun), `/api/health` stops responding but PID/port listener remains bound. Resetting `$consecutiveFailures = 0` whenever PID is alive causes an infinite hang trap until OS crash (0xC0000409). Fix: Track consecutive health failures with a hard ceiling (e.g. 8–10 checks = 2–3 min). If threshold reached, terminate with `Stop-Process -Force` and restart even if PID/listener is present |
| Hermes sessions fail with "API call failed after 3 retries" during local proxy restarts | Default `agent.api_max_retries: 3` only retries for ~20–30s before dropping turns. When local proxy watchdog takes 1–3 minutes to recover, increase `agent.api_max_retries: 10` or `12` in `~/.hermes/config.yaml` to extend backoff window to 5–10m (with internal 30s `_touch_activity` keeping Gateway alive). Ensure `fallback_providers` point to an independent route (9Router :20128 or direct API), NOT back to the failing local proxy |
| Watchdog script patched on disk remains running with stale RAM logic indefinitely | Modifying a `.ps1` on disk does NOT update long-running background PowerShell processes. Always inspect running PID, terminate the old watchdog process, and launch a fresh headless instance (`-WindowStyle Hidden`) to load new logic into RAM |
| Modifying watchdog/config only in runtime AppData leaves repo unversioned | User requirement: Always commit standardized ops scripts and runbooks into the source repository (e.g. `scripts/ops/omniroute_watchdog.ps1`, `docs/deployment/UPDATE_RUNBOOK.md`) so fixes are not lost on fresh clones or migrations |
| Probe timeout too low on high concurrency (`TimeoutSec 5`) | When upstream/LLM proxies handle multi-worker bursts, the event loop delays health responses. Set `TimeoutSec` >= 15s to prevent false restart flapping |
| Next.js startup grace period too short (30s) | Next.js cold compile takes 50-75s on Windows. Increase `$MaxStartupWaitSec` to >= 90s with progressive polling ($StartupPollIntervalSec 3s) |
| Consecutive failure threshold too aggressive | With 10s check and 3 failures, service is killed after 30s blip. Use `$CheckIntervalSec = 15` and `$MaxConsecutiveFailures = 5` (>75s uninterrupted outage required) |
| Stale watchdog threshold out of sync with Worker Budget (e.g. 10m vs 15m) | Watchdog threshold must match or exceed worker execution budget (`DEFAULT_THRESHOLD_SECONDS = 900.0` for 15m budget) to prevent false stall alerts |
| Stale watchdog picks up previous turn's finished/zombie subagent sharing the same parent_session_id | Filter child sessions by timestamp: `cstate timestamp >= (dispatched_at - 30.0)` so only active subagents from the current dispatch are evaluated |
| Mock unit test sessions lingering in shared state files trigger false stall watchdog alerts with absurd elapsed times | Test suites writing mock session IDs (`test_*`, `mock_*`, `parent_*`) to `farm_coordinator_phase.json` and `watchdog_state.json` leave stale records from weeks ago. When watchdog runs, it evaluates the mock session against ancient timestamps, firing alarms like "Session test_xxx im lặng 34513 phút". Fix: (1) In tests, isolate state files via `tmp_path` or cleanup mock keys in teardown; (2) In watchdogs, skip test/mock session prefixes (`test_`, `mock_`, `coord_session_`); (3) Triage absurd elapsed times as test pollution rather than real process hangs. See `references/hermes-stale-watchdog-subagent-coordination.md`. |
| Watchdog scripts duplicated between local appdata and shared cloud sync | Ensure updates are applied to both `%LOCALAPPDATA%\hermes\scripts\...` and `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\...` to avoid drift |
| Primary gateway port (Port 1 / proxy01) reset triggers cascading failure | Box DDNS/gateway bound to Port 1; resetting it drops domain and makes all ports appear dead → always enforce `skip_first = true` and domain preflight |
| Auto-healer unit test mocks only target ports | Scanner treats omitted cluster ports as dead (Layer 1 fallback) → hits `MAX_HEALS_PER_RUN` cap and defers test port. Populate mock API for ALL cluster ports and use call-tracking mock for post-heal re-probes |
| `powershell.exe -WindowStyle Hidden` in Task Scheduler flashes console window | PowerShell is a CUI binary; conhost creates console window before args are parsed. In interactive sessions/gaming, this causes focus loss and flashing every tick. Always launch via `wscript.exe "launcher.vbs"` with `WScript.Shell.Run(cmd, 0, False)` (GUI subsystem + `SW_HIDE (0)` creates console hidden from frame 0) and avoid spawning child `powershell.exe` for in-process Cim queries |
| Python watchdog/cron subprocess calls flash cmd/conhost windows | When running without a console (pythonw / hidden parent), any `subprocess.run` or `Popen` invoking console executables (`adb.exe`, `git.exe`, `python.exe`) without `creationflags=0x08000000` (`CREATE_NO_WINDOW`) forces Windows to allocate a visible console window. Fix: explicitly pass `creationflags=subprocess.CREATE_NO_WINDOW` or inject `sitecustomize.py` into environment `site-packages` to auto-inject `0x08000000` on Windows |
| `DETACHED_PROCESS` (`0x00000008`) allocates a visible console window when paired with console Python (`python.exe`) | In Windows subprocess creation, passing `DETACHED_PROCESS` (`0x08`) without `CREATE_NO_WINDOW` tells the OS to detach from the parent console and allocate a NEW console window (`conhost.exe`) for the child process. When watchdog/worker scripts call `python.exe -u ...` with `DETACHED_PROCESS`, a blank CMD window pops up on screen (`MainWindowHandle != 0`). Fix: (1) Always use `pythonw.exe` instead of `python.exe` for background workers; (2) In `sitecustomize.py`, strip `0x08` and enforce `CREATE_NO_WINDOW`: `kwargs['creationflags'] = (flags & ~0x00000008) | 0x08000000`; (3) In companion VBS startup scripts (`shell:startup`), invoke `pythonw.exe` directly via `WScript.Shell.Run ..., 0, False`. |
| Hermes cronjob watchdog with no_agent=True spams Telegram on batch stdout | In `no_agent=True` cron jobs, ANY non-empty stdout is delivered to chat as a message. Recurring batch scripts (e.g. every 10m) must keep intermediate execution silent (route logs to `stderr` or logfiles) and print to `stdout` ONCE ONLY when the entire multi-batch shift finishes (`all_done=True`) or at shift cutoff. Empty stdout = silent run. |
| Watchdog prints empty summary on zero work / transient dependency blip (`eligible_count == 0`) | Must `return 0` with completely silent stdout. Never print an empty report header/summary template when 0 items were processed, as `no_agent=True` Hermes cron treats any stdout as a user-facing message. |
| Sub-module calls in Python watchdog leak internal `print()` to stdout mid-run | When calling sub-module functions directly via Python import, internal `print()` leaks into stdout during 30-60m batches, causing continuous spam in `no_agent=True` cron/Telegram. Fix: wrap sub-module calls in `with contextlib.redirect_stdout(io.StringIO()):` |
| Multi-device/batch watchdog lacks singleton lock against recurring cron ticks | A 30-60m batch invoked via 5-15m cron will spawn overlapping instances competing for ADB/device locks. Fix: NEVER use custom PID files with unlink/os.kill(0) (prone to race conditions and Windows PID reuse). Always use kernel-level advisory file lock `ProcessLock` via `msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)` on Windows (`fcntl.flock` on POSIX). OS automatically frees handle on normal exit or abnormal crash without stale file deadlock. |
| Watchdog summary dumps raw Python lists of dozens/hundreds of items | In final report, never output raw Python lists `['M1 (email1)', ...]`. Format a concise summary showing count metrics (`Thành công: X/Y máy`) and compact failed machine IDs only (`Thất bại: Z máy (Mxx, Myy)`). |
| Windows path `\r` escape inside string replacement corrupts generated code | Writing `r"D:\Taadaa\runtime\..."` through string patch tools interprets `\r` as ASCII Carriage Return (0x0D), corrupting the path into `D:\Taadaa\r` and breaking syntax (`unterminated string literal`). Always use forward slashes `D:/Taadaa/runtime/...` in generated Python code on Windows. |
| Apologizing verbosely when user reports spam or watchdog bug | Empty apologies ("Dạ em nhận lỗi...") infuriate the user. Practice Action-First response: identify faulty script/job immediately, state the concrete fix (redirect_stdout, singleton lock, compact format), and dispatch the patch without conversational delay. |
| Agent deletes/pauses cronjob when user forwards or replies to a cron report | User forwarding a cron report is asking about the technical outcome ("why 0 items?", "why failed?"), NOT ordering the job to be deleted. NEVER call `cronjob(action='remove')` or `action='pause'` without an explicit text command ("xóa cron X", "tắt job Y"). |
| Watchdog subprocess calls `adb` via shell instead of absolute path | Environment PATH sanitization in scheduler jobs can drop custom paths or resolve stale/incompatible ADB binaries. Always resolve and invoke the farm-specific absolute ADB binary path (e.g. `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`) directly. |
| Watchdog race condition on premature session completion reporting | If a watchdog aggregates multiple phases (e.g., Feed swipe finished before Follow hook), checking only feed completion count triggers early report delivery with 0 follow results. Require ALL linked hooks/files (`follow_result.json`, `upload_result.json`) to be finalized or verify `runner_busy is False` after a grace window before emitting session report. |
| Watchdog summary fallback reads stale historical logs on batch crash/error | When a batch runner fails early (syntax error, missing environment variable, preflight crash with exit code != 0), a fallback parser that scans for `logs_*/summary.json` sorted by mtime will silently pick up prior runs (e.g. yesterday's summary), reporting false success counts for today's crashed run. Enforce run window validation (`log_mtime >= run_start_time`); if exit code != 0 or no fresh logs exist in window, report failure / error status rather than falling back to historical summary files. |
| Stale log fallback in watchdog masks early launcher failures | Never read unconstrained historical summary files when exit code != 0. Require strict epoch gating: `min_mtime = run_start_epoch` and only evaluate files created after `min_mtime`. When runner exit code != 0, zero out totals and explicitly set phase status to runner failure. |
| Python multiline f-string with unescaped newline in write() causes syntax error | When appending log lines (`_df.write(f"...{var}\n")`), an accidental physical newline inside quotes (`f"...{var}\n"`) becomes `unterminated f-string literal` in Python 3.12+. Always write explicit escaped `\n` in a single line and run `python -m py_compile` before deployment. |
| Subprocess ADB commands outputting warnings (Samsung Pay / spay / spaymini) trigger false Telegram delivery in no_agent cron | In `no_agent: true` cron, any non-empty stdout triggers Telegram delivery. When watchdogs execute package commands or when devices lack packages (`Error: java.lang.IllegalArgumentException: Unknown package: com.samsung.android.spay`), warnings on stderr/stdout must be silenced via `subprocess.DEVNULL` or filtered out so the watchdog stays 100% silent unless real actions occur. |
| Watchdog false-positive reporting on runner crash via unconstrained mtime glob | Watchdog parsing runtime logs (`glob("logs_*/summary.json")`) without `mtime >= run_start_epoch` will pick up yesterday's summary when today's runner exits with code 1. In report generation: gate log parsing with `min_mtime`, guard non-zero exit codes to report "LỖI KHỞI ĐỘNG RUNNER (0/0/0)", and keep backward compatibility when `min_mtime is None`. |
| PowerShell `2>&1` combined with `$ErrorActionPreference = 'Stop'` treats native command stderr as fatal RemoteException | When invoking Python scripts from PowerShell, stderr output (warnings, tracebacks) captured via `2>&1` creates error records that trigger `NativeCommandError` / terminate execution immediately. Wrap native command calls in `$ErrorActionPreference = 'Continue'` and evaluate `$LASTEXITCODE` explicitly, or separate stderr redirection from pipeline output. |
| Subagent dispatched to test/patch server script blocks on foreground loop | If worker runs `python server.py` directly, `serve_forever()` blocks indefinitely until the 600s timeout. Coordinator contract must strictly forbid running long-lived foreground server processes; test via `curl`/HTTP endpoints instead. |
| Legacy `.bat` launcher on Desktop opened by habit still pops cmd | Replace `.bat` with `start "" wscript.exe "run_hidden.vbs"` + `exit`, or supply direct `.lnk` shortcut pointing to `wscript.exe` with `SW_HIDE (0)` so double-clicking never leaves a lingering cmd window. |
| Startup folder (`shell:startup`) `.bat` launcher with `start /min` pops visible cmd window on reboot | Windows `start /min` in `.bat` scripts still allocates a console window with a visible taskbar item. In `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`, never use `.bat` with `start /min`; replace with a `.vbs` launcher using `WScript.Shell.Run(..., 0, False)` invoking `pythonw.exe` directly so reboots stay 100% headless. |
| VBScript `WshShell.Run` uses `cmd /c pythonw.exe` | Leaves a resident `cmd.exe` parent process in task manager. Invoke `pythonw.exe` directly from VBScript with dynamic fallback resolution across uv/Python312/venv paths. |
| Python service under `pythonw.exe` crashes with `AttributeError: 'NoneType' object has no attribute 'write'` on client connection | In Windows GUI mode (`pythonw.exe`), `sys.stdout` and `sys.stderr` are `None`. Any `print()`, `sys.stderr.write()`, or `BaseHTTPRequestHandler.log_message()` crashes the worker thread immediately. Port remains `LISTENING` but client receives `ERR_EMPTY_RESPONSE` / `Empty reply from server`. Fix: (1) At entrypoint, guard: `if sys.stdout is None: sys.stdout = open(os.devnull, 'w', encoding='utf-8')` and same for `sys.stderr`; (2) Guard `log_message` in HTTP handlers; (3) When converting to `pythonw.exe`, NEVER verify port listening only — MUST execute real HTTP `curl -i` test against the headless process. |
| User reports service/dashboard "sập" after configuring startup/reboot | When user mentions "t chỉnh bật lên cùng window ... r mà" or reports a service down after boot, search recent sessions (`session_search`) first for recent startup/VBScript changes instead of asking redundant discovery questions. |
| Unbounded batch iteration in no_agent watchdog causes Hermes cron execution timeout (10800s) and provider alert timeout | In scheduled watchdogs iterating over a pool of items (e.g. 70+ phones/accounts), sequential processing without a batch cap or per-item deadline exceeds Hermes cron limit (3h / 10800s). When Hermes kills the hung script, its failure notification agent attempts LLM delivery; if the provider times out, it reports `⚠️ Cron '<name>' failed: provider timeout`, masking the real root cause (`Script timed out after 10800s`). Fix: (1) Cap batch size per tick (`MAX_BATCH = 2..5`) so runs take <5m; (2) Enforce strict per-item timeouts (`timeout=10..30s` on all ADB/network calls); (3) Check `~/AppData/Local/hermes/cron/output/<job_id>/` directly to diagnose the underlying script timeout. |
| Python logging / library stderr leaks to stdout causing recurring cron spam | Sub-modules or third-party SDKs using Python logging (or logging.basicConfig) with StreamHandler(sys.stdout) will dump [INFO]/[ERROR] to stdout on every failure (e.g. GPM Chromium version error). In no_agent=True cron jobs, this causes repeated Telegram message spam every tick. Fix: redirect root logger to sys.stderr or a local log file; wrap helper invocations in contextlib.redirect_stdout; suppress stdout completely on dependency errors. |
| Module-level logging.basicConfig in imported helper scripts leaks root logs to stdout in no_agent watchdogs | When an imported script or helper (e.g. `preflight_s7_rolling_cleanup.py`) calls `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` at module top-level, importing it pollutes Python's root logger. All downstream libraries (`automation_core.adb`, `requests`, `urllib3`) inherit `propagate=True` and dump verbose info logs (`AdbClient initialized...`) to stdout, flooding Telegram Farm Alert every tick. Fix: (1) In helper modules, NEVER call `basicConfig` at top level; configure a dedicated `FileHandler`, set `logger.propagate = False`, and gate console `StreamHandler(sys.stderr)` inside `if __name__ == '__main__':`; (2) In watchdog entrypoints, scrub root logger handlers: `for h in list(root_logger.handlers): if isinstance(h, StreamHandler) and h.stream in (sys.stdout, sys.__stdout__): root_logger.removeHandler(h)`. |
| Imported browser/OAuth helper modules (e.g. `add_oauth_omniroute`) leak reCAPTCHA and audio challenge logs to stdout during no_agent cron | When helper modules for GPM/Playwright attach `StreamHandler(sys.stdout)` or call `logging.basicConfig` without stream specification, reCAPTCHA solver logs (`[INFO] Clicking reCAPTCHA...`, `[ERROR] Error solving reCAPTCHA audio: Frame was detached`) dump to stdout when Google challenges multi-worker sessions. In `no_agent=True` Hermes cron, non-empty stdout triggers Telegram delivery, spamming Farm Alert. Fix: (1) Force root logger to `sys.stderr` via `logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)`; (2) Remove handlers where `h.stream == sys.stdout`; (3) Clear handlers on specific loggers (`logging.getLogger(name).handlers.clear()`); (4) Guard `print()` to fire ONLY when `success_count > 0`, ensuring 0 bytes stdout on fail/skip. |
| Python watchdog adds StreamHandler(sys.stdout) by default, leaking normal INFO logs to cron delivery | Adding StreamHandler(sys.stdout) unconditionally in script logger setup prints routine lines (`[INFO] Bắt đầu đồng bộ...`, `[INFO] Không có thay đổi`) to stdout every 15m tick. For `no_agent=True` Hermes cron, ANY non-empty stdout triggers Telegram delivery, flooding the user with spam even when 0 actions were taken. Fix: attach only `FileHandler` to file by default; gate `StreamHandler(sys.stdout)` behind CLI flag `--verbose` / `-v`; emit summary via `print()` ONLY when actual work occurred (`created_count > 0 or cleaned_count > 0`). See `references/silent-watchdog-logging-and-reporting.md`. |
| Account pool watchdog spams Telegram every tick even when healthy | Watchdog unconditionally prints status report even when 100% accounts are active and no errors exist. In `no_agent=True` Hermes cron, stdout = message. Fix: enforce Silent Mode when `len(all_failed) == 0 and active_cnt == total_cnt` (return without print) and silence intermediate scan/open profile stdout logs. |
| Muting cron delivery to local when user complains about spam | When user says "đừng có spam thông báo", they object to noise/progress logs, not the channel. Muting delivery to `local` loses essential farm alerts. Keep target `telegram:-5373649734`, enforce 0-byte stdout on failure/idle, and emit only a concise summary on success. |
| Midnight boundary cutoff masks final batch completion in silent watchdogs (`schedule: */5 20-23`) | When a silent watchdog (running batches from 20:15-23:45) suppresses per-batch alerts and only emits a single final summary at cutoff / all-done, a batch launched at 23:3x finishing at 23:56 will miss the final summary if cron schedule is capped at `23` (`*/5 20,21,22,23 * * *`). The 23:55 tick sees the batch still running and stays silent, but no further ticks fire post-midnight (`00:00 - 04:00`). Fix: Always align cron schedule with script's after-window definition (e.g. `*/5 20,21,22,23,0,1,2,3 * * *`) so post-midnight completion triggers final summary report. |
| Farm watchdog lacks `--dry-run` and structured telemetry dict | Testing watchdog eligibility logic (ADB checks, device locks, slot schedule distance, live account status) without `--dry-run` risks accidental hardware command execution or state corruption. Fix: Implement `check_and_run_one(dry_run: bool = False) -> dict` returning telemetry metrics (`scanned_targets`, `skipped_locked`, `skipped_feed`, `skipped_distance`, `skipped_die`, `attempted`, `success`, `failed`, `dry_run`). When `dry_run=True`, skip mutating hooks and return immediately. |
| Dual script locations (`deploy/hermes-home/scripts` vs `%LOCALAPPDATA%\hermes\scripts`) drift during test authoring | New unit tests and script edits placed only in git repo deploy or only in runtime will fail or get overwritten during sync. Always update/create companion test scripts in both locations and execute `cron_sync_watchdog.py --force` to reconcile with OneDrive shared sync. |
| Tool patch failure (`write error: No space left on device`) on low-headroom C: drive | `%LOCALAPPDATA%\hermes\scripts` sits on `C:`, which may run low on disk space (<200MB free). Patching via temp-file-backed tools fails with `cat: write error: No space left on device`. Fix: patch the source copy on `D:` first, then copy directly via Python binary stream (`with open('D:/...', 'rb') as src, open('C:/...', 'wb') as dst: dst.write(src.read())`) to avoid temporary buffer allocation on `C:`, followed by syntax verification (`python -m py_compile`). |
| Remote ADB Windows Task Scheduler SYSTEM conflict with Xiaowei/UI tools | Registering ADB server as a Task Scheduler task under `SYSTEM` account (`/ru "SYSTEM"`) causes `adb.exe` to use `C:\Windows\System32\config\systemprofile\.android\adbkey` instead of the user profile key (`C:\Users\<User>\.android\adbkey`). This clobbers RSA keys with Xiaowei/GemPhoneFarm, breaks device authorization, and causes phone prompt popup spam. Fix: ALWAYS register Remote ADB startup task under the active interactive user profile (`/sc onlogon /rl highest`) and bind `adb -a nodaemon server` so it uses the standard user RSA key matching Xiaowei |
| Browser automation / nurture script on no_agent=True cron dumps CDP & tab step logs to stdout | User phản ánh: "spam quá chạy xong r báo cáo ngắn gọn thôi". In no_agent=True cron, any stdout stream creates a Telegram message. Scripts with extensive step-by-step progress (CDP connect, tab navigation, sleep timers, scrolling) MUST route logger to dedicated file (`logs/*.log`) and keep stdout 100% empty until execution completes, then print a concise 2-4 line summary (success count, email list, and MEDIA: screenshot) |
| Raw progress logs in `no_agent=True` cron / updater scripts produce unreadable Telegram messages ("nhìn sida khó hiểu") | In `no_agent=True` cron jobs, stdout is sent verbatim as the Telegram message. Dumping step-by-step debug lines (`[UPDATER] 1. Fetching...`, `Candidate pool size...`, `+ LIVE: ...`) produces an ugly, confusing message. Route ALL intermediate logs to `sys.stderr` (`print(..., file=sys.stderr)`). Reserve `sys.stdout` exclusively for ONE final Telegram Markdown report with clear emoji badges (⚡, 🥇, 🥈, 🌐), sanitized model names (strip `openrouter/`, `:free`), and clear priority tiers. Set `max_tokens: 5` on post-update verification pings and keep them non-blocking so slow reasoning models do not fail a successful combo update. |
| Muting cron delivery to local when user complains about cron spam | When user says "t bảo k đc gửi spam như v r mà", their goal is to eliminate verbose raw logs and retain a concise summary ("ý tao vẫn đc gửi báo cáo nhưng tóm tắt lại thôi"), NOT silencing delivery completely by setting `deliver: local`. Switching delivery to `local` silences the alert completely and triggers user steering. Correct response: keep `deliver: telegram:...`, isolate root/Playwright logger to rotating file, and emit only a structured 2-3 line summary to stdout on completion. |
| Recurring retry ticks spam Telegram with "Đã dọn đợt này: 0 máy" on persistent device failure | In scheduled batch watchdogs (e.g. `*/15 3,4,5 * * *`), when devices fail in batch 1, subsequent retry ticks re-run. If `s_count == 0` (0 new devices cleared), script MUST `return 0` with completely silent stdout (0 bytes). CẤM in template báo cáo ra stdout khi `s_count == 0`. Báo cáo tổng thể chỉ in 1 lần/ngày (`reported_date == today_str`); giới hạn retry tối đa 2 lần/máy/ngày (`machine_retries >= 2`) để chống lặp vô tận và hammering phần cứng. Khi user báo spam: gọi ngay `cronjob(action='pause')` để ngắt nhịp trước khi sửa. Xem `references/silent-watchdog-pattern-and-telegram-spam-prevention.md` (Mục 18). |
| ThreadPoolExecutor bypasses thread-unsafe `contextlib.redirect_stdout` and `s_count == 0` report condition causes multi-thousand character cron spam | In `no_agent: true` Python watchdogs using `ThreadPoolExecutor`, `contextlib.redirect_stdout` is not thread-safe and leaks child logs if imported modules attach `StreamHandler(sys.stdout)` directly. Furthermore, condition `if success_list or fail_list: print(...)` violates the silent watchdog invariant when `len(success_list) == 0`. When every account/profile fails or is not logged in, printing `fail_list` causes tens of kilobytes of raw exceptions/redirects to be delivered to Telegram every tick (generating "Clgt" / "Đkm lại spam alert"). Fix: (1) At entrypoint, purge all root logger handlers and attach `NullHandler()` to sub-loggers with `propagate = False`; (2) Strictly enforce `if len(success_list) == 0: return 0` (silent exit, zero stdout bytes); (3) Only print summary report when `len(success_list) > 0`. |
| Imported helper modules calling `StreamHandler(sys.stdout)` inside thread workers leak sub-module logs to Telegram | When helper modules (like `run_add_2fa_remaining.py`) configure `logging.StreamHandler(sys.stdout)` internally, calling them inside worker threads bypasses global redirects and dumps 30KB-40KB of raw connection/error logs into stdout. Fix: (1) Pre-emptively configure `NullHandler()` on helper loggers (`logging.getLogger('Add2FA').handlers = [logging.NullHandler()]`, `propagate = False`); (2) Wrap worker execution in dual context: `with contextlib.redirect_stdout(_dummy_f), contextlib.redirect_stderr(_dummy_f):`; (3) Scrub all handlers pointing to `sys.stdout` before launching `ThreadPoolExecutor`. |
| ADB unknown package warning (e.g. Samsung Pay / spay / spaymini) treated as non-empty stdout in no_agent cron | When watchdogs execute ADB package commands (`pm disable-user com.samsung.android.spay`, `pm list packages`), devices lacking the package return `Error: java.lang.IllegalArgumentException: Unknown package...` on stdout/stderr. In `no_agent: true` cron, even 2 lines of ADB warnings trigger Telegram message delivery. Fix: redirect stderr and filter stdout of package management commands (`stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`) or check package presence via `pm list packages <pkg>` before attempting disabling. |
| TikTok Switcher logout subagent evaluates empty XML Element as False in Python | In Python `xml.etree.ElementTree`, an Element without child elements evaluates to `bool(elem) == False`. Checking `if not target_node:` triggers falsely even when the element is found, breaking automated account switcher selection during parasite logout. Fix: Always use explicit identity check `if target_node is None:`, or bypass slow XML dumping in favor of deterministic coordinate taps for known switcher account positions. |
| ADB server launched via `.bat` (`adb -a nodaemon server`) leaves visible cmd window streaming USB transport/auth trace logs on screen | Running `start "" /b adb.exe -a nodaemon server` inside a batch file keeps `cmd.exe` open indefinitely and dumps live handshake logs (`read/write thread spawning`, `fetching keys`, `Calling send_auth_response`, `offline` -> `device`) across all farm phones (~80 devices), confusing users ("nhảy lung tung gì thế"). Clicking `X` kills `adb.exe` and disconnects all farm devices. Fix: Wrap execution in a headless VBS launcher (`WScript.Shell.Run """<path>\adb.exe"" -a nodaemon server", 0, False`) or configure Task Scheduler task to execute via `wscript.exe` with `SW_HIDE (0)` so ADB server runs 100% headless with zero console window. |
| Subprocess CLI rescan in no_agent watchdog prints intermediate stdout, mimicking partial farm alert ("sao có 16 máy") | When a rolling batch finishes (e.g. Tik 7 on 16 machines), calling a helper CLI (`tiktok_account_tracker.py --machines ...`) and printing its `res.stdout` via `print()` leaks the partial scan to Telegram. In `no_agent: true` cron, stdout = message. A partial report labeled `[FARM ALERT]` confuses users into thinking farm scale collapsed (16 machines instead of 160). Fix: redirect intermediate subprocess stdout/stderr to `sys.stderr` or file logger; keep `sys.stdout` 100% silent until final session summary. |
| Dual Delivery on no_agent cron: Script direct Telegram API + scheduler deliver stdout causes duplicate report | When a Python script calls direct HTTP Bot API (`send_farm_alert(report)` via `api.telegram.org`) AND ALSO prints `print(report)` to stdout, while Hermes cronjob is configured with `deliver: "telegram:-<chat_id>"` and `no_agent: true`, the user receives 2 identical messages simultaneously (one clean from Bot API, one prefixed with `Cronjob Response: <job_id>` from Hermes scheduler). Fix: Choose ONE delivery model. If using direct Bot API in script, configure cron with `deliver: local` and suppress report stdout. If relying on Hermes scheduler delivery (`deliver: telegram:...`), remove direct `send_farm_alert()` and only `print()` to stdout. |
| Exception double-fire & recurring cron crash alert storm ("sao cùng 1 lỗi nó bắn cả đống alert") | In top-level entrypoints (`if __name__ == '__main__': try: main() except Exception: alert(); raise`), calling a direct alert helper (`send_farm_script_alert`) AND THEN re-raising `raise` causes exit code 1. In Hermes cron (`deliver: telegram:...`), exit code != 0 delivers stderr as a 2nd alert (`⚠️ Cron '<name>' failed...`), doubling alerts every tick. When scheduled recurringly (e.g. `*/15`), 12 ticks × 2 alerts = 24 alerts spamming chat. Fix: (1) Choose ONE error delivery channel (do not direct-alert and then raise to scheduler deliver); (2) Add stateful exception debounce (e.g. `alert_state.json` keyed by hash of `script_name + error_reason` with >= 1h-4h cooldown); (3) Framework-level cooldown in `send_farm_script_alert()`. See `references/cron-dual-delivery-prevention.md`. |
| Chrome/browser process watchdog counts `--type=` sub-processes causing duplicate PID spam (e.g. 2 profiles reported as 13 PIDs) | In Windows, Chromium spawns 5–10 helper processes (`--type=renderer`, `--type=gpu-process`, `--type=utility`, `crashpad`) per browser profile. A watchdog scanning `psutil.process_iter()` without filtering sub-processes treats each child PID as an independent stuck instance, flooding stdout/Telegram with dozens of redundant PID lines. Fix: (1) Ignore child processes with `if any(arg.startswith('--type=') for arg in cmdline): continue`; (2) Deduplicate by profile ID or user-data-dir via `seen_profiles: set[str] = set()`; (3) Set high-frequency maintenance/janitor cronjobs (5–10m) to `deliver: local` so routine cleanups do not spam Telegram. |
| User questions cron alert output from an earlier tick before fix was deployed | When user forwards or asks about a confusing/spammy cron alert ("Clgt..."), don't assume the code has regressed or make redundant edits blindly. Inspect O(1) timestamp of the alert against script `mtime` and check `~/.hermes/cron/output/<job_id>/*.md` to confirm if the report was from a historical run prior to deployment. Verify current script behavior with `--dry-run` or live silent tick status before answering. |
| `taskkill exit=128` treated as fatal termination failure in `Stop-ChildProcessBounded` | When killing a hung process tree in watchdog scripts (e.g. `hermes-gateway-watchdog.ps1`), `taskkill.exe /PID <pid> /T /F` exits with code 128 if the process already terminated or PID is invalid. Unconditionally throwing `$terminationFailure` jumps to `catch`, aborting watchdog execution before restarting the service and causing persistent service downtime (~1h). Fix: check if `$Process.HasExited` or if exit code is 128, treat termination as successful, clear `$terminationFailure` before the throw check. |
| `taskkill` fails with `Access is denied` on UAC-elevated target processes | Background watchdogs/cron running at standard Medium Integrity cannot terminate High Integrity (Run as Administrator) processes like `xiaowei.exe` via `taskkill` or `Stop-Process` due to Windows UAC integrity level isolation and UIPI. Fix: Implement fallback to WMI/CIM termination: `Get-CimInstance Win32_Process -Filter "Name = 'target.exe'" \| Invoke-CimMethod -MethodName Terminate`. See `references/windows-uac-elevated-process-termination-fallback.md`. |
| OpenBLAS memory allocation failure (`VirtualAlloc` failed after 10 retries) crashes Python scripts without traceback | On high-core Windows hosts (e.g. 56+ cores), scripts importing `openpyxl`, `numpy`, or `scipy` trigger OpenBLAS thread pool allocations for all cores. Under memory fragmentation/commit charge, OpenBLAS fails `VirtualAlloc` and calls `exit(1)` directly in C code. Fix with 3-tier defense: (1) Set `OPENBLAS_NUM_THREADS="1"` at top of Python script before imports; (2) Inject `OPENBLAS_NUM_THREADS="1"` in scheduler subprocess environment (`_run_job_script`); (3) Set Windows User environment variable `OPENBLAS_NUM_THREADS=1`. |
| Sequential ADB health probing/healing across large dual-cluster farm (80-140+ devices) exceeds watchdog deadline | Probing `ip -4 addr show wlan0` sequentially over 140 devices across local and remote ADB hosts (`192.168.110.119:5037`) takes several minutes, easily breaching cron execution timeouts. Fix: Dispatch device checks via `concurrent.futures.ThreadPoolExecutor(max_workers=20)`. Wrap per-device probe & toggle recovery into an isolated function returning healed status. Total dual-cluster farm scan drops to <7s while preserving the silent watchdog pattern (zero stdout when all devices connected). |
| Unmocked `psutil.process_iter` in watchdog unit tests and inverted short-circuit flag checks cause 30s+ timeouts on Windows | (1) Evaluating `if is_feed_runner_active() and not args.dry_run:` evaluates the left-hand function call first before checking `dry_run`, executing expensive process enumeration even under `--dry-run`. Always short-circuit with flags first: `if not args.dry_run and is_feed_runner_active():`. (2) In pytest test suites, `psutil.process_iter(['name', 'cmdline'])` iterates every OS process, triggering slow PEB/cmdline queries and permission retries on Windows that easily exceed 30s test limits. Unit tests for watchdog entrypoints MUST explicitly mock process/lock probes (`patch.object(watchdog, 'is_feed_runner_active', return_value=False)`, `patch.object(watchdog, 'has_active_device_locks', return_value=False)`). |
| Auto-healer watchdog prints routine successful remediation actions to stdout, triggering recurring Telegram spam | When an auto-healing watchdog (app provisioner, wifi healer, screen/app healer) detects an anomaly and successfully fixes it (e.g. installed missing package, restored screen timeout), this is routine background maintenance, NOT a human alert. Printing `Completed Provision Actions` to stdout causes Hermes `no_agent: true` cron to deliver a `Cronjob Response` message every tick. Fix: (1) Log successful remediation actions to local runtime log (`D:\Taadaa\runtime\<name>.log`) and keep stdout 100% EMPTY (`sys.exit(0)`); (2) Reserve stdout strictly for unrecoverable errors (`errors`) requiring human intervention; (3) Default fleet maintenance / auto-healer cronjobs to `deliver: "local"`; (4) Schedule heavy device-inventory scans at low frequency (`0 4 * * *` daily or hourly, never `*/5 * * * *`). See `references/silent-watchdog-pattern-and-telegram-spam-prevention.md` (Section 23). |
| Multi-stage lifecycle watchdog summary masks errors via flat truncation and stage-vs-status mismatches | When a periodic reporting script aggregates failures across multi-stage pipelines (e.g. Login -> Reg -> OAuth -> Change Info) into a flat list and slices with `[:N]`, high-frequency failures in one stage (e.g. 198 Codex OAuth retries) crowd out critical low-frequency errors in upstream stages (e.g. 33 Hotmail Login auth failures), hiding them in the truncated summary. Additionally, checking `elif stage == 'DONE'` when the supervisor stores `stage: 'CHANGE_INFO'` and `status: 'DONE'` falsely reports 0 completed accounts ('Đã hoàn thành toàn bộ chu kỳ: 0'). Fix: (1) Always bucket failures by stage/subsystem (`Counter` or dict), report counts per stage, and display top samples per stage; (2) Check both `status in ('DONE', 'COMPLETED')` and stage indicators for cycle completion; (3) Do not assume absence of alerts means healthy execution without verifying state-machine BLOCKED unblock rules. See `references/multi-stage-lifecycle-watchdog-reporting-and-stage-status-parity.md`. |
| Scheduled dual-PC reboot without AutoAdminLogon freezes interactive services at Windows sign-in screen | On headless Windows hosts running farm/interactive tasks (`LogonType = Interactive`), rebooting when `AutoAdminLogon = 0` stops at the lock screen. SSH service starts but interactive tasks (`Hermes_Gateway`, startup `.vbs` loops, user ADB transport) never run. Furthermore, rebooting the controller PC before the remote host breaks SSH and leaves the remote un-rebooted. Fix: (1) Configure `AutoAdminLogon = 1` with `DefaultUserName` and `DefaultPassword` (mandatory if account has password, even if PasswordRequired=No); (2) Controller triggers remote reboot via SSH first, verifies dispatch, then schedules local reboot with grace delay; (3) Confine reboots strictly to the farm dead-zone (04:30 - 05:00 AM). See `references/dual-pc-scheduled-reboot-and-autologon-trap.md`. |
| Single-layer reboot startup fails to heal mid-session worker crashes (or cron watchdog without startup fails across reboot) | Relying solely on `shell:startup` leaves background workers (downloader, renderer) dead if they crash mid-day from network/DB errors; relying solely on cronwatchdogs can miss early startup or stack multiple instances if ticks overlap. Fix: Deploy the Dual-Tier pattern: Tier 1 (Windows Startup headless `.vbs` launcher via `WScript.Shell.Run ..., 0, False`) for boot survival + Tier 2 (Hermes cron `*/15 * * * *`, `deliver: local`) for crash auto-heal. Protect the worker daemon with non-blocking kernel lock `msvcrt.locking` to eliminate race conditions between boot and cron triggers. See `references/dual-tier-reboot-survival-and-daemon-watchdog.md`. |
| Blind USB controller reset before batch scripts disrupts active farm devices | Resetting USB Host Controller when fleet is busy drops all active ADB sessions. Furthermore, initial launch stagger does not prevent phase drift during long sessions where concurrent screencaps saturate USB 2.0. Fix: implement 2-tier `safe_usb_guard.py` — unconditionally block reset if any device in `~/.codex/device-locks/` has an active lock with alive owner process; when fleet is 100% idle, probe `adb devices` with 8s timeout and only trigger `reset_usb_bus.bat` if ADB is hung or offline device count dropped below threshold |
| Multi-host / dual-cluster shared watchdog identifies host via filesystem path existence (`os.path.exists`) | Checking a directory path (e.g. `if os.path.exists(r"D:\video goc may 2"): host = "ADMIN"`) to determine machine role causes catastrophic misdetection if a test folder or synced backup exists on the controller (Kibe). On Kibe, the script thought it was on Admin, resulting in missing Kibe metrics and sending Admin-only partial reports to Farm Alert. Fix: ALWAYS determine host identity via OS environment variables (`os.environ.get("USERNAME").lower()` in ('admin', 'kibe')) or `socket.gethostname()`. Never use filesystem directory presence as host discriminator. See `references/dual-cluster-host-detection-pitfall.md`. |
| Building/committing audit or watchdog script on disk without registering scheduler cronjob ("Ủa bữa có làm bộ lọc... sao đéo thấy chạy") | Building core logic, tests, and committing to git without executing `cronjob(action='create')` leaves the watchdog orphaned on disk. Task is INCOMPLETE until registered in scheduler, verified in `cronjob action=list`, and validated via a test tick. Furthermore, distinct watchdog scopes must not be conflated: Video Inventory Depletion (file `{N+1}.mp4` missing in folder) vs. Account Upload Freshness SLA (>7d / >14d stale snapshot). Stale alert scripts delivering text must exit code `0` with stdout, avoiding non-zero exit codes that trigger scheduler crash wrappers. See `references/watchdog-cron-registration-and-upload-sla-discipline.md`. |

---

## References

- `references/watchdog-cron-registration-and-upload-sla-discipline.md` — Kỷ luật đăng ký cronjob khi triển khai watchdog/audit mới, phân biệt Media Inventory vs Account Freshness SLA, và quy chuẩn exit code 0 khi deliver alert qua no_agent: true.

- `references/phone-farm-usb-bus-saturation-and-controller-reset.md` — Khắc phục nghẽn bus USB 2.0 (EHCI), tràn endpoint, và script reset controller không cần reboot PC trên dàn farm 80+ thiết bị.
- `references/dual-cluster-host-detection-pitfall.md` — Multi-host watchdog host detection pitfall: avoiding filesystem path discrimination in favor of OS username/hostname.
- `references/dual-tier-reboot-survival-and-daemon-watchdog.md` — Dual-tier reboot survival (Windows Startup headless `.vbs` + Hermes cron periodic watchdog) with kernel-level `msvcrt` single-instance locking for background heavy workers (downloader, renderers).
- `references/dual-pc-scheduled-reboot-and-autologon-trap.md` — Dual-PC (Controller + Remote Host) scheduled reboot orchestration order, farm dead-zone window (04:30 - 05:00 AM), and Windows AutoAdminLogon interactive task recovery.
- `references/openblas-memory-allocation-high-core-windows.md` — OpenBLAS/MKL thread pool allocation failure on high-core Windows hosts (Dual CPU 56 cores), root cause analysis, and 3-tier defense implementation.
- `references/telegram-message-length-limit-and-line-aware-chunking.md` — Telegram API 4096-character limit (HTTP 400 Bad Request message is too long) in long farm watchdogs & line-aware auto-chunking pattern.

- `references/multi-shift-silent-watchdog-state.md` — Multi-shift silent watchdog pattern: dynamic shift naming (Sáng/Trưa/Tối) and shift-isolated state management (`finished_shifts`) preventing premature whole-day lockouts and confusing report labels.
- `references/midnight-boundary-silent-watchdog-deadlock.md` — Detailed post-midnight boundary alignment for silent watchdogs on Hermes cron, avoiding dropped final summary reports.

- `references/windows-zero-flicker-console-suppression.md` — Complete 3-tier guide to eliminating flashing cmd/conhost windows on Windows (VBScript SW_HIDE launcher, in-process CIM probes, Python sitecustomize.py CREATE_NO_WINDOW hook).
- `references/hermes-stale-watchdog-subagent-coordination.md` — Hermes stale watchdog coordination with coordinator phase, 15m worker budget, and dispatch-timestamp filtering for subagents.
- `references/windows-uac-elevated-process-termination-fallback.md` — Windows UAC elevated (Run as Administrator) process termination fallback in watchdogs via WMI/CIM `Invoke-CimMethod -MethodName Terminate` when `taskkill` is denied access.
- `references/omniroute-watchdog-case-study.md` — Full reproduction of the OmniRoute watchdog fix (this session), including provider-error isolation, PID/listener ownership checks, and health-degraded vs hard-down restart evidence
- `references/9router-watchdog-comparison.md` — Comparison with 9Router watchdog patterns
- `references/hardware-proxy-healing-and-anti-flapping.md` — Auto-healer patterns for hardware proxy/modem pools: Single-Instance lock, per-target cooldown, max heals cap, and API request spacing.
- `references/silent-watchdog-logging-and-reporting.md` — Chuẩn cấu hình logging cho Watchdog script: FileHandler mặc định cho log file, StreamHandler(sys.stdout) chỉ bật qua cờ `--verbose`, giữ stdout rỗng khi không có việc để ngăn Hermes scheduler gửi tin nhắn rác Telegram.
- `references/module-level-logging-basicconfig-leak-prevention.md` — Phòng ngừa ô nhiễm Root Logger khi import helper scripts khiến các log thư viện con (AdbClient, requests) bị leak ra stdout trong cronjob no_agent=True.
- `references/gpm-oauth-captcha-stdout-leak-prevention.md` — Triệt tiêu rò rỉ log reCAPTCHA/Playwright ra stdout khi chạy GPM OAuth pool feeder trên cronjob no_agent=True.
- `references/farm-watchdog-stdout-cleanliness.md` — Quy chuẩn giữ sạch stdout cho silent watchdog (`no_agent=True`), xử lý rò rỉ log đa luồng, cảnh báo ADB unknown package và lỗi boolean XML element.
- `references/no-agent-cron-report-formatting-and-stdout-separation.md` — Chuẩn tách luồng stdout/stderr và format báo cáo Telegram Markdown trực quan cho cronjob no_agent=True (tránh log tiến trình thô "sida khó hiểu", helper clean tên model, icon thứ tự ưu tiên, non-blocking ping max_tokens).
- `references/cron-dual-delivery-prevention.md` — Cơ chế phòng ngừa báo kép (Dual Delivery) khi kết hợp script direct Bot API và Hermes cron scheduler `no_agent=True` deliver stdout.
- `references/silent-watchdog-pattern-and-telegram-spam-prevention.md` — Silent watchdog patterns for Hermes cron (`no_agent=True` stdout semantics, preventing multi-batch Telegram spam).
- `references/multi-stage-lifecycle-watchdog-reporting-and-stage-status-parity.md` — Multi-stage lifecycle watchdog reporting, per-stage bucketed failure display, and status vs stage parity in state-machine pipelines.
- `templates/single_instance_lock.py` — Reusable, cross-platform kernel-level single-instance lock class (`msvcrt` on Windows, `fcntl` on Unix).