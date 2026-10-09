# Concurrency Spillover Diagnostics for OmniRoute Priority Pools

## Pattern Observed: Priority Account Concurrency Spillover to Failing Accounts

When a priority-ordered pool has accounts with `max_concurrent` caps, high concurrency on early-priority accounts (P1–P14) causes spillover to later-priority accounts (P15–P18). If those later accounts have credential failures (403/revoked tokens), the entire pool reports "No active credentials" 404/502 errors even though early accounts are healthy.

### Diagnostic Query: Full Account Health + Concurrency State

```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cursor = conn.cursor()
cursor.execute('''
  SELECT name, priority, is_active, test_status, error_code, last_error, last_error_at, last_error_type,
         backoff_level, rate_limited_until, last_used_at, max_concurrent, expires_at
  FROM provider_connections
  WHERE provider = 'antigravity'
  ORDER BY priority ASC
''')
for row in cursor.fetchall():
    print(row)
```

### Key Columns to Inspect

| Column | Purpose |
|--------|---------|
| `max_concurrent` | Capacity ceiling per account (8 for Pro, 3 for Starter) |
| `last_used_at` | Last successful inference call timestamp |
| `consecutive_use_count` | Sequential dispatches without rotation |
| `expires_at` | OAuth token expiry (critical for 403 diagnosis) |
| `backoff_level` / `rate_limited_until` | Active backoff state |

### Spillover Detection Logic

1. Count accounts with `last_used_at` within last N minutes → active concurrency
2. If active concurrency ≥ sum of `max_concurrent` for P1–P14 → spillover to P15+
3. Check P15+ for `test_status != 'active'` OR `expires_at` near/past now OR 403 in recent `call_logs`

### Remediation Options

| Option | When |
|--------|------|
| Re-login failing accounts (P15+) | Token revoked/expired (403 `invalid_grant`) |
| Temporarily `is_active = 0` for failing accounts | Need immediate stop to 404 pool errors |
| Increase `max_concurrent` on P1–P14 | If capacity genuinely insufficient |
| Add more healthy priority accounts | Long-term fix |

### Evidence from 2026-09-03
- P1–P14: `max_concurrent = 8`, healthy tokens, serving 200
- P15 (`phungthibichngoc`): 8, but 403 errors in logs
- P16 (`lamngocdiep`): 8, 403 errors
- P17 (`lequynh27032002`): 8, 403 errors
- P18 (`brittanysbarnes`): 3 (Starter), no recent errors

Pool errors: "No active credentials for provider: antigravity (+7/+9/+10 more)" = router tried all 18 accounts, all failed (because P1–P14 busy, P15–P17 failing, P18 alone insufficient).

## Multi-Tier Worker Combo Inversion & Free-Tier Spillover Trap (2026-09-11)

### Symptom & Dashboard Phenomenon
- OmniRoute Dashboard Logs (`:20129/dashboard/logs`) suddenly exhibits red 502/504 errors on `opencode/nemotron-3-ultra-free` and green 200 OK on `opencode/muse-spark-1.3-contributor-free` with high token volume (`TL: 320.000`–`345.000` tokens).
- Operator asks: *"sao acc gemini còn quota mà nhảy tùm lum qua bên model free v"* (Gemini pool still has ample quota, e.g. 42/63 accounts healthy with >90% quota).

### Root Causes
1. **Tier Ordering Inversion in `omni-worker` Combo**:
   - Intended architecture: Tier 1 `ag-gemini-pool-3` (Gemini Flash) → Tier 2 `ag-claude` (Claude Sonnet 4.6 Pro) → Tier 3 `omni-free` (Safety net).
   - Misconfiguration defect: `omni-free` was inserted at index 1 (Tier 2 position), pushing `ag-claude` down to index 2 (Tier 3 position).
   - When Gemini targets experienced transient account semaphore caps (`max_concurrent: 2`) or rate limits under concurrent subagent burst load (>300K tokens each), OmniRoute immediately spilled over to Tier 2 (`omni-free`) instead of trying `ag-claude`.
