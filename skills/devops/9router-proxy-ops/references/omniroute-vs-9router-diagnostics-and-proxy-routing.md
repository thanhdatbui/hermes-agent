# OmniRoute vs 9Router Diagnostics & Proxy Routing

## 1. System Disambiguation & Directory Topology

Always distinguish the two routing services when diagnosing account, quota, or model errors:

| Feature | 9Router | OmniRoute |
| :--- | :--- | :--- |
| **Port** | `:20128` | `:20129` |
| **App Location** | `%APPDATA%\npm\node_modules\9router\app` | `C:\Users\Kibe\OmniRoute` |
| **Active DB Path** | `%APPDATA%\9router\db\data.sqlite` | `C:\Users\Kibe\.omniroute\storage.sqlite` *(Note: `.omniroute` legacy path has precedence over `%APPDATA%\omniroute`)* |
| **Watchdog** | `%APPDATA%\9router\9router_watchdog.ps1` | `%APPDATA%\omniroute\omniroute_watchdog.ps1` |
| **Supervisor Mutex** | `Local\9Router_Supervisor_Mutex_v2` | `Local\OmniRoute_Supervisor_Mutex_v1` |

---

## 2. OmniRoute Account Failure Modes & Diagnostics

In OmniRoute (`storage.sqlite`), account connections live in `provider_connections` with explicit columns (`id`, `provider`, `name`, `email`, `priority`, `is_active`, `proxy_enabled`, `provider_specific_data`, `test_status`, `error_code`, `last_error`, `expires_at`, `token_expires_at`).

### A. "Load failed" / "HTTP 503: fetch failed" / "Token expired" (Red Card in Quota Dashboard)
- **Root cause:** The account has `proxy_enabled = 1` and an assignment in `proxy_assignments` (`scope = 'account'`, `scope_id = <connection_id>`), but the assigned proxy in `proxy_registry` is unreachable, dead, or timing out (e.g. MikroTik proxy down).
- When the account's OAuth token expires (e.g. after 1 hour), OmniRoute attempts token refresh through the dead proxy. This causes `Proxy request failed: fetch failed` -> sets `error_code = 'refresh_transient'` / `'refresh_failed'` -> UI card turns red and displays `Load failed` / `Token expired`.
- **Diagnosis Script:**
  ```python
  import sqlite3
  conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
  cursor = conn.cursor()
  cursor.execute('''
    SELECT pc.id, pc.name, pc.is_active, pc.error_code, pc.last_error, pr.name, pr.host, pr.port
    FROM provider_connections pc
    LEFT JOIN proxy_assignments pa ON pa.scope_id = pc.id AND pa.scope = 'account'
    LEFT JOIN proxy_registry pr ON pa.proxy_id = pr.id
    WHERE pc.provider = 'antigravity'
  ''')
  for r in cursor.fetchall():
      print(r)
  ```
- **Remediation:**
  1. Test the proxy connectivity with `curl -x http://<host>:<port> https://www.google.com --connect-timeout 5`.
  2. If dead, reassign or remove the dead proxy assignment in `proxy_assignments` or Dashboard UI.
  3. Click **"Làm mới ngay (Refresh now)"** on the account card to refresh the OAuth token.

### B. Inactive Accounts (`is_active = 0` / Toggle OFF)
- **Root cause:** Toggle switch is disabled in the UI, or the account was imported without required fields (e.g. empty `projectId: ''`).
- **Remediation:** Verify account configuration in `provider_specific_data`, ensure `projectId` is populated, and flip `is_active = 1` in UI or DB.

---

## 3. 9Router 429 Priority Demotion & "No Active Credentials"

In 9Router (`data.sqlite`):
- When accounts receive repeated `429 Quota Exceeded` errors, 9Router automatically demotes the account `priority` to `9999` (persisting `priorityBase` in JSON `data`).
- If **ALL** accounts for a provider reach `priority >= 9000`, 9Router treats the provider as having no available accounts and returns:
  `{"error": "No active credentials for provider: antigravity", "status": 404}`
- **Remediation:**
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
  Then restart the 9Router process (watchdog will supervise or launch via background terminal).
