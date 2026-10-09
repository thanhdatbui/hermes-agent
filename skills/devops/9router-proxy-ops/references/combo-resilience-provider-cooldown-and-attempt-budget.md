# Combo Resilience: Provider Cooldown, Attempt Budget & Nested Combo-Ref Behavior

## Problem: Combo Burns Through All Accounts Before Reaching Fallback Tiers

When a combo uses nested `combo-ref` targets (e.g., `omni-worker` → `ag-gemini-pool-3` with 63 accounts), and the upstream provider returns persistent errors (403/429/502), the combo tries every individual account/model before moving to the next tier. With 63 accounts × 1 error each = 63 attempts, easily exceeding the default `maxGlobalAttempts` of 30.

**Symptom:** Combo reports "Maximum combo retry limit reached" at 30 attempts. Tier 3 (`omni-free`) is never reached. Hermes falls back to `9r-free`.

## Two Independent Fixes (Both Needed)

### Fix 1: Enable Provider Cooldown

**Config path:** `key_value` table, namespace `settings`, key `resilienceSettings`

```json
{
  "providerCooldown": {
    "enabled": false,       // ← DEFAULT IS FALSE! Must enable.
    "minRetryCooldownMs": 5000,
    "maxRetryCooldownMs": 300000
  }
}
```

**What it does:** When a provider returns 403/429/502, the connection goes into cooldown. After cooldown expires, the provider is probed. If still failing, cooldown doubles (exponential backoff up to `maxRetryCooldownMs`).

**Log signal (working):**
```
"auth failure (403) — marking for skip on remaining targets (#8133)"
"Skipping antigravity/gemini-3.8-flash-tiered — model locked by resilience (cooldown active)"
```

**Pitfall:** Cooldown is **per-connection**, not per-provider. With 63 accounts, each account gets its own cooldown. The combo still tries other accounts in the same provider until the attempt budget is exhausted. This is why Fix 2 is also needed.

**Recommended settings for continuous failures:**
```json
{
  "providerCooldown": {
    "enabled": true,
    "minRetryCooldownMs": 10000,
    "maxRetryCooldownMs": 600000
  }
}
```

### Fix 2: Increase `maxGlobalAttempts`

**Config path:** Combo `config.maxGlobalAttempts` in `combos` table

**Default:** 30 (hard cap: 200, defined in `open-sse/services/combo/comboPredicates.ts` → `MAX_GLOBAL_ATTEMPTS`)

**Source:** `clampGlobalAttempts()` in `open-sse/services/combo/comboPredicates.ts:125`

```typescript
export const MAX_GLOBAL_ATTEMPTS = 30;
export const MAX_GLOBAL_ATTEMPTS_HARD_CAP = 200;

export function clampGlobalAttempts(value: unknown): number {
  const n = Math.floor(Number(value));
  if (!Number.isFinite(n) || n < 1) return MAX_GLOBAL_ATTEMPTS;
  return Math.min(n, MAX_GLOBAL_ATTEMPTS_HARD_CAP);
}
```

**For combos with nested combo-refs:** Set `maxGlobalAttempts` ≥ (accounts in tier 1) + (accounts in tier 2) + (models in tier 3). Example: `omni-worker` with 63 AG accounts + 2 claude + 7 free = ~72 → set to 80.

**Update via SQLite:**
```javascript
const data = JSON.parse(row.data);
data.config.maxGlobalAttempts = 80;
db.prepare("UPDATE combos SET data = ? WHERE name = 'omni-worker'").run(JSON.stringify(data));
```

## Combo Retry Flow (Priority Strategy)

```
Request → resolveComboTargets() → flat list of all models across all tiers
  → For each model:
    1. Check provider cooldown → if active, skip
    2. Check #8133 auth failure skip → if marked, skip
    3. Dispatch → success? return
    4. Fail → increment globalAttempts
    5. globalAttempts > maxGlobalAttempts? → TERMINATE
  → All models exhausted or budget hit → "Maximum combo retry limit reached"
```

**Key insight:** `resolveComboTargets()` expands nested combo-refs into a flat list. The combo loop iterates the flat list, not the tier structure. So a nested `ag-gemini-pool-3` with 63 accounts becomes 63 individual entries in the flat list, all before the next tier's entries.

## #8133 Auth Failure Skip Mechanism

When a connection returns 403 (auth failure), the combo logs:
```
"Provider antigravity connection <id> auth failure (403) — marking for skip on remaining targets (#8133)"
```

This marks the specific connection for skip on remaining targets **within the same request**. It does NOT persist across requests — each new request starts fresh.

## When Provider is Working But Accounts Have Intermittent 403

Some accounts may have valid tokens (connection-test = 200) but get 403 on actual model requests. This is an Antigravity upstream issue, not a proxy or token issue. Symptoms:
- `connection-test` model: HTTP 200 ✅
- `gemini-3.8-flash-tiered`: HTTP 403 ❌
- `claude-sonnet-4-6`: HTTP 403 ❌

This means the Antigravity upstream is blocking the account for specific models despite valid OAuth tokens. Possible causes: account flagged, rate-limited at upstream level, or model access policy change.

## Verification Commands

```bash
# Check provider cooldown settings
node -e "
const Database = require('better-sqlite3');
const db = new Database('<DATA_DIR>/storage.sqlite');
const row = db.prepare(\"SELECT value FROM key_value WHERE namespace = 'settings' AND key = 'resilienceSettings'\").get();
const s = JSON.parse(row.value);
console.log('Provider cooldown:', JSON.stringify(s.providerCooldown));
"

# Check combo maxGlobalAttempts
node -e "
const Database = require('better-sqlite3');
const db = new Database('<DATA_DIR>/storage.sqlite');
const row = db.prepare(\"SELECT data FROM combos WHERE name = 'omni-worker'\").get();
const data = JSON.parse(row.data);
console.log('maxGlobalAttempts:', data.config.maxGlobalAttempts);
"

# Check recent combo logs for cooldown activity
tail -500 ~/.omniroute/logs/application/app.log | grep -i 'cooldown\|skipping.*provider\|auth failure.*403\|Maximum combo'
```
