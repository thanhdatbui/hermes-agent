# OmniRoute Per-Account Proxy Egress Assignment Architecture

## Problem Background & Direct IP Leak Pathology
- **Cockpit Tools Limitation**: `cockpit-tools.exe` and its sidecar `cockpit-cliproxy.exe` only support a single global upstream proxy. Accounts within the pool cannot be bound to independent egress IPs. Requests sent directly via the machine host IP result in OpenAI mass token revocation (`401: token_revoked` / `Your session has ended. Please log in again`).
- **OmniRoute Silent Direct Fallback Trap**: In OmniRoute (`port 20129`), having `proxy_enabled = 1` in `provider_connections` is **ONLY a toggle, NOT proof of proxying**. When `proxy_assignments` lacks an `account`-scope record for that connection, `resolveProxyForConnection()` evaluates Steps 3-11 and silently falls through to Step 12 (`level: 'direct'`), sending raw HTTP requests using the host machine IP (`1.53.55.190`). In October 2026, 65 Codex accounts without `proxy_assignments` suffered a 94.4% ban rate (`account_deactivated`) due to this silent leak.
- **False Reporting Anti-Pattern**: NEVER claim an account is proxied based solely on `SELECT proxy_enabled FROM provider_connections`. Coordinator/Worker MUST audit `proxy_assignments` rows AND check `proxy_logs` table (`level != 'direct'`).
- **9Router Codex OAuth Gate**: While 9Router supports `proxyPoolId` on `providerConnections` (failing closed if proxy fails), re-authenticating accounts via browser OAuth frequently triggers OpenAI SMS verification gates (`can co So dien thoai`).
- **OmniRoute Solution**: OmniRoute (`port 20129`) supports per-connection proxy binding via its relational SQLite schema, allowing existing `chatgpt-web` sessions (120+ accounts) to route through dedicated 4G Mobi proxies without re-authenticating or triggering SMS gates.

---

## OmniRoute Proxy Architecture & Database Schema
OmniRoute stores its persistent state in `~/.omniroute/storage.sqlite` (or `C:/Users/<User>/.omniroute/storage.sqlite`).

### Key Tables:
1. **`proxy_registry`**:
   - Stores active proxy endpoints (`id`, `host`, `port`, `username`, `password`, `status`).
   - Example: `test.taadaa.click:5101` (`mobi1`), `5102` (`mobi2`), etc.
2. **`provider_connections`**:
   - Stores individual account sessions (`id`, `provider`, `name`, `email`, `is_active`).
   - For ChatGPT Web: `provider = 'chatgpt-web'`.
3. **`proxy_assignments`**:
   - Enforces per-account proxy mapping:
   ```sql
   CREATE TABLE proxy_assignments (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     proxy_id TEXT NOT NULL,
     scope TEXT NOT NULL,         -- 'account'
     scope_id TEXT,               -- provider_connections.id
     position INTEGER NOT NULL DEFAULT 0,
     created_at TEXT NOT NULL DEFAULT (datetime('now')),
     updated_at TEXT NOT NULL DEFAULT (datetime('now')),
     UNIQUE(scope, scope_id, proxy_id),
     FOREIGN KEY (proxy_id) REFERENCES proxy_registry(id) ON DELETE RESTRICT
   );
   ```

---

## Automated Per-Account Proxy Mapping Procedure
To bind each `chatgpt-web` account to its matching GPM profile's 4G proxy:

1. **Map GPM Profile to Proxy Port**:
   - Query GPM API `http://127.0.0.1:19995/api/v3/profiles` to extract `(email, proxy_port)`.
2. **Match with `proxy_registry`**:
   - Lookup `proxy_id` in `proxy_registry` matching the assigned `port`.
3. **Upsert `proxy_assignments`**:
   ```sql
   DELETE FROM proxy_assignments WHERE scope = 'account' AND scope_id = ?;
   INSERT INTO proxy_assignments (proxy_id, scope, scope_id, created_at, updated_at)
   VALUES (?, 'account', ?, datetime('now'), datetime('now'));
   ```
4. **Verify Egress Execution**:
   - Inspect OmniRoute logs (`omniroute-stdout.log`):
     Verify `[ProxyEgress] chatgpt-web status=success` and ensure `proxy_logs` table records the correct `proxy_host` and `proxy_port`.

---

## Provider-Level Safety Net Pool Architecture
To protect against unassigned or newly added connections silently leaking host IP:
1. **Populate Provider-Level Fallback**:
   Assign all known healthy proxies from `proxy_registry` to `scope = 'provider'` (e.g. `scope_id = 'codex'` or `'chatgpt-web'`).
   ```sql
   INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
   VALUES (?, 'provider', 'codex', 0, datetime('now'), datetime('now'));
   ```
