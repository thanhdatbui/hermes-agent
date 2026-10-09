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
  3. Click "Làm mới ngay (Refresh now)" on the account card to refresh the OAuth token.

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

---

## 4. OmniRoute Provider / Combo APIs

```bash
# List combos
curl http://localhost:20129/api/combos

# List provider connections
curl http://localhost:20129/api/providers

# Get specific provider
curl http://localhost:20129/api/providers/<provider-id>

# Update provider (including providerSpecificData)
curl -X PUT http://localhost:20129/api/providers/<provider-id> \
  -H "Content-Type: application/json" \
  -d '{"providerSpecificData": {"accountProxies": [...], "autoFetchModels": true}}'

# Trigger model sync/import
curl -X POST http://localhost:20129/api/providers/<provider-id>/sync-models?mode=import
```

---

## 5. Proxy Registry (OmniRoute)

### Tables
- `proxy_registry` — proxy definitions (id, name, type, host, port, username, password, region, notes, status, ...)
- `proxy_assignments` — links proxy_id → scope_id (provider connection id)
- `free_proxies` — free proxy pool (currently empty in this env)

### Proxy Import Script Pattern
```python
import sqlite3, uuid
db = sqlite3.connect(r'C:\Users\Kibe\AppData\Roaming\omniroute\storage.sqlite')
cursor = db.cursor()

# Insert proxy
proxy_id = str(uuid.uuid4())
cursor.execute('''
    INSERT OR IGNORE INTO proxy_registry 
    (id, name, type, host, port, username, password, region, notes, status, created_at, updated_at, source, quality_score, latency_ms, anonymity, google_access, last_validated, country_code, family)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)
''', (proxy_id, name, 'http', host, port, user, pwd, region, notes, 'active', 'manual', 0, None, 'high', 1, None, 'VN', 'http'))

# Assign to provider connection
cursor.execute('''
    INSERT OR IGNORE INTO proxy_assignments (id, proxy_id, scope_id, scope, created_at, updated_at)
    VALUES (?, ?, ?, 'provider_connection', datetime('now'), datetime('now'))
''', (str(uuid.uuid4()), proxy_id, connection_id))

db.commit()
```

---

## 6. Model Discovery & Sync (OmniRoute)

When upstream launches new models (e.g., `gemini-3.8-flash-tiered`):

1. Enable auto-fetch on connection:
```bash
curl -X PUT http://localhost:20129/api/providers/<conn-id> \
  -H "Content-Type: application/json" \
  -d '{"providerSpecificData": {"autoFetchModels": true, "autoSync": true}}'
```

2. Trigger import:
```bash
curl -X POST http://localhost:20129/api/providers/<conn-id>/sync-models?mode=import
```

Discovered models become callable immediately without static catalog release.

---

## 7. Combo Structure

### Nested Combo (Pool inside Pool) — CRITICAL
Must use `combo-ref` NOT `model`:
```json
{
  "kind": "combo-ref",
  "comboName": "ag-gemini-pool-3"
}
```
Wrong (causes failover to next tier on first glitch):
```json
{
  "kind": "model",
  "model": "combo/ag-gemini-pool-3",
  "providerId": "combo"
}
```

---

## 8. Single-Account Live Verification

To test one pool member without altering combos:
```bash
curl -H "x-omniroute-connection-id: <conn-id>" \
  -X POST http://localhost:20129/v1/chat/completions \
  -d '{"model":"antigravity/gemini-3.7-flash-high","messages":[{"role":"user","content":"ping"}]}'
```

Or create temporary single-target combo: `strategy: priority`, `maxRetries: 0`, exact `connectionId`.

---

## 9. Model ID Fidelity Rule

**ALWAYS use exact upstream model ID** (e.g., `antigravity/gemini-3.8-flash-tiered`).

**NEVER invent aliases** (e.g., `gemini-3.8-flash-high`) and patch core source (`modelSpecs.ts`, `antigravityModelAliases.ts`) then rebuild — causes service crash.

