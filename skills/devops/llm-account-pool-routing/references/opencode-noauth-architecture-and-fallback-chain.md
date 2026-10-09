# OpenCode No-Auth Architecture & Correct Fallback Chain (2026-09-11)

## OpenCode in OmniRoute is Pure No-Auth

**File:** `src/shared/constants/providers/noauth.ts`

```typescript
opencode: {
  id: "opencode",
  alias: "oc",
  name: "OpenCode Free",
  icon: "terminal",
  color: "#E87040",
  textIcon: "OC",
  website: "https://opencode.ai",
  noAuth: true,
  hasFree: true,
  serviceKinds: ["llm"],
  authHint: "No API key required — uses OpenCode's public free endpoint.",
  freeNote:
    "No API key required — public OpenCode endpoint with Kimi, GLM, Qwen, MiMo, MiniMax models.",
  notice: {
    text: "OpenCode Free uses the public OpenCode endpoint (https://opencode.ai/zen/v1). No signup or API key needed. Rate limits apply.",
  },
},
```

**Executor:** `open-sse/executors/opencode.ts`
- Builds `accounts` array from `providerSpecificData.fingerprints` + `accountProxies`
- Default single direct account (`fingerprint: ""`) when no configured accounts
- Round-robin pick with cooldown skip (`pickRotatableAccount`)
- **NO API KEY REQUIRED** for free models: `big-pickle`, `deepseek-v4-flash-free`, `mimo-v2.5-free`, `hy3-free`, `nemotron-3-ultra-free`, `north-mini-code-free`

**Free models set** (from executor):
```typescript
const OPENCODE_FREE_MODELS = new Set([
  "big-pickle",
  "deepseek-v4-flash-free",
  "mimo-v2.5-free",
  "hy3-free",
  "nemotron-3-ultra-free",
  "north-mini-code-free",
]);
```

**Premium models gate** — returns 402 if keyless + premium model:
```typescript
const isKeyless = !creds?.apiKey && !creds?.accessToken && !creds?.providerSpecificData?.extraApiKeys;
if (isKeyless && isPremiumOpencodeModel(input.model, this.provider)) {
  return 402 "This model requires an opencode API key — add one in Settings → Providers."
}
```

---

## The Dummy Key Incident

**Connection:** `fd892039-3c78-4920-8aa1-a0e81695993c` ("OpenCode Free Pool")
- Created: 2026-09-04T18:09:59.291Z
- Had `api_key: "free****free"` (dummy/placeholder)
- `authType: "apikey"` — **INCORRECT**, should be no-auth
- 38 fingerprints/proxies configured (MikroTik 10001-10035 + MobiProxy 5101-5138 + khoalee 16001-16002)
- **27 requests, ALL 401** — never worked once

**Why 401:** OmniRoute sent `Authorization: Bearer free****free` to OpenCode public endpoint → upstream rejected invalid key.

**Fix:** Remove API key from connection or disable connection. Real no-auth path works perfectly:
- `opencode/nemotron-3-ultra-free` → **HTTP 200 OK**
- `combo/omni-free` → **HTTP 200 OK** (routes to mimo-v2.5-free, nemotron-3-ultra-free, etc.)

---

## Correct Fallback Chain Architecture

### OmniRoute Internal (combo `omni-worker`)
```
Tier 1: ag-gemini-pool-3 (63 hard-bound Antigravity accounts, gemini-3.8-flash-tiered)
Tier 2: ag-claude (9 hard-bound accounts, antigravity/claude-sonnet-4-6, 100% Claude quota)
Tier 3: omni-free (OpenCode free tier, no-auth, proxy rotation)
```

### Hermes External (when OmniRoute returns 5xx)
```
1. omni-free (provider: omni)      — OmniRoute free pool combo
2. 9r-free (provider: custom:9router) — 9Router free tier
```
**NOT ag-claude** — it's already Tier 2 inside omni-worker combo!

### Why This Separation Matters
- OmniRoute `maxGlobalAttempts=30` budget applies to Tier 1 only
- When Tier 1 exhausts budget → OmniRoute returns 503 for entire combo
- Hermes fallback triggers independently with its own timeout/retry budget
- Putting ag-claude in Hermes fallback would duplicate Tier 2 and waste budget

---

## 503 ALL_TARGETS_SKIPPED Diagnosis Methodology

**Symptom:** `recordedAttempts === 0`, `duration < 1000ms`, `tokens.in = 0`

