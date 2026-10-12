# OmniRoute Combo HTTP 503: All Targets Skipped Pre-Dispatch

## Symptom
Incoming requests to a combo (e.g. `omni-worker`) receive HTTP 503 in bursts:
```json
{
  "error": {
    "message": "Service temporarily unavailable: all targets were skipped by pre-dispatch filters",
    "type": "service_unavailable",
    "code": "ALL_TARGETS_SKIPPED"
  }
}
```
In the Dashboard / Call Logs, duration is near zero or very low (<2s), token usage is 0, and no upstream requests appear in outbound network logs.

## Root Cause Architecture (`open-sse/services/combo.ts`)
1. **Single-Provider Dependency in Combos**:
   When all tiers/targets in a combo (e.g. `ag-gemini-pool-3`, `ag-gemini-free-pool`, `ag-gemini-free-pool-37`, `ag-sonnet`) resolve to accounts belonging to the **same upstream provider** (`antigravity`).
2. **Resilience Cascade**:
   - Bursts of requests encounter upstream rate limits (HTTP 429) or proxy timeouts.
   - OmniRoute's resilience system trips:
     - `recordProviderCooldown(provider, connectionId, ...)` sets global cooldown on `provider antigravity`.
     - `recordModelLockoutFailure(...)` locks specific models under that provider.
3. **Pre-Dispatch Evaluation**:
   - `executeTarget` checks `isProviderInCooldown(provider)` and `isModelLocked(...)` before attempting any upstream call.
   - If every single target in `orderedTargets` is skipped, `recordedAttempts === 0`.
   - The loop exhausts all set retries without a single attempt, returning `503 ALL_TARGETS_SKIPPED`.

## Diagnostic Playbook (SQLite & Logs)
1. **Locate SQLite & Storage**:
   - Storage path: `C:\Users\Kibe\.omniroute\storage.sqlite`
   - Application logs: `C:\Users\Kibe\.omniroute\logs\application\app.<timestamp>.log`
   - Request artifacts: `C:\Users\Kibe\.omniroute\call_logs\<YYYY-MM-DD>\<artifact_relpath>.json`
2. **Query 503 Logs in SQLite**:
   ```sql
   SELECT timestamp, status, model, correlation_id, error_summary 
   FROM call_logs 
   WHERE status = 503 
   ORDER BY timestamp DESC LIMIT 20;
   ```
3. **Inspect Application Log for Skips**:
   Grep/search for:
   - `Skipping <model> — provider <provider> in global cooldown`
   - `Skipping <model> — model locked by resilience (cooldown active)`
   - `hard-bound connection <id> unavailable; refusing sibling selection`
   - `Combo loop safety timeout (600000ms) reached without a terminal response — force-terminating`

## False "Server Crash" vs Real Routing Outage Triage
When user/agent reports "OmniRoute sập / không phản hồi":
1. **Process Liveness Verification**:
   OmniRoute process (PID `node.exe scripts/dev/run-next.mjs start`) often **did NOT crash**. `/api/health` still returns `{"status":"ok"}`.
   - Use `psutil` in Python (avoid `subprocess`/`netstat`/`curl` if guarded):
     ```python
     import psutil
     for p in psutil.process_iter(['pid', 'name', 'create_time', 'cmdline']):
         if p.info['name'] == 'node.exe':
             print(p.info['pid'], p.info['create_time'], p.info['cmdline'])
     ```
2. **Per-Minute Incident Timeline via SQLite**:
   Aggregate failures by minute to pinpoint exact collapse window and cascading statuses:
   ```python
   import sqlite3
   conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
   cur = conn.cursor()
   cur.execute('''
       SELECT strftime('%Y-%m-%d %H:%M', timestamp) as m, status, count(*)
       FROM call_logs
       WHERE timestamp >= datetime('now', '-2 hours')
       GROUP BY m, status ORDER BY m ASC
   ''')
   for r in cur.fetchall(): print(r)
   ```
3. **Dual Upstream Failure Cascade Pattern**:
   - `Antigravity` accounts hit `403` (auth lost/invalidated) or `429` (individual quota reset delay ~60m) on Claude/Gemini.
   - Simultaneously `ChatGPT Web` accounts hit `502` ("You've hit your limit") or `499` (request aborted > 45s).
   - This trips circuit breakers across ALL fallback targets, producing:
     - Immediate `503 ALL_TARGETS_SKIPPED` bursts.
     - 10-minute hanging requests terminated only by `Combo loop safety timeout (600000ms)`.
4. **Guarded Health Check Verification**:
   Probe via Python `urllib.request`:
   ```python
   import urllib.request, json
   res = urllib.request.urlopen('http://127.0.0.1:20129/api/monitoring/health')
   data = json.loads(res.read().decode())
   print('Circuit breakers:', data.get('circuitBreakers', {}))
   ```

## Hot Recovery & Long-Term Prevention
1. **Hot Circuit Breaker / Cooldown Reset**:
   ```bash
   curl -X DELETE http://localhost:20129/api/monitoring/health
   ```
   This resets all provider circuit breakers and clears health payload cache.
2. **Multi-Provider Combo Architecture**:
   Never build combos where 100% of fallback tiers depend on a single upstream provider. Always include a terminal safety fallback tier pointing to an isolated alternative provider (e.g. `chatgpt-web` via `gpt-5.6-luna-free` or OpenRouter free models).
