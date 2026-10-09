# OpenCode Free Tier Proxy Rotation Configuration

## Problem
In combo `omni-free`, OpenCode models (`oc/muse-spark-*`, `oc/mimo-*`) default to direct egress (`proxy: null`). When the single egress IP is rate-limited (429/503), the executor has no fallback proxy, causing immediate failover to the next model in the combo instead of retrying on a different proxy.

## Solution
Configure proxy rotation for OpenCode via `providerSpecificData.accountProxies` in the provider connection row.

## Steps

### 1. Import Proxies to `proxy_registry`
Use the combined proxy list from both Kibe and Admin pools (68 unique proxies):

```python
# Sources:
# - D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx (80 rows, 40 unique)
# - D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx (80 rows, 28 unique)
# Total: 68 unique proxies across 3 types:
#   1. MikroTik mirotik1.taadaa.click:10001..10035 (admin@1:admin@1)
#   2. Farm test.taadaa.click:5101..5138 (mobi1..mobi38)
#   3. khoalee.duckdns.org:16002 (5ns08q:AmLmaMJ0)
```

### 2. Create/OpenCode Connection with `accountProxies`
Each fingerprint (virtual account) maps to one proxy. For no-auth OpenCode, fingerprints are synthetic IDs (e.g., `opencode-free-1`, `opencode-free-2`, ...).

```json
{
  "provider": "opencode",
  "name": "opencode-free-pool",
  "providerSpecificData": {
    "accountProxies": [
      {"fingerprint": "opencode-free-1", "proxyId": "<proxy-uuid-1>"},
      {"fingerprint": "opencode-free-2", "proxyId": "<proxy-uuid-2>"},
      ...
    ]
  }
}
```

Or inline proxy objects (escape hatch):
```json
{
  "accountProxies": [
    {"fingerprint": "opencode-free-1", "proxy": {"type": "http", "host": "test.taadaa.click", "port": 5101, "username": "mobi1", "password": "admin@1"}},
    ...
  ]
}
```

### 3. Hydration at Runtime
OmniRoute's `loadNoAuthProviderSpecificData()` → `resolveAccountProxiesFromRegistry()` resolves `proxyId` to live proxy records, producing `fingerprint + proxy` entries consumed by `OpencodeExecutor`.

### 4. Rotation Behavior
- `OpencodeExecutor.execute()` iterates `this.accounts` (one per fingerprint).
- Each account has its own `proxy` → `runWithProxyContext(account.proxy, ...)` pins egress.
- On 429/network error: `markCooldown(account)` → rotate to next account (different proxy).
- Shared-egress guard skips proxy-less accounts if direct egress is down; proxied accounts still tried.

### 5. Verification
```bash
# Check proxies in registry
curl http://localhost:20129/api/proxies

# Check OpenCode connection has accountProxies
curl http://localhost:20129/api/providers/opencode

# Test single-account dispatch via header
curl -H "x-omniroute-connection-id: <conn-id>" \
  -X POST http://localhost:20129/v1/chat/completions \
  -d '{"model":"oc/muse-spark-1.3-contributor-free","messages":[{"role":"user","content":"ping"}]}'
```

## Key Files
- `open-sse/executors/opencode.ts` — executor logic, `syncAccountsFromCredentials`, rotation loop
- `open-sse/executors/accountRotation.ts` — shared rotation utilities
- `src/sse/services/noAuthProxyResolution.ts` — `resolveAccountProxiesFromRegistry`
- `src/sse/services/auth.ts` — `loadNoAuthProviderSpecificData`
- `src/shared/components/NoAuthAccountCard.tsx` — UI for managing accountProxies

## Notes
- Never mutate `providerSpecificData` directly in SQLite; use API `PUT /api/providers/[id]`.
- Keep proxy list in sync with `proxy_combined_pool.txt` and both Excel sources.
- For 68 proxies, create 68 fingerprints to fully utilize pool.