2. **Resolution Mechanics**:
   When `resolveProxyForConnection()` finds no `scope='account'` record, it checks Step 6 (`Provider-level registry`). Having the provider pool populated ensures OmniRoute rotates among healthy proxies rather than falling through to Step 12 (`direct`).

---

## Sync Script Auto-Assignment Invariant
Any script registering or syncing sessions to OmniRoute (e.g. `chatgpt_gpm_direct_reg.py`):
- **MUST** insert into `provider_connections` AND immediately verify/insert a row into `proxy_assignments` (`scope='account'`, `scope_id=connection_id`).
- Creating bare `provider_connections` records without matching `proxy_assignments` is strictly prohibited.
- **Reference Implementation (`sync_registered_chatgpt_web_connection`)**:
  ```python
  cur.execute("SELECT id FROM proxy_assignments WHERE scope='account' AND scope_id=?", (cid,))
  if not cur.fetchone():
      cur.execute("SELECT id FROM proxy_registry WHERE (status IS NULL OR status NOT IN ('inactive','error','disabled','dead','down')) ORDER BY RANDOM() LIMIT 1")
      px_row = cur.fetchone()
      if px_row:
          cur.execute("INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at) VALUES (?, 'account', ?, 0, datetime('now'), datetime('now'))", (px_row[0], cid))
  ```

---

## Verification Trap & Header Pitfall: `x-omniroute-connection` vs False Load-Balancer `200 OK`
- **The Load-Balancer False Positive Trap**: Sending a chat completion request to OmniRoute without forcing a specific connection will be handled by OmniRoute's pool load balancer / fallback logic. If 1 or 2 accounts in the pool are healthy, the request returns `200 OK`, leading operators to falsely conclude that *all* or *the targeted* connection is alive.
- **Mandatory Header for Pinned Probes**: OmniRoute (`src/sse/handlers/chat.ts`) strictly listens to **`x-omniroute-connection: <connection_id>`** (NOT `x-connection-id`). Probing with any other header name causes OmniRoute to ignore the pin and serve the request from an arbitrary live account.
- **Account Deactivation Blast Radius (`account_deactivated`)**: When OpenAI issues an account deactivation (`trustandsafety@tm.openai.com`), it bans the underlying OpenAI account entity. Even though Web session tokens (`__Secure-next-auth.session-token`) and Codex OAuth tokens use different auth flows, **a deactivated account is dead across BOTH Codex and ChatGPT Web** (returning HTTP 403 `SENTINEL_BLOCKED` / deactivation on Web).
- **Post-Mortem Reality (October 2026 Audit)**:
  - 43 accounts overlapping with the banned Codex set failed with 403 when forced via `x-omniroute-connection`.
  - 59 clean accounts (22 Gmail, 37 Hotmail not hit by the direct IP deactivation) remain 100% LIVE and responsive (`200 OK` ~1.8s).
  - Operators must mark deactivated accounts `is_active = 0` / `test_status = 'banned'` in SQLite to eliminate useless retries and latency overhead.

---

## SQLite Database Bloat & WAL Lock Remediation (`state.db`)
- **Symptom**: Runtime abruptly halts turns with: `session storage could not be written (often a full disk)`.
- **Root Cause**: When `state.db` grows large (>14 GB), heavy concurrent write traffic causes SQLite transactions to hit `busy_timeout` (3000ms), which Hermes misinterprets as an OS disk-full or permissions failure.
- **O(1) Resolution**: Execute passive WAL checkpointing without exclusive database locking:
  ```python
  import sqlite3
  conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\hermes\state.db', timeout=5)
  conn.execute('PRAGMA wal_checkpoint(PASSIVE)')
  conn.close()
  ```

---

## Hermes Fallback & Alias Configuration
In `~/.hermes/config.yaml`:
- Evict deprecated `cockpit` from `custom_providers`.
- Point Luna models to OmniRoute's `gpt-web-luna`:
  ```yaml
  model:
    aliases:
      luna: custom:omni/gpt-web-luna
      luna-6: custom:omni/gpt-web-luna
      gpt-6-luna: custom:omni/gpt-web-luna
  ```
- Omni provider in `custom_providers`:
  ```yaml
  - name: omni
    base_url: http://192.168.110.123:20129/v1
    models:
      gpt-web-luna: { context_length: 256000 }
  ```
