# OmniRoute Proxy Resolution — Full Chain & Hash Distribution

## Complete 12-Step Resolution Chain (`src/lib/db/settings.ts` → `resolveProxyForConnection`)

In OmniRoute (`C:\Users\Kibe\OmniRoute`), proxy resolution follows this chain:

| Step | Scope | Requires | Key Detail |
|------|-------|----------|------------|
| 1 | Global `proxyEnabled` toggle | — | If false, skip to direct |
| 1.5 | Global `perKeyProxyEnabled` | — | Gates per-key resolution |
| 2 | API key (`proxy_assignments`, scope='apiKey') | `apiKeyId` | Only if per-key proxy enabled globally AND per-connection |
| 3 | Account (`proxy_assignments`, scope='account') | `connectionId` | Health-checks proxy; if unreachable → `resolveProviderPoolFallbackProxy` (hash dist) |
| 4 | Legacy key-level (`config.keys`) | `connectionId` | Legacy JSON config |
| 5-6 | Provider registry (`scope='provider'`) | `connectionRecord` + `proxyEnabled` | Needs real `provider_connections` row |
| 7 | Combo registry (`scope='combo'`) | `connectionRecord` + `proxyEnabled` | Scans all combos for matching provider |
| 8 | Legacy provider (`config.providers`) | `connectionRecord` + `proxyEnabled` | Legacy JSON config |
| **8.5** | **No-auth shared provider** | **No `connectionRecord`** | **For `opencode`/`mimocode` etc.** — calls `resolveNoAuthSharedProviderProxy()` which checks provider-level registry then legacy |
| 9 | Global registry (`scope='global'`) | — | Last registry check |
| 10 | Legacy global (`config.global`) | — | Legacy JSON config |
| **11** | **Auto-select fallback** | **`PROXY_AUTO_SELECT_ENABLED=true`** | **Picks ONE proxy from ALL registry, tests against `api.openai.com`, caches 5min in `PROXY_FALLBACK_CACHE`** |
| 12 | Direct | — | No proxy |

### ⚠️ No-Auth Provider Trap (Step 8.5 + 11)

**Problem:** No-auth providers (`opencode`, `mimocode`) use synthetic `connectionId = "noauth"`. No `provider_connections` row has `id = "noauth"`, so `connectionRecord` is NULL → Steps 2-8 ALL skipped.

Step 8.5 (`resolveNoAuthSharedProviderProxy`) only checks if the specific no-auth provider has a provider-level proxy in `proxy_assignments`. If not → falls to Step 11 (auto-select).

**Auto-select cache trap:** Step 11 picks ONE proxy, caches it in `PROXY_FALLBACK_CACHE` (5min TTL). BUT the proxy resolution cache in `proxyResolutionCache` (Map, no TTL) stores the RESOLVED proxy keyed by `"noauth::opencode"`. All 7 models in an `omni-free` combo share this same cache key → **all models use the same cached proxy**. When that proxy dies, all models fail with no rotation.

**Fix options:**
- Assign provider-level proxy pool (`scope='provider', scope_id='opencode'`) → `resolveScopePoolInternal` uses round-robin via `pickFromCandidates` — BUT the result is still cached by `resolveProxyForConnection`
- Disable auto-select for no-auth providers (they should go direct)
- Add TTL to `proxyResolutionCache` or invalidate on proxy failure

### ⚠️ OAuth / Codex Provider Proxy Trap (Step 3 vs Step 12 Direct Egress)

**Problem:** Khi tài khoản OAuth (như OpenAI Codex) được import qua `/api/oauth/codex/import-token` hoặc poll callback (`/api/oauth/codex/poll-callback`), cờ `proxy_enabled = 1` được tự động set trên bảng `provider_connections`. Tuy nhiên:
- `proxy_enabled = 1` chỉ là cờ cho phép resolve proxy, **KHÔNG TỰ GÁN PROXY**.
- Nếu không có dòng tương ứng trong bảng `proxy_assignments` với `scope = 'account'` (cho `connectionId`) HOẶC `scope = 'provider'` (cho `codex`), toàn bộ Steps 2-10 đều miss.
- Do `PROXY_AUTO_SELECT_ENABLED` mặc định `false`, Step 11 bị skip → OmniRoute rơi thẳng xuống **Step 12: `{ proxy: null, level: "direct" }`**.
- **Hậu quả:** Toàn bộ request gọi model qua connection Codex này sẽ **egress trực tiếp qua IP mạng nhà**, gây rò rỉ IP và nguy cơ bay dàn account OpenAI.