2. **Nvidia Upstream Failure Mode on `nemotron-3-ultra-free`**:
   - `nemotron-3-ultra-free` frequently returns HTTP 502 (`Upstream error from Nvidia: Service temporarily overloaded`) or hangs until HTTP 504 Gateway Timeout (`Stream produced no non-ping SSE event within 135000ms/160000ms`), blocking worker subagents for 2.5–3 minutes per attempt before falling through to `muse-spark-1.3-contributor-free`.

### Rapid O(1) Diagnostic Queries
```python
import sqlite3, json

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
c = conn.cursor()

# 1. Verify combo tier order
c.execute('SELECT data FROM combos WHERE name = "omni-worker"')
worker_data = json.loads(c.fetchone()[0])
print("omni-worker tiers:", [m.get("comboName") or m.get("model") for m in worker_data.get("models", [])])

# 2. Check recent spillover calls
c.execute('''
    SELECT timestamp, status, provider, model, combo_step_id, duration, tokens_in, error_summary
    FROM call_logs
    WHERE combo_name = "omni-worker" AND model LIKE "%free%"
    ORDER BY timestamp DESC LIMIT 10
''')
for r in c.fetchall():
    print(r)

# 3. Check Gemini pool health (active vs exhausted)
c.execute('SELECT is_active, test_status, COUNT(*) FROM provider_connections WHERE provider="antigravity" GROUP BY is_active, test_status')
print("Connection health:", c.fetchall())
```

### Remediation Rules
1. **Reorder `omni-worker` combo tiers**: Ensure Tier 1 = `ag-gemini-pool-3`, Tier 2 = `ag-claude`, Tier 3 = `omni-free`.
2. **Prune/Deprioritize Unstable Free Models**: Remove or disable `nemotron-3-ultra-free` from `omni-free` due to frequent upstream 502/504 hangs.
3. **Backup combo changes**: Export to `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json` and commit.

## Reset-Aware Runtime Ordering vs Static DB Order (2026-09-11)

### Core Finding
**`reset-aware` strategy DOES reorder targets at runtime per-request** - it fetches live quota snapshots and sorts by remaining quota before dispatch. However, this is **ephemeral runtime behavior only** - the static order in `combos.data.models` array remains unchanged.

### Why Static Order Still Matters

Even with `reset-aware` runtime reordering, the static DB order controls several critical mechanisms:

| Mechanism | Uses | Impact of Bad Static Order |
|-----------|------|----------------------------|
| **Session Stickiness** | `executionKey` from static order | Pin can land on exhausted account at position #3 even if runtime puts it at #50 |
| **LKGP (Last Known Good Provider)** | `executionKey` from static order | Records success against wrong executionKey if static order ≠ runtime winner |
| **Prompt Cache Affinity (global scope)** | `executionKey` for rendezvous hashing | Hash distributes based on static position, not runtime quota rank |
| **Pre-screen cache** | `target.executionKey` from static order | May fetch quota for wrong connection if static order diverges |
| **Decision Trace / Debug** | `comboStepId` = `executionKey` | Logs show static position, hard to correlate with actual quota state |

### Evidence from Session

