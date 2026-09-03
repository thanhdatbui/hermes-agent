# OmniRoute & 9Router Account Pool Diagnostics

## 0. Router Disambiguation Invariant
- **OmniRoute (`:20129`)**: UI title **OmniRoute**; DB is `C:\Users\Kibe\.omniroute\storage.sqlite` (legacy directory priority over `%APPDATA%\omniroute`), codebase at `C:\Users\Kibe\OmniRoute`.
- **9Router (`:20128`)**: UI title **9Router**; DB is `%APPDATA%\9router\db\data.sqlite` (or `9router.db`), codebase at `%APPDATA%\npm\node_modules\9router\app`.
- **Rule**: When operator asks about account status/quotas, check port (`:20129` vs `:20128`) and dashboard logo/version first. Never diagnose 9Router when the operator is asking about OmniRoute.

---

## 1. OmniRoute (`:20129`) Diagnostic Recipes

Database: `C:\Users\Kibe\.omniroute\storage.sqlite` (Note: `src/lib/dataPaths.ts` checks `~/.omniroute` before `%APPDATA%\omniroute`; the active production DB is under `C:\Users\Kibe\.omniroute`).

### Checking Account Status & Assigned Proxies
```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cursor = conn.cursor()
cursor.execute('''
  SELECT pc.id, pc.name, pc.priority, pc.is_active, pc.test_status, pc.error_code, pc.last_error, 
         pr.name as proxy_name, pr.host, pr.port, pr.username, pr.password
  FROM provider_connections pc
  LEFT JOIN proxy_assignments pa ON pa.scope_id = pc.id AND pa.scope = 'account'
  LEFT JOIN proxy_registry pr ON pa.proxy_id = pr.id
  WHERE pc.provider = 'antigravity'
  ORDER BY pc.priority ASC
''')
for row in cursor.fetchall():
    print(row)
```

### Checking Proxy Registry for Missing Auth
```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cursor = conn.cursor()
cursor.execute('''
  SELECT id, name, host, port, username, password, status
  FROM proxy_registry
  WHERE username = '' OR username IS NULL OR password = '' OR password IS NULL
''')
print("Proxies missing auth:", cursor.fetchall())
```

### Common Failure Modes in Dashboard:
1. **"Load failed" / "HTTP 503: fetch failed" / "Token expired":**
   - Account has `proxy_enabled = 1` and an assigned proxy in `proxy_assignments`.
   - **Root Cause A (Missing Auth):** The assigned proxy entry in `proxy_registry` has empty `username`/`password`. For MikroTik farm proxies (`mirotik1.taadaa.click:10001..10035`), credentials `admin@1:admin@1` are REQUIRED.
   - **Root Cause B (Dead Proxy/Bad Port):** The proxy is down or host/port is misconfigured.
   - **Mechanism:** OAuth tokens expire every ~1 hour. Token refresh requests are routed through the assigned proxy. When the proxy rejects connection, refresh fails with `refresh_transient` / `refresh_failed` and the account turns red in UI despite previously showing 100% quota.
   - **Fix:** Update `username='admin@1'`, `password='admin@1'` in `proxy_registry` (or reassign to live proxy), then trigger refresh in UI or call API `POST /api/providers/<id>/refresh-token`.

2. **Inactive / Grey Toggle (`is_active = 0`):**
   - Account toggle is switched OFF in the dashboard UI or lacks required configuration (e.g. empty `projectId`).
   - **Fix:** Update `is_active = 1` and ensure `projectId` is populated.

3. **"422: Missing Google projectId for Antigravity account" on Claude / Gemini models:**
   - **Root Cause:** In `open-sse/services/tokenRefresh.ts`, `formatProviderCredentials()` for `antigravity` / `agy` previously returned only `{ accessToken, refreshToken }`, dropping `projectId` and `providerSpecificData`.
   - **Mechanism:** When credentials were formatted before dispatch to `open-sse/executors/antigravity.ts`, `credentials.projectId` was undefined, triggering auto-discovery via `loadCodeAssist` which failed with 422.
   - **Fix:** Ensure `formatProviderCredentials` includes `projectId: credentials.projectId` and `providerSpecificData: credentials.providerSpecificData`.

