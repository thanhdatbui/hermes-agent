# OmniRoute Combo Pool & Antigravity/Gemini Routing

## Architecture & Ports

- **9Router**: `:20128` (legacy/remote LLM proxy, e.g. `http://192.168.110.123:20128/v1`).
- **OmniRoute**: `:20129` (active local Next.js/Open-SSE proxy, `http://127.0.0.1:20129/v1`).
  - Active runtime data: `C:\Users\<user>\.omniroute\storage.sqlite` (NOT `AppData/Roaming/omniroute/storage.sqlite` when running from dev/local repo).
  - Source repository: `C:\Users\<user>\OmniRoute`.

## Combo Pool Architecture (`ag-gemini-pool-3`)

```
Hermes Agent (Telegram Gateway / CLI)
  → /v1/chat/completions (port :20129)
    → Combo Service (open-sse/services/combo.ts)
      → Strategy: 'priority' (Strict sequential priority; never round-robin or random)
      → Target 1: pool-1 (Account 1: dokieu0409...)
      → Target 2: pool-2 (Account 2: marcusep...)
      → Target 3: pool-3 (Account 3: dinhlan2...)
```

### Key Routing & Failover Rules

1. **Strategy: `priority`**:
   - Always attempts Target #1 first.
   - If Target #1 is at concurrency capacity (`max_concurrent`), busy, or returns a rate limit/quota/transient error, it fails over immediately to Target #2, then Target #3.
2. **Concurrency Gate (`isAccountSemaphoreFull`)**:
   - Checked via `lookupPositiveCap(connectionId)` (`open-sse/services/combo/concurrencyCaps.ts`).
   - If active in-flight requests on an account >= `max_concurrent` (typically 2-3 slots per account), the combo marks the target `skipped_before_dispatch` with reason `concurrency_cap` and advances to the next account.
3. **Queue & Timeout Settings**:
   - `queueTimeoutMs: 120000` (120 seconds queue time before timing out).
   - `failoverBeforeRetry: true`: Failover happens before retrying the same connection.
   - `maxRetries: 0`, `maxSetRetries: 0`: Prevents retrying a rate-limited connection in-place.
4. **Thought Signature Preservation (`gemini_thought_signatures`)**:
   - Stored in `key_value` table with TTL (`expiresAt`).
   - Essential for Gemini 2.0/3.x Flash thinking models so multi-turn tool calling does not drop thought context or fail signature verification.

## Concurrency Cap vs Rate Limit Protection

| Mechanism | Controlled By | Purpose & Behavior |
| :--- | :--- | :--- |
| **`max_concurrent`** | `provider_connections.max_concurrent` + `combo.ts` (Semaphore) | Hard ceiling on concurrent in-flight requests per account. When saturated in a `priority` combo, it triggers fail-fast skip to the next target. |
| **`rate_limit_protection`** | `provider_connections.rate_limit_protection` + `rateLimitManager.ts` (Bottleneck) | Adaptive rate limiter. Reads response headers (`x-ratelimit-*`, `retry-after`), auto-adjusts minimum delay between requests (`minTime`), pauses on 429 cooldowns, and supervises stuck queues with a wedge watchdog. |

## Data-Plane Egress Isolation vs Dual-Layer Direct Fallback

| Flow Layer | Function | Direct Fallback on Dead Proxy? | Rationale |
| :--- | :--- | :--- | :--- |
| **Data-Plane (Chat / LLM Gen)** | `runWithProxyContext` | ✅ **Layer 1: Provider Pool (69 Ports) → Layer 2: Direct Fallback (`PROXY_FAIL_OPEN=true`)** | Provider-level pool with 69 rotated proxy ports (Mobi + Mirotik) handles per-port failures with Fast-Fail (<1.5s). If the entire proxy cluster fails, `PROXY_FAIL_OPEN=true` falls back to host direct connection so agent sessions never abort mid-turn. |
| **Control-Plane (Auth / Refresh)** | `runWithProxyContextOrDirect` | ✅ **Yes (`OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK=true`)** | Token refresh and connection probes degrade to direct connection if proxy is unreachable so credentials remain valid. |

### Dual-Layer Proxy Resilience Architecture (2026-08-27)
1. **Layer 1: Shared Provider-Scope Proxy Pool (69 Ports)**
   - All active proxy ports (33 Mobi `test.taadaa.click:5101..5138` + 35 Mirotik `mirotik1.taadaa.click:10001..10035` + 2 KhoaLee) are loaded in `proxy_registry` and assigned to `scope='provider', scope_id='antigravity'` in `proxy_assignments`.
   - **Rotation:** `proxy_scope_rotation` sets `strategy='round-robin'` so Antigravity accounts automatically cycle egress across all healthy ports.
   - **Single Port Failure:** Fast TCP reachability probe (< 1.5s) detects dead ports immediately and skips to the next healthy port or combo target without blocking.
