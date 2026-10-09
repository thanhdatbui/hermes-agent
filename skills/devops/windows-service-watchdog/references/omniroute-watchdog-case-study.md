# OmniRoute Watchdog Case Study: Provider Errors vs Process Down

## Symptom
A Codex pool contained inactive/expired targets and produced upstream 401s. The watchdog later restarted OmniRoute after eight consecutive `/api/health` failures. The restart caused active streams to drop, but there was no evidence that a provider 401 directly killed the process.

## Confirmed evidence pattern
- `/api/health` was a minimal route returning JSON 200 without reading the provider pool, database, or upstream.
- Executor/combo handling kept provider 401/expired errors at request/target scope (fallback, cooldown, breaker, or request error); no direct process exit path was found.
- The watchdog treated every health timeout/non-200 as the same failure and restarted after 8 checks at 15-second intervals.
- A matching OmniRoute PID/listener check was absent before the original restart decision.

## Correct contract & Hung-Process Refinement
1. Keep liveness separate from provider/readiness health.
2. Identify the exact OmniRoute process by command signature and the listener owner for the target port.
3. For short transient load spikes (1–2 failed checks), emit `health_degraded` without restarting.
4. **Deadlock Ceiling (Anti-Zombie Rule):** CẤM reset `$consecutiveFailures = 0` vô điều kiện mỗi tick khi PID còn sống. Nếu `/api/health` fail liên tục >= 8 lần (khoảng 2 phút), coi process đã bị freeze/deadlock (vòng lặp selection, cạn buffer, crash 0xC0000409). BẮT BUỘC force-kill (`Stop-Process -Force`) và restart ngay.
5. Restart ngay khi process/listener vắng mặt sau ngưỡng hard-down (2–3 checks).
6. Preserve mutex, stop-file handling, startup grace, và post-start PID/listener verification.
7. Phía client Hermes: Đặt `agent.api_max_retries: 10` hoặc `12` để bot tự động backoff chờ 5–10 phút mà không rớt session chat của user khi proxy đang restart.

## Operational lesson
Quota, provider count, and provider test status are not process liveness. A bad pool target should be removed/cooldowned at routing scope, not healed by restarting the whole proxy. A restart watchdog must not convert a transient health probe failure into a process-wide outage.

## Follow-up Incident: Watchdog Zombie Freeze via Invoke-WebRequest

### Symptom
OmniRoute experienced intermittent latency spikes during high-concurrency combo fallback bursts (22–259 targets, 200k+ tokens), but the watchdog stopped supervising and failed to restart it. The watchdog process (`powershell.exe`) remained alive in Task Manager with an established TCP connection to port 20129, but had not emitted log lines for over 5 hours.

### Root Cause
PowerShell 5.1's `Invoke-WebRequest -TimeoutSec` relies on .NET Framework `HttpWebRequest`, where `-TimeoutSec` only bounds connection establishment. When OmniRoute's Node.js event loop is saturated during combo fallback loops, the TCP 3-way handshake succeeds (`ESTABLISHED`), but the HTTP response stream stalls. `Invoke-WebRequest` hangs indefinitely on `Stream.Read()`, freezing the single-threaded watchdog process in RAM without ever reaching the timeout or exception handler.

### Resolution
1. **Stream-Safe Probe & Singleton HttpClient:** Replace `Invoke-WebRequest` with `System.Net.Http.HttpClient` initialized with an explicit task cancellation timeout (`$client.Timeout = [TimeSpan]::FromSeconds(8)`). To prevent socket churn and ephemeral port exhaustion in `TIME_WAIT` over weeks of monitoring, maintain a script-scoped singleton instance (`Get-HttpClient`) reused across all cycles, disposed only in the script's `finally` block:
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

   function Test-OmniRouteAlive {
       try {
           $client = Get-HttpClient
           $res = $client.GetAsync("http://${HostAddr}:${Port}/api/health").GetAwaiter().GetResult()
           return ($res.StatusCode -eq [System.Net.HttpStatusCode]::OK)
       } catch {
           return $false
       }
   }
   ```
2. **Dual-Threshold Calibration:** Configure `$CheckIntervalSec = 15` and `$MaxConsecutiveFailures = 4` (60s). Transient degradation during burst fallbacks (1–2 checks) emits `health_degraded` without restarting, while persistent deadlock (>= 4 checks) triggers full child process cleanup and restart.
3. **Anti-Flapping Restart Budget:** Implement `Test-CanRestartOmniRoute` with a sliding window (e.g. max 3 restarts within 900s / 15 minutes). If persistent upstream network outages or proxy failures prevent recovery after 3 restarts, pause restarts and log `anti_flapping` to protect CPU and avoid restart thrash.
4. **RAM Reload Discipline:** Always kill the stuck watchdog PID (`Stop-Process -Force`) and re-launch via its VBScript launcher (`wscript.exe run_watchdog.vbs`) to ensure updated logic runs in RAM.