4. **Cascade Failover on Exhausted Model Quotas (Shared `correlation_id`):**
   - **Symptom:** Logs show a burst of 10-15 consecutive 429 errors within seconds across different accounts for the same model (e.g. `claude-sonnet-4-6`).
   - **Diagnosis:** Check `correlation_id` in `call_logs`. If multiple error rows share the exact same `correlation_id`, it is **NOT** a looping bug hitting the same account; it is the router sequentially attempting account failover across all candidate connections in the pool until all fail.
   - **Root Cause:** Upstream model quota is depleted across the entire account pool at the provider side.
   - **Fix:** Wait for provider quota reset window, or route traffic to an active alternative model pool (e.g. `gemini-3.7-flash-high`).

5. **Distinguishing Code Formatting Bugs vs OAuth Session Expiry (401/403 invalid_grant):**
   - **Code bug (422):** Fixed in router codebase (e.g. missing `projectId` or headers).
   - **Session Expiry / Revocation (401 / 403 `invalid_grant`):** Google invalidated the refresh token or requires user re-authentication/verification. Code patches cannot fix this; operator must click Re-login/Re-authenticate in the dashboard UI.

6. **Auditing Account Real Usage vs Health Checks:**
   - Inspect `TokensIn`, `last_used_at`, and `consecutive_use_count` in `provider_connections` and `usage_history`.
   - If `TokensIn == 0` and all 200 logs are `connection-test` (health checks) while actual inference calls returned 403/422/429, the account has never successfully served user traffic. Check project ID validity and OAuth scope.

7. **Auditing Worker Combos for Unintended Model Calls (e.g. Sonnet in `ag-worker`):**
   - **Symptom:** User notices requests unexpectedly hitting paid/restricted models (e.g. `antigravity/claude-sonnet-4-6`) during autonomous worker execution.
   - **Diagnosis:** Inspect `combos` table (`SELECT id, name, data FROM combos WHERE name='ag-worker'`).
   - **Root Cause:** When `delegation.model` is set to a combo (e.g. `ag-worker`), the combo's fallback hierarchy may contain intermediate tiers (e.g. Tier 1: `ag-gemini-pool-3` -> Tier 2A: `claude-sonnet-4-6` -> Tier 2B: `deepseek-v4-flash` -> Tier 3: `omni-free`). If Tier 1 experiences transient 429s or high concurrency, the combo silently falls over to Tier 2A.
   - **Fix:** Remove the unwanted model from the combo `models` array in `combos.data` so the fallback chain routes directly from pool to free tiers without hitting restricted models.

8. **Nested Combo Expansion (`combo-ref` vs `model` kind):**
   - **Symptom:** When calling a wrapper combo (e.g. `ag-worker`) that contains a sub-combo pool (e.g. `ag-gemini-pool-3`), a transient failure or rate-limit on Account 1 causes the router to immediately skip to the next top-level step (e.g. Tier 2 / Free models) without trying the remaining accounts in the sub-combo.
   - **Root Cause:** In the `combos` table `data` JSON, the sub-combo was saved as `{"kind": "model", "model": "combo/ag-gemini-pool-3", "providerId": "combo"}` instead of `{"kind": "combo-ref", "comboName": "ag-gemini-pool-3"}`. When `kind == "model"`, OmniRoute's `resolveComboTargets` does not recursively unroll the nested combo targets into individual account targets, treating the entire pool as a single monolithic model step.
   - **Fix:** Update the combo definition to use `{"kind": "combo-ref", "comboName": "<nested-combo-name>"}`. This allows `resolveComboTargets` to unroll all 18 individual account targets in order.



---

## 2. 9Router (`:20128`) Diagnostic Recipes

Database: `%APPDATA%\9router\db\data.sqlite`

### 429 Priority Demotion to 9999 ("No active credentials")
- When all accounts for a provider hit 429 rate limits, 9Router demotes their priority to 9999.
- If all accounts have `priority >= 9000`, 9Router returns `No active credentials for provider: <provider>` (404).
- **Fix:**
```python
import sqlite3, os, json
db_path = os.path.join(os.environ['APPDATA'], '9router', 'db', 'data.sqlite')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    UPDATE providerConnections 
    SET priority = json_extract(data, '$.priorityBase'),
        updatedAt = datetime('now')
    WHERE provider = 'antigravity' AND priority = 9999
""")
conn.commit()
```