**Fix bắt buộc trong script automation:**
Mọi script sau khi nhận `conn_id` OAuth Codex bắt buộc phải:
1. Bóc `raw_proxy` từ profile GPM (`host:port:user:pass`).
2. Tra cứu `proxy_id` tương ứng qua `GET /api/settings/proxies`.
3. Gọi `PUT /api/settings/proxies/assignments` với `{ proxyId, scope: "account", scopeId: conn_id }`.
4. Gọi `PUT /api/providers/{conn_id}` với `{ proxyEnabled: true }`.

### Provider Pool Assignment for No-Auth Providers (Proven Fix)

**Pitfall: Don't assume a proxy pool can't work for a provider without checking ALL available pools.** MobiProxy (MobiFone mobile) can't reach `opencode.ai` (502), but MikroTik (FPT egress) CAN. Always test reachability before concluding.

**DB injection method** (direct SQLite, no OmniRoute restart needed):

```sql
-- 1. Get unique MikroTik proxies (dedupe mirotik_ prefixed)
-- In Node.js: db.prepare("SELECT id FROM proxy_registry WHERE host = 'mirotik1.taadaa.click' AND name LIKE 'mirotik_%' ORDER BY port").all()

-- 2. Insert into proxy_assignments
-- INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
-- VALUES ('<proxy_id>', 'provider', 'opencode', <position>, datetime('now'), datetime('now'))

-- 3. Bump registry generation to invalidate cache
-- UPDATE key_value SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)
-- WHERE namespace = 'proxyRegistry' AND key = 'generation'
```

**Verify rotation works:**
```sql
-- Check rotation state
SELECT cursor, strategy FROM proxy_scope_rotation WHERE scope = 'provider' AND scope_id = 'opencode';
-- cursor should advance with each request (round-robin)
```

**Reachability matrix (Taadaa infrastructure):**

| Proxy Pool | `opencode.ai` | `generativelanguage.googleapis.com` (AG) |
|-----------|---------------|------------------------------------------|
| MobiProxy (MobiFone mobile, 5101-5138) | ❌ 502/timeout | ✅ via OmniRoute undici |
| MikroTik (FPT egress, 10001-10035) | ✅ works | ✅ works |

**After assignment:** `resolveProxyForScopeFromRegistry("provider", "opencode")` → `resolveScopePoolInternal` → `pickFromCandidates` (round-robin) → rotates through all assigned ports. Combo `omni-free` now has working proxy rotation instead of shared egress single-point-of-failure.

### Pool Rotation: `pickFromCandidates` (round-robin default)

`resolveProxyForScopeFromRegistry` → `resolveScopePoolInternal` → `pickFromCandidates`:
- **round-robin** (default): cursor advances monotonically, wraps around pool size
- **random**: `crypto.randomInt` (unbiased)
- **sticky**: rotates after `stickyWindowMinutes`
- **latency**: picks lowest-latency candidate

Rotation state stored in `proxy_scope_rotation` table. Rotation only runs on **cache miss** — if proxy resolution is cached, rotation doesn't happen.

## Unreachable Account Proxy & Hotspot Problem

When an account proxy is configured but unreachable (e.g. failing TCP health checks), OmniRoute falls back to the provider proxy pool (`proxy_assignments` where `scope = 'provider'`).

A naive fallback implementation (`firstReachableProviderPoolProxy`) selects the first healthy proxy in the pool list. This leads to **hotspotting**:
- All accounts under the same provider collapse onto candidate 0.
- Egress rate limits (HTTP 429), IP bans, or connection throttling occur on candidate 0 while other proxies in the pool remain idle.

## Solution: Deterministic Hash Distribution (`resolveProviderPoolFallbackProxy`)

To distribute traffic evenly while preserving deterministic connection stickiness:

