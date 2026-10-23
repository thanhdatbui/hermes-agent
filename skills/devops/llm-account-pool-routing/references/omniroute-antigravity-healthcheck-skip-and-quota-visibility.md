# OmniRoute Antigravity Health-Check Skip & Quota Visibility Management

## 1. Cosmetic "Token Expired" vs True Session Invalidation

### Root Cause & Dynamics
- **Google OAuth Access Token Lifecycle:** Google OAuth access tokens have a strict 3,600s (1-hour) time-to-live.
- **Proactive Sweep Skip Gate:** In `src/lib/tokenHealthCheck.ts`:
  ```typescript
  if (!conn.isActive) return;
  ```
  When an account is deactivated (`isActive: false`) manually or via batch operations, OmniRoute ceases proactive token refresh for that connection.
- **Cosmetic Expiration Warning:** Once 1 hour elapses, the access token expires naturally. The Dashboard surfaces a red "Token expired" warning next to the connection.
- **Diagnostic Verification (Prove Session Is Alive):**
  Never assume "Token expired" indicates an invalidated session or revoked OAuth grant (`invalid_grant`). Send a live probe targeting the connection ID:
  ```bash
  curl -X POST http://127.0.0.1:20129/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "x-omniroute-connection-id: <connection_id>" \
    -d '{"model": "antigravity/gemini-3.8-flash-tiered", "messages": [{"role": "user", "content": "ping"}]}'
  ```
  If this returns HTTP 200 OK, the refresh token is 100% valid; OmniRoute's reactive refresh path (`tokenRefresh.ts`) successfully minted a fresh token on demand.

---

## 2. Proactive Health-Check Sweep Opt-Out

To prevent OmniRoute's proactive background sweeps from touching, clobbering, or false-deactivating Antigravity / AGY connections, configure the native skip list:

### Configuration Mechanics
- **Mechanism:** In `src/lib/tokenHealthCheck.ts:296`:
  ```typescript
  function getHealthCheckSkipProviders(): Set<string> {
    const raw = process.env.OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS || "";
    return new Set(raw.split(",").map(s => s.trim().toLowerCase()).filter(Boolean));
  }
  ```
- **File 1 — Runtime Environment (`AppData/Roaming/omniroute/server.env`):**
  ```env
  OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS=antigravity,agy
  ```
- **File 2 — Supervisor Persistence (`omniroute_watchdog.ps1`):**
  ```powershell
  $psi.EnvironmentVariables["OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS"] = "antigravity,agy"
  ```
- **Effect:** Antigravity connections remain strictly on the reactive on-demand refresh path (`open-sse/services/tokenRefresh.ts`) protected by serialized mutexes, preventing sweep rate-limits and unwanted state transitions.

---

## 3. Server-Side Quota Row Visibility (`quotaVisibility`)

### The Problem
Google Cloud Code API (`v1internal:fetchAvailableModels`) returns the fixed catalog of models hosted on the Google account, which includes Claude models (`claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `claude_gpt_weekly`). Google does not provide an API query parameter to exclude Claude. Consequently:
- Cards clutter with Claude rows that the operator does not care about.
- When Claude quota exhausts on Google, the card falsely turns red/alert even if Gemini Flash/Pro has 100% quota remaining.

### The Solution: Global Persisted Quota Visibility
OmniRoute supports a persistent server-side filter in the `settings` table (`PATCH /api/settings`), ported from upstream 9router#2371.

Send a single PATCH request to apply the filter globally to all Antigravity and AGY cards:
```bash
curl -X PATCH http://127.0.0.1:20129/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "quotaVisibility": {
      "antigravity": {
        "hidden": [
          "claude-sonnet-4-6",
          "claude-opus-4-6-thinking",
          "claude_gpt_weekly",
          "claude-3-5-sonnet",
          "claude-3-7-sonnet"
        ]
      },
      "agy": {
        "hidden": [
          "claude-sonnet-4-6",
          "claude-opus-4-6-thinking",
          "claude_gpt_weekly",
          "claude-3-5-sonnet",
          "claude-3-7-sonnet"
        ]
      }
    }
  }'
```

### Operational Impact
1. **Instant Card Cleanup:** On `/dashboard/usage`, all Claude quota bars disappear across all Google cards without manual per-card clicking.
2. **True Health Color:** The card's worst-status indicator (`getWorstStatus`) evaluates only visible rows. Exhausted Claude quota will no longer flag Google accounts as red/critical.
3. **Permanent Durability:** Saved in SQLite `settings` table; survives browser reloads, OmniRoute process restarts, and PC reboots.
