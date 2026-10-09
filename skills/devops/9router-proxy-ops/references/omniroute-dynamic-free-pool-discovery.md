# Dynamic Free Pool Discovery & Dual-Layer Proxy Binding Pattern

## 1. Context & Problem
Free AI models from public aggregators (e.g. OpenRouter Free Tier, OpenCode) undergo continuous lifecycle turnover:
- Free models frequently degrade, hit rate-limits, get deprecation/404s, or impose strict client-origin blocks (e.g. OpenCode HTTP 403 `Error from provider (Console): OpenCode's free tier can only be used from within OpenCode`).
- Hardcoding free models directly into combo configs causes periodic cascade failures where requests stall or fail across dead endpoints.
- User Invariant Constraint: Certain families (e.g. `gemini-3.8`, `gemini-3.8-flash`) may be strictly prohibited from the Free combo to avoid unintended quota or architecture contamination.

## 2. Dynamic Discovery & Verification Architecture
A resilient free pool pattern requires a decoupled background watchdog script:

```
[OpenRouter / Catalog API] (https://openrouter.ai/api/v1/models)
           │
           ▼ Filter pricing == 0 && exclude prohibited models (gemini-3.8)
[Candidate Free Models]
           │
           ▼ Parallel Health-Check via Local Proxy (:20129)
           │ (Ping with short timeout, max_workers=2-4 to avoid rate-limiting)
[Live Verified Models] (HTTP 200 OK only, sorted by latency)
           │
           ▼ Top N Fast Free Models + Rock-solid Web Fallbacks (ChatGPT Web Free)
[PATCH Combo API] (http://127.0.0.1:20129/api/combos/<combo_id>)
```

## 3. Implementation Rules & Pitfalls

### Rule 1: Guarded Concurrency on Free Upstreams
- OpenRouter free tier and proxy connections throttle aggressive concurrent probes.
- **Pitfall:** Using `ThreadPoolExecutor(max_workers=8+)` triggers immediate 429 rate limits or timeouts, causing all candidate models to appear dead.
- **Fix:** Limit health-check concurrency to `max_workers=2..4` with per-request timeouts of 6–8 seconds.

### Rule 2: Anchor Fallbacks (Hybrid Redundancy)
- Always terminate the Free combo with high-resilience web sessions (e.g. `chatgpt-web/gpt-5.6-luna-free` and `chatgpt-web/gpt-5.6-sol-instant` from an internal pool of rotated accounts).
- If transient network jitter momentarily drops external free catalog models, the web fallbacks guarantee zero total outages.

### Rule 3: Strategy & Failure Isolation
- Strategy: `priority` (waterfall).
- Combo config settings:
  ```json
  {
    "maxRetries": 1,
    "retryDelayMs": 100,
    "targetTimeoutMs": 25000,
    "queueTimeoutMs": 1000,
    "stickyRoundRobinLimit": 1,
    "disableSessionStickiness": true,
    "maxGlobalAttempts": 8,
    "nestedComboMode": "execute",
    "failoverBeforeRetry": true
  }
  ```

### Rule 4: Verification Ping Post-Update
- After sending HTTP PATCH to `/api/combos/<id>`, execute a live verification completion request directly through the modified combo to verify that the active in-memory routing table responds with HTTP 200 OK. Step verification timeout should be $\ge 25s$ to account for fallbacks.

## 4. Dual-Layer Proxy Binding (Gán Proxy Pool 2 Lớp)
To protect external free upstreams (OpenRouter) from origin IP rate-limiting, bans, or Cloudflare flagging, attach a pool of rotated 4G/datacenter proxies across two layers in OmniRoute (`:20129`):

1. **Combo-Level (`scope='combo'`):**
   - Bind proxy pool to the target combo ID (`5a72c9bc-94d8-4e35-a9c6-51545cb73d7a`).
   - Strategy: `round-robin`.
2. **Provider-Level (`scope='provider'`):**
   - Bind proxy pool to provider `openrouter` with strategy `round-robin` and ensure `proxy_enabled = 1`.
3. **OmniRoute API Endpoints:**
   - Strategy: `PATCH /api/settings/proxies/pool` with `{"scope": "...", "scopeId": "...", "strategy": "round-robin"}`.
   - Assignment: `PUT /api/settings/proxies/pool` with `{"scope": "...", "scopeId": "...", "proxyId": "..."}`.