**Pool: `ag-gemini-pool-3` (strategy=reset-aware, 63 targets)**
- Static order: Exhausted accounts at positions #3, #7, #12, #13, #14, #15, #17, #18
- Runtime: `jinrakal@gmail.com` (position #1, quota=100%) correctly selected for all recent requests
- BUT: 8 concurrent workers quickly saturated concurrency cap (2/acc) on top accounts → spill to `omni-free` before runtime ordering could reach healthy accounts deeper in pool

**Pool: `ag-claude` (strategy=reset-aware, 63 targets)**
- 45/63 accounts exhausted (0% quota) concentrated in first 30 positions
- Only 18 healthy accounts scattered at positions #35-#61
- `maxGlobalAttempts=80` sufficient budget, but static order causes unnecessary scan

### Recommended Practice
1. **Run physical reorder script** (`pool-reorder-script.md`) periodically to align static order with quota reality
2. **Set combo config**:
   ```json
   {
     "disableSessionStickiness": true,
     "disablePromptCacheAffinity": true
   }
   ```
3. **Reorder GRP0-4 groups**:
   - GRP0: Pro tier + live proxy
   - GRP1: Free tier + quota >= 10%
   - GRP2: Free tier + quota < 10%
   - GRP3: Standard-tier (403 candidate)
   - GRP4: Dead proxy / expired / inactive

### Related Skills
- `references/pool-reorder-and-fallback-chain.md` - Full reorder procedure
- `references/pool-reorder-script.md` - Python reorder script
- `references/session-stickiness-pool-safety.md` - Stickiness interaction with ordering
- `references/priority-combo-unrolling-and-tier-fallback.md` - Tier fallback mechanics

---

## OmniRoute Log Symbol `↳` & Antigravity Concurrency Spillover vs 422 ProjectId Deactivation Protocol (2026-10-01)

### 1. OmniRoute Dashboard Log Symbol `↳` (Next to 200 OK)
In `RequestLoggerV2.tsx`, requests sharing the same `correlationId` (same client turn / subagent dispatch) are grouped:
- **First row**: Root request.
- **Subsequent rows**: Rendered indented with **`↳`** (a clickable jump button `goToParent`).
- **Healed Status**: If a prior attempt failed (e.g. 422, 429) and a retry/fallback succeeded, the parent shows a green `✓` (`recoveredByRetry`) and the winning attempt displays `↳ 200 OK`.
- **False Retry Phenomenon**: If the client (Hermes/Playground) reuses `correlationId` across multiple independent tool calls, all calls after the first will display `↳` even if 100% of them succeeded with 200 OK.

### 2. Antigravity `max_concurrent: 2` Ceiling & Transient Spillover
- **Why `max_concurrent: 2` is Optimal**: Google Code Assist enforces strict stream multiplexing per OAuth token. Concurrency > 2 on long-context prompts (>60K-200K tokens) causes upstream HTTP 429 or severe stream latency degradation (TTFT jumping from 15s to >60-120s).
- **Fleet Scale**: 20 Pro accounts @ `max_concurrent: 2` = 40 parallel inference streams. Historical data (58K requests over 7 days) demonstrates Pro absorbs 96%–99.8% of daily volume with <0.4% spillover and <23 429s/day.
- **Overflow Mechanism**: Saturated concurrency caps (`runtimeUnitCapacity.ts`) or queue wait > 3s (`queueTimeoutMs`) immediately spills traffic to Tier 2 (`ag-gemini-free-pool`).

### 3. The HTTP 422 `Missing Google projectId` Trap
- **Root Cause**: Accounts onboarded via raw OAuth without selecting a Cloud Code project in Gemini Code Assist have `project_id = NULL`.
- **Failure Mode**: When Tier 1 spills over to Tier 2, requests hitting unconfigured Free accounts throw `422: Missing Google projectId for Antigravity account...`.
- **Cascade**: Router tries multiple Free accounts, failing with 422 on each until hitting an onboarded account or returning to Pro, producing noisy 422 churn in logs.

### 4. Safe Deactivation & Watchdog Auto-Heal Defense
When isolating/deactivating broken accounts (`is_active = 0`), beware of automated healer scripts undoing operator action:
- **Watchdog Bug Pattern**:
  ```python
  # BAD: Unconditionally reactivates broken accounts every hour
  cur.execute("UPDATE provider_connections SET is_active = 1 WHERE provider = 'antigravity' AND is_active = 0 AND test_status = 'active'")
  ```
- **Invariant Fix**:
  ```python
  # GOOD: Only reactivates accounts that satisfy all runtime prerequisites
  cur.execute("""
      UPDATE provider_connections 
      SET is_active = 1 
      WHERE provider = 'antigravity' 
        AND is_active = 0 
        AND test_status = 'active'
        AND project_id IS NOT NULL 
        AND project_id != ''
  """)
  ```
- **Sync Requirement**: Always run `python ~/AppData/Local/hermes/scripts/cron_sync_watchdog.py` after editing cron scripts to keep runtime, Git deploy, and OneDrive Shared synchronized.