Test single request in isolation before updating entire combo.

---

## 10. Proxy Auth Specifics

### MikroTik
- Host: `mirotik1.taadaa.click`
- Ports: `10001..10035`
- Auth: `admin@1:admin@1` (MUST be in proxy_registry username/password, else background token refresh fails with 503)

### Farm Proxies
- Host: `test.taadaa.click`
- Ports: `5101..5138`
- Auth: `mobi1..mobi38` : `admin@1`

---

## 11. Backup & Sync

All combo changes MUST be exported and synced:
```bash
curl http://localhost:20129/api/combos > D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json
# commit & push to AI-Tools.git
```

**Repo location:** ONLY `D:\Taadaa\AI-Tools` (forbid clone at `D:\OneDrive\AI-Tools`).

---

## 12. Host Quirk
Port `:20129` may show OPEN on raw socket while `http://127.0.0.1:20129` refuses; prefer `http://localhost:20129` for API calls.

---

## 13. Codex (OpenAI) Deprecation on 9Router & Migration to OmniRoute (:20129)

### User Invariant & Policy (2026-09-05)
- **User Directive**: *"Nhưng oath token vào omni router, k dùng 9router nữa"* (Chuyển toàn bộ Codex OAuth sang OmniRoute `:20129`, ngừng sử dụng Codex trên 9Router `:20128`).
- Khi kiểm tra dàn 6 tài khoản Codex cũ trong 9Router (`data.sqlite`):
  - `bevels.vanity8s@icloud.com` (Port 5108 / 5101)
  - `dishes.66-panic@icloud.com` (Port 5102)
  - `98.duper-comb@icloud.com` (Port 5103)
  - `coaster.leafed-5x+5diuz@icloud.com` (Port 5104)
  - `bulbous_elector_3m@icloud.com` (Port 5105)
  - `quocthanhthao.962@outlook.com` (Port 5111)
  -> Toàn bộ đều đã bị máy chủ OpenAI vô hiệu hóa (`error_code: account_deactivated`). Lý do 9Router liên tục báo lỗi `TOKEN_REFRESH Codex refresh token already used or invalid (401)`.

### Quy trình nạp Codex OAuth mới vào OmniRoute (:20129)
1. **Khởi động Callback Server**: Gọi `GET http://localhost:20129/api/oauth/codex/start-callback-server` (OmniRoute lắng nghe cổng cố định `1455` và trả về `authUrl`).
2. **Kỷ luật tuần tự (Sequential)**: Vì callback server chỉ lắng nghe 1 luồng duy nhất trên cổng 1455 tại một thời điểm, các profile GPM **BẮT BUỘC** phải chạy tuần tự từng máy (CẤM chạy song song).
3. **Mở Profile GPM theo Port tương ứng**: Mở profile kèm proxy 4G Farm (`test.taadaa.click:5101..5138`), tab điều hướng tới `authUrl`.
4. **Dual-Capture Callback**: Hook network Playwright `page.on("request")` bắt URL chứa `1455/auth/callback` và forward trực tiếp về `http://127.0.0.1:1455` để tránh lỗi hairpin NAT proxy.
5. **Gán Proxy 1:1 theo Account Scope**:
   - Sau khi exchange token thành công (`POST /api/oauth/codex/poll-callback`), OmniRoute sinh `connectionId`.
   - Lập tức tra cứu `proxyId` từ port Mobi tương ứng và gọi:
     ```bash
     curl -X PUT http://localhost:20129/api/settings/proxies/assignments \
       -H "Content-Type: application/json" \
       -d '{"scope": "account", "scopeId": "<connectionId>", "proxyId": "<proxyId>"}'
     ```
6. **Script Canonical**: `D:/Taadaa/GPM auto/scripts/run_codex_oauth_flow.py` (chạy bằng `python` Python 3.11 hoặc `env -u PYTHONPATH`).
