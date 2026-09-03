# OmniRoute 3-Layer Proxy Resilience & Direct Fallback

## 1. Proxy Scope Hierarchy in OmniRoute

OmniRoute resolves proxies for outgoing requests through a deterministic precedence cascade (`src/lib/db/settings.ts` -> `resolveProxyForConnection` and `src/lib/db/proxies/rotation.ts`):

1. **Step 1: API Key Scope (`scope='apiKey'`)** (if per-key proxy is enabled).
2. **Step 2: Account Scope (`scope='account'`)** (`proxy_assignments` matching `scope_id = connectionId`).
3. **Step 3: Provider Scope (`scope='provider'`)** (`proxy_assignments` matching `scope_id = provider`, e.g. `antigravity`).
4. **Step 4: Combo Scope (`scope='combo'`)** (`proxy_assignments` matching `scope_id = comboId`).
5. **Step 5: Global Scope (`scope='global'`)** (any global proxy assignment).
6. **Step 6: Direct IP / Fail-Closed Guard**.

---

## 2. The Single-Host Proxy Failure Mode (Incident 2026-08-27 22:29)

### Symptom
- Upstream proxy host (e.g. `test.taadaa.click`) loses connectivity or ports close.
- OmniRoute's `[Proxy Fast-Fail]` TCP reachability probe fails across all ports (`5102`, `5104`, `5111`).
- Every target in a priority combo (`ag-gemini-pool-3`: Target 1 -> Target 2 -> Target 3) is attempted, fails fast with `503 Proxy Unreachable`, and the combo terminates with `503 ALL_TARGETS_SKIPPED`.
- In-flight Hermes Gateway sessions abort with `The model provider failed after retries...`.

### Root Cause
All accounts in the pool were assigned individual ports on the **same physical proxy host**. When the host suffered a network drop, the entire combo collapsed simultaneously because no cross-host backup pool existed and data-plane chat defaulted to fail-closed (`PROXY_FAIL_OPEN=false`).

---

## 3. Production 3-Layer Resilience Architecture

To prevent LLM dropouts during proxy outages without losing egress IP separation during normal operation:

### Layer 1: Dedicated Account Scope (Primary)
- **Account Scope (Primary):** Assign 1 dedicated mobile/residential proxy to each Antigravity account (e.g. `dokieu` -> `mobi11:5111`, `marcusep` -> `mobi2:5102`, `dinhlan` -> `mobi4:5104`) for strict IP separation.
- Stored in `proxy_assignments` where `scope='account', scope_id=<connection_id>`.

### Layer 2: Combined Provider Fallback Pool (69 Ports + Round-Robin)
- **Provider Scope (Backup Pool):** Populate `proxy_registry` with the full combined pool:
  - 35 Mirotik ports (`mirotik1.taadaa.click:10001`–`10035`)
  - 32 Mobi ports (`test.taadaa.click:5101`–`5138`)
  - 2 KhoaLee ports (`khoalee.duckdns.org:16001`–`16002`)
  Total: 69 active ports.
- Assign all 69 proxies to `scope='provider', scope_id='antigravity'`.
- Set `proxy_scope_rotation` for `(scope='provider', scope_id='antigravity')` to strategy `'round-robin'`.
- **Behavior:** If an account's primary proxy is inactive/dead or hangs, OmniRoute fails fast (< 1.5s) and falls through to the 69-port Provider Pool, rotating candidates seamlessly without needing manual assignment of 69 proxies per account.

### Layer 3: Final Direct IP Fail-Safe (Phao Cứu Sinh)
- If all proxy candidates across both Account and Provider pools are unreachable (e.g. total proxy network blackout):
- Set `PROXY_FAIL_OPEN=true` and `OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK=true` in:
  - `C:\Users\Kibe\OmniRoute\.env`
  - `C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`
- In `open-sse/utils/proxyFetch.ts`: when `!unreachableProbe.reachable` or family pre-check fails and `PROXY_FAIL_OPEN=true`, downgrade to `runDirect()` instead of throwing `PROXY_UNREACHABLE (503)`.

---

## 4. Key Pitfalls & Verification

1. **URL Encoding in Proxy Auth:**
   - Credentials containing `@` (e.g. `username: admin@1`, `password: admin@1`) MUST be URL-encoded as `%40` (`admin%401:admin%401`) in proxy connection URLs (`http://admin%401:admin%401@mirotik1.taadaa.click:10001`).
   - Unencoded `@` splits the URL authority prematurely and causes `Invalid proxy URL` or connection failures in `undiciFetch` / `curl`.
2. **Testing Proxy Connectivity:**
   ```bash
   # Test HTTP proxy with URL-encoded credentials
   curl -s -x "http://admin%401:admin%401@mirotik1.taadaa.click:10001" https://api.ipify.org?format=json --connect-timeout 5
   ```
3. **Database Inspection & Assignment Verification:**
   ```python
   import sqlite3
   conn = sqlite3.connect('file:///C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
   c = conn.cursor()
   # Verify account assignments (Layer 1)
   c.execute("SELECT a.scope_id, p.name, p.host, p.port FROM proxy_assignments a JOIN proxy_registry p ON p.id = a.proxy_id WHERE a.scope = 'account'")
   print("Account assignments:", c.fetchall())
   # Verify provider pool count (Layer 2)
   c.execute("SELECT count(*) FROM proxy_assignments WHERE scope = 'provider' AND scope_id = 'antigravity'")
   print("Provider pool count:", c.fetchone()[0])
   ```