**Root causes (pre-dispatch filters in combo.ts):**

| Filter | What it checks | Common cause |
|--------|----------------|--------------|
| `resolveQuotaExhaustionCutoffForTarget` | `quota_snapshots` by `(connection_id, window_key)` | Stale snapshot (`is_exhausted=1` while real quota reset) |
| `resolvePersistedConnectionCooldownSkipReason` | `rate_limited_until` in `provider_connections` | Expired cooldown not cleared |
| `isModelLocked` / `isProviderInCooldown` | Model/provider level cooldown | Previous 429/403 wave |
| Hard-bound binding | `connectionId` hard-bound | `refusing sibling selection` — cannot borrow sibling |

**Diagnosis steps:**
1. Check `call_logs` for duration <1s and 0 tokens
2. Query `quota_snapshots` for model/window_key of request
3. Probe TCP proxy for each account (`socket.connect_ex` 0.3s timeout)
4. Check `rate_limited_until` in `provider_connections`
5. Trigger `POST /api/providers/{id}/refresh` + `/sync-models` to refresh quota
6. Clear stale cooldowns in DB

---

## MikroTik DNS Resolution Quirk

**Hostname:** `mirotik1.taadaa.click`
- **WAN DNS resolves to:** `171.231.195.2` (public IP)
- **LAN actual IP:** `192.168.110.2` (MikroTik on LAN)
- **Open ports on LAN:** 10001-10035, 8291 (WinBox)

**Probe from this machine:** Socket connect to WAN IP times out (firewall/NAT)
**Real traffic from farm devices:** Goes through LAN IP, works fine

**Fix:** Probe `192.168.110.2:10001` directly, or use Singbox egress `192.168.110.2:20001-20080`

---

## Combo Update Pattern (Hard-Bound Targets)

**Endpoint:** `PUT http://127.0.0.1:20129/api/combos/{combo_id}`

**Payload structure:**
```json
{
  "name": "ag-claude",
  "description": "AG Claude Sonnet 4.6 - 9 hard-bound accounts (100% Claude quota) + Gemini fallback",
  "strategy": "priority",
  "config": {
    "maxRetries": 0,
    "retryDelayMs": 0,
    "handoffThreshold": 0.85,
    "failoverBeforeRetry": true,
    "reasoningTokenBufferEnabled": true
  },
  "models": [
    {
      "id": "ag-claude-model-1-claude-sonnet-4-6-1be3bc77",
      "kind": "model",
      "model": "antigravity/claude-sonnet-4-6",
      "providerId": "antigravity",
      "connectionId": "1be3bc77-29cb-476a-a109-19909063b30a",
      "weight": 0,
      "label": "claude-pool-1"
    },
    ...more hard-bound targets...
    {
      "id": "ag-claude-model-fallback-gemini-pool-3",
      "kind": "model",
      "model": "combo/ag-gemini-pool-3",
      "providerId": "combo",
      "weight": 0,
      "label": "Gemini Pool (Fallback)"
    }
  ]
}
```

**Key points:**
- `kind: "model"` with `connectionId` for hard-bound
- `kind: "model"` with `model: "combo/..."` for nested combo fallback
- `providerId: "combo"` for nested combos
- `strategy: "priority"` for sequential failover

---

## Versioning to AI-Tools Repo

**After any combo/proxy/settings change:**
```bash
# Export combos
curl http://127.0.0.1:20129/api/combos > D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json

# Export resilience settings
# Query key_value for resilienceSettings

# Git commit
cd D:/Taadaa/AI-Tools
git add tools/omniroute/combos_backup.json
git commit -m "omniroute: update ag-claude with 9 hard-bound Claude 100% quota accounts"
```

**Repo location:** `D:\Taadaa\AI-Tools` (NOT `D:\OneDrive\AI-Tools`)

---

## Quick Verification Commands

```bash
# Test OpenCode no-auth direct
curl -X POST http://127.0.0.1:20129/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"opencode/nemotron-3-ultra-free","messages":[{"role":"user","content":"ping"}]}'

# Test omni-free combo
curl -X POST http://127.0.0.1:20129/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"combo/omni-free","messages":[{"role":"user","content":"ping"}]}'

# Test omni-worker combo (full chain)
curl -X POST http://127.0.0.1:20129/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"combo/omni-worker","messages":[{"role":"user","content":"ping"}]}'

# Check Hermes fallback chain
python -c "from hermes_cli.config import load_config; print(load_config().get('fallback_providers'))"
```