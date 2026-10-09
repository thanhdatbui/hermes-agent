# OmniRoute Priority Pool Routing & Account Quota Diagnosis

## 1. Storage Location Invariant (Windows)
OmniRoute resolves its data directory via `src/lib/dataPaths.ts`:
- **Active Production Database:** `~/.omniroute/storage.sqlite` (e.g. `C:\Users\<user>\.omniroute\storage.sqlite`).
- **Caveat:** Even if `%APPDATA%\omniroute\storage.sqlite` exists, OmniRoute preserves the legacy dot-dir `~/.omniroute` if present. Always verify active SQLite DB file by checking `.sqlite-wal` activity or inspecting process handle.
- Do not inspect `%APPDATA%\omniroute\storage.sqlite` if `~/.omniroute/storage.sqlite` exists; the former contains stale bootstrap data.

## 2. Priority Pool Waterfall & Standby Spillover
In combos configured with `strategy: "priority"` (such as `ag-gemini-pool-3`):
- Targets are ordered sequentially from Pool 1 to Pool N (e.g., P1 Pro -> P12 Pro -> P13-P18 Starter/Standby).
- Every request attempts target 1 (P1) first.
- Traffic only spills over to lower ranks (e.g., P18) under two specific conditions:
  1. **Concurrency saturation:** Higher-priority accounts reach their `maxConcurrent` ceiling (typically 8 for Pro, 3 for Starter), forcing parallel requests to waterfall down.
  2. **Transient errors / rate-limits:** Cascading 429s or network failures (e.g. DNS 502 `ENOTFOUND cloudcode-pa.googleapis.com`) trip fallback to subsequent accounts.

### Diagnosing "Traffic suddenly stopped entering account X":
1. Query `call_logs` for `account` around the cutoff window:
   ```sql
   SELECT timestamp, status, model, account, error_summary
   FROM call_logs
   WHERE timestamp >= '<start>' AND timestamp <= '<end>'
     AND model != 'connection-test'
   ORDER BY timestamp ASC;
   ```
2. Aggregate calls by account to check where traffic moved:
   ```sql
   SELECT account, count(*) as total, sum(status=200) as ok, sum(status!=200) as err
   FROM call_logs
   WHERE timestamp >= '<incident_day>' AND model != 'connection-test'
   GROUP BY account ORDER BY total DESC;
   ```
3. If traffic shifted back to P1..P10, the pool simply recovered from peak load or upstream transient faults. Standby accounts naturally receive zero traffic when top-priority accounts are idle.
4. Check account health in `provider_connections`:
   ```sql
   SELECT id, name, priority, is_active, test_status, rate_limited_until, backoff_level, last_error
   FROM provider_connections WHERE provider = 'antigravity';
   ```
   If `test_status = 'active'`, `rate_limited_until IS NULL`, and `last_error IS NULL`, the account is fully healthy.

## 3. UI Dashboard Indicators (ProviderLimits)
- **Status Cards & Colors:**
  - `CRITICAL` (Red dot/border): Quota remaining <= 20%.
  - `ALERT` (Amber dot/border): Quota remaining <= 50% and > 20%.
  - `HEALTHY` (Green dot): Quota remaining > 50%.
  - An "ALERT" status on an account card reflects quota depletion level (e.g. 29% remaining), not an account ban or operational failure.
- **Slashed Eye Icon:**
  - Controlled by `useQuotaVisibility.ts` and persisted in `settings.quotaVisibility`.
  - Purely toggles UI row display on the dashboard; does NOT disable or block the model from handling requests.
- **"Token expires in Xm":**
  - Displays Google OAuth access token lifetime (standard 3600s).
  - OmniRoute automatically refreshes tokens via OAuth refresh token flow before expiration.