1. **Reachable Candidate Filtering:** Retrieve all provider pool proxies and filter for reachable candidates using `proxyHealthUrl(candidate)` and `isProxyReachable(url)`.
2. **Deterministic Hash Selection:**
   - Compute a deterministic hash from `connectionId` (e.g. polynomial string hash / djb2).
   - Compute index: `const index = Math.abs(hash) % reachableProxies.length;`
   - Select `reachableProxies[index]`.
3. **Stickiness Invariant:** The same `connectionId` always lands on the same fallback proxy in the pool as long as the pool of reachable candidates does not change.
4. **Uniform Distribution:** Distinct connection IDs spread across all healthy pool candidates.

## Implementation Details (`src/lib/db/settings.ts`)

```typescript
function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
}

export async function resolveProviderPoolFallbackProxy(
  provider: string,
  connectionId?: string
): Promise<ProxyResolutionResult | null> {
  const candidates = await getProxyPoolCandidates("provider", provider);
  if (!candidates || candidates.length === 0) return null;

  const reachable: ProxyRegistryRow[] = [];
  for (const candidate of candidates) {
    const healthUrl = proxyHealthUrl(candidate);
    if (healthUrl && (await isProxyReachable(healthUrl))) {
      reachable.push(candidate);
    }
  }

  if (reachable.length === 0) return null;

  const chosen =
    connectionId && reachable.length > 1
      ? reachable[Math.abs(hashString(connectionId)) % reachable.length]
      : reachable[0];

  return {
    proxy: {
      type: chosen.type,
      host: chosen.host,
      port: chosen.port,
      username: chosen.username,
      password: chosen.password,
      family: typeof chosen.family === "string" ? chosen.family : "auto",
    },
    level: "provider",
    levelId: provider,
    source: "provider_pool",
  };
}
```

## Testing Pattern (`tests/unit/proxy-fallback-distribution.test.ts`)

OmniRoute uses the Node.js native test runner (`node:test` + `tsx/esm`):

```bash
node --import tsx/esm --test tests/unit/proxy-fallback-distribution.test.ts
```

Harness boilerplate:
- Initialize isolated SQLite DB in `os.tmpdir()`.
- Set `process.env.DATA_DIR = TEST_DATA_DIR; process.env.API_KEY_SECRET = "test-secret";`.
- Mock TCP connectivity via `proxyHealth.__setProxyHealthTcpCheckForTesting((host, port) => ...)`.
- Seed multiple pool proxies with `proxiesDb.createProxy(...)` and `proxiesDb.addProxyToScopePool("provider", provider, proxy.id)`.
- Verify distribution across multiple connection IDs and verify stickiness for identical IDs.
- Clean up test storage and reset `__setProxyHealthTcpCheckForTesting(null)`.

## Provider Cooldown Configuration (Resilience Settings)

**Location:** `key_value` table, namespace='settings', key='resilienceSettings'

**Critical pitfall:** Provider cooldown defaults to **DISABLED** (`enabled: false`). Without it, when a provider returns 403/429, the combo burns through ALL accounts in that provider before reaching the next tier. With 63 antigravity accounts, this can hit the max combo attempts limit before omni-free (tier 3) is ever reached.

### Enabling & Tuning

```sql
-- Read current settings
SELECT value FROM key_value WHERE namespace = 'settings' AND key = 'resilienceSettings';

-- Update via Node.js (in-memory + SQLite)
const s = JSON.parse(row.value);
s.providerCooldown.enabled = true;
s.providerCooldown.minRetryCooldownMs = 30000;     // 30s initial
s.providerCooldown.maxRetryCooldownMs = 1800000;   // 30min max
db.prepare("UPDATE key_value SET value = ? WHERE namespace = 'settings' AND key = 'resilienceSettings'").run(JSON.stringify(s));

-- Bump settings revision to invalidate in-memory cache
db.prepare("UPDATE key_value SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE namespace = 'settings' AND key = '_settingsRevision'").run();
```

**Scope: per-connection, NOT per-provider.** When account A gets 403, only account A is cooldown'd. The combo still tries account B (different connectionId), which also fails. This means the combo can still burn through 63 accounts even with cooldown enabled. The cooldown helps by skipping individual failed accounts immediately (no TCP connect delay), but doesn't skip the entire provider.