2. **Layer 2: Fail-Safe Direct IP Fallback**
   - When entire proxy infrastructure goes down, `PROXY_FAIL_OPEN=true` and `directFallbackOnUnreachable` in `open-sse/utils/proxyFetch.ts` allow in-flight requests to execute via host Direct IP rather than throwing `503 PROXY_UNREACHABLE` / `ALL_TARGETS_SKIPPED`.
   - Configured in `OmniRoute/.env` and injected by `AppData/Roaming/omniroute/omniroute_watchdog.ps1`.

### Proxy Fast-Fail & Cascade Outage (Historical Root Cause)
- **Mechanism (`open-sse/utils/proxyFetch.ts`):** `isProxyUnreachable` fires an optimistic TCP reachability probe. If the assigned proxy host/port drops or refuses connections, the request previously failed hard with `[Proxy Fast-Fail] Proxy unreachable: <proxy_url>` (`PROXY_UNREACHABLE` / HTTP 503).
- **Cascade Behavior in Combo (`ag-gemini-pool-3`):**
  1. Target 1 (Account A, Proxy A) fails fast with `PROXY_UNREACHABLE`.
  2. Combo advances to Target 2 (Account B, Proxy B). If Proxy B is on the same downed proxy host, Target 2 fails fast.
  3. Combo advances to Target 3 (Account C, Proxy C). Target 3 fails fast.
  4. With all targets exhausted/skipped, OmniRoute returns `HTTP 503: ALL_TARGETS_SKIPPED`.
  5. Hermes Gateway aborts the in-flight agent turn with `⚠️ The model provider failed after retries...`.
- **Fix:** Switched from 1-to-1 account pinning to the 69-port shared provider pool + `PROXY_FAIL_OPEN=true` direct fail-safe.

## Incident Pattern: `503 ALL_TARGETS_SKIPPED`

### Symptom
- **Telegram / Gateway Client:** `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- **OmniRoute `call_logs`:** HTTP `503` with error `[503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters` (`code: ALL_TARGETS_SKIPPED`).

### Root Cause
During high-traffic bursts (e.g. multi-step automation, multiple subagents, concurrent sessions), if all targets in a `priority` combo reach their `max_concurrent` capacity simultaneously:
1. Target #1 is skipped by the concurrency gate (`isAccountSemaphoreFull`).
2. Target #2 is skipped by the concurrency gate.
3. Target #N is skipped by the concurrency gate.
4. Since `recordedAttempts === 0` (no upstream was called), OmniRoute returns `503 ALL_TARGETS_SKIPPED` immediately.

### Remediation
1. Increase `max_concurrent` on Antigravity accounts (e.g. from 3 to 4–5 slots per account) if accounts can safely absorb higher parallel load.
2. Add additional Antigravity accounts to the pool combo.

## Read-Only Inspection Commands

### Check Active Combo Definition
```python
import sqlite3, json
conn = sqlite3.connect('file:///C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
cursor = conn.cursor()
cursor.execute('SELECT id, name, data FROM combos WHERE name="ag-gemini-pool-3"')
for row in cursor.fetchall():
    print(row[1], json.dumps(json.loads(row[2]), indent=2))
```

### Check Provider Connections & Quotas
```python
import sqlite3
conn = sqlite3.connect('file:///C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
cursor = conn.cursor()
cursor.execute('SELECT id, name, email, priority, is_active, max_concurrent, rate_limit_protection, last_error FROM provider_connections WHERE provider="antigravity"')
for row in cursor.fetchall():
    print(row)
```

### Inspect Recent Errors in Call Logs
```python
import sqlite3
conn = sqlite3.connect('file:///C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
cursor = conn.cursor()
cursor.execute('SELECT id, timestamp, status, model, connection_id, error_summary, duration FROM call_logs ORDER BY timestamp DESC LIMIT 20')
for row in cursor.fetchall():
    print(row)
```

### Diagnose Request Latency & Token Bloat (Profiling)
When requests feel slow, distinguish concurrency saturation (queueing/503 skips) from upstream single-request processing latency:
- **`max_concurrent`** limits total parallel requests; it does NOT slow down individual in-flight requests.
- **Latency Drivers**: Large context size (`tokens_in` > 150k takes 8–14s on Google backend for prefill TTFT), high reasoning budget (`gemini-3.7-flash-high`), and multi-turn agent tool loops.

```python
import sqlite3
conn = sqlite3.connect('file:///C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
c = conn.cursor()
c.execute('''
SELECT 
    CASE 
        WHEN tokens_in < 50000 THEN '< 50k tokens'
        WHEN tokens_in < 150000 THEN '50k - 150k'
        WHEN tokens_in < 300000 THEN '150k - 300k'
        ELSE '> 300k tokens'
    END as token_range,
    COUNT(*) as cnt,
    ROUND(AVG(duration), 0) as avg_ms,
    ROUND(MIN(duration), 0) as min_ms,
    ROUND(MAX(duration), 0) as max_ms
FROM call_logs
WHERE timestamp > datetime('now', '-24 hours') AND tokens_in > 0
GROUP BY token_range
ORDER BY avg_ms ASC
''')
for r in c.fetchall():
    print(r)
```

### Live Smoke Verification
```bash
curl -s -X POST http://127.0.0.1:20129/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer omni-test" \
  -d '{"model": "ag-gemini-pool-3", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 10}'
```