### Combo Max Global Attempts

**Default:** 30 (`MAX_GLOBAL_ATTEMPTS` in `open-sse/services/combo/comboPredicates.ts`)
**Hard cap:** 200 (`MAX_GLOBAL_ATTEMPTS_HARD_CAP`)

```sql
-- Update via DB
SELECT data FROM combos WHERE name = 'omni-worker';
-- Parse JSON, set config.maxGlobalAttempts = 80, save back
```

**When to increase:** When a provider has many accounts (63 antigravity) and all fail, the combo needs enough budget to burn through them AND reach the next tier. Formula: `maxGlobalAttempts > (accounts_in_tier1 + accounts_in_tier2) + models_in_tier3`.

### Combo Tier Reordering

Combo models are stored as an ordered array in `combos.data` JSON. To reorder tiers (e.g., put omni-free first when antigravity is down):

```sql
-- Read combo
SELECT data FROM combos WHERE name = 'omni-worker';

-- Parse JSON, reorder data.models array, save back
-- Example: swap tier 1 and tier 3
const models = data.models;
const omniFree = models.find(m => m.comboName === 'omni-free');
const agGemini = models.find(m => m.comboName === 'ag-gemini-pool-3');
data.models = [omniFree, agGemini, models.find(m => m.comboName === 'ag-claude')];
```

**After reorder, test immediately** — no restart needed (combo config is read from DB on each request).

### Debugging Combo Failures via Logs

**Log location:** `~/.omniroute/logs/application/app.log`

**Key patterns:**
```
# Provider in cooldown (good — skipping fast)
"Skipping antigravity/gemini-3.8-flash-tiered — provider antigravity in global cooldown"

# Model locked by resilience
"Skipping antigravity/gemini-3.8-flash-tiered — model locked by resilience (cooldown active)"

# Connection marked for skip after 403
"Provider antigravity connection XXXXXX auth failure (403) — marking for skip on remaining targets (#8133)"

# Max attempts hit (bad — combo exhausted budget)
"Maximum combo attempts (N) exceeded across all targets and fallbacks"

# Client disconnected during slow combo
"Client disconnected (499) during antigravity/gemini-3.8-flash-tiered — stopping combo loop"

# Opencode also in cooldown (from earlier test failures)
"Skipping oc/muse-spark-1.3-contributor-free — provider opencode in global cooldown"

# Successful request
"🌊 [STREAM] ANTIGRAVITY | gemini-3.8-flash-tiered | 8703ms | complete"
```

**Diagnostic output from API response:**
```json
{
  "diagnostics": {
    "poolSize": 72,
    "attempted": 28,
    "excluded": [{"provider": "antigravity", "reason": "exhausted_connection:XXXX"}],
    "terminalReason": "max_attempts_exceeded"
  }
}
```

### No-Auth Provider Cooldown Pitfall

**Problem:** When testing proxy assignment for `opencode` with a dead proxy (e.g., MobiProxy), the 502 errors trigger provider cooldown for `opencode`. After switching to a working proxy (MikroTik), the cooldown persists in memory — `opencode` remains skipped in combo context even though it works for direct requests.

**Diagnosis:** Log shows `"Skipping oc/muse-spark-1.3-contributor-free — provider opencode in global cooldown"` while `curl ... combo/omni-free` works fine.

**Fix:** Restart OmniRoute to clear in-memory cooldown state. There is NO API to clear cooldown programmatically.

```
# Stop
powershell -Command "Stop-Process -Id <PID> -Force"
# Start
cd C:/Users/Kibe/OmniRoute && npm run dev
```

## Tooling & Search Pitfall on Windows

- **Windows search_files path issue:** Passing absolute paths with forward slashes directly pointing to a single file (e.g. `path="C:/Users/Kibe/OmniRoute/src/lib/db/settings.ts"`) can fail with `os error 3 (The system cannot find the path specified)`. Always target the directory `path="C:/Users/Kibe/OmniRoute/src/lib/db"` or use `terminal` tool with `grep -n` directly inside the worktree.
