# OmniRoute Account Proxy Fallback to Provider Pool

## Root Cause & Architecture
When connection accounts (e.g. Antigravity / Gemini accounts) have dedicated account-level proxy assignments in `proxy_assignments` (scope=`account`), `resolveProxyForConnection()` in `src/lib/db/settings.ts` evaluates them before provider-level or global pools.

If an account-level proxy host/port dies or times out (TCP probe failure):
1. **Resolution Failure without Fallback:** Previously returned the dead proxy immediately. Egress TCP connection timed out or triggered non-blocking Fast-Fail (502 / `PROXY_UNREACHABLE`), causing OmniRoute to fail the request with `503 ALL_TARGETS_SKIPPED`.
2. **Resilient Resolution Pattern:**
   - Probe the account proxy via `isProxyReachable(proxyHealthUrl(accountProxy))` with the configured TCP timeout / in-memory cache TTL.
   - If the account proxy is unreachable (or has an invalid/malformed health URL), query `getAliveProxyPoolForScope("provider", connectionProvider)` to retrieve the healthy candidates in position order from the provider scope pool (e.g. Mirotik / Taadaa provider pool).
   - Cache and return the reachable provider pool proxy to prevent cascading request stalls.

## Runtime In-Memory & Dev Mode Pitfalls
1. **Standalone Bundle Stale Trap:** When editing source files in `src/` or `open-sse/`, running `node scripts/dev/run-next.mjs start` (or `npm run start`) runs the pre-compiled code in `.build/next/standalone` or `.next/standalone`. Any newly edited code will NOT be active in-memory, causing live requests to continue failing with old behavior.
2. **Dev Hot-Reloading Execution:** Use `node scripts/dev/run-next.mjs dev` (or rebuild standalone bundle) to ensure live requests load the updated TypeScript source.
3. **Live Verification Canary:** After restarting, verify both:
   - Direct OmniRoute port 20129: `POST /v1/chat/completions` with combo model `ag-gemini-pool-3` -> expects `200 OK`.
   - 9Router gateway port 20128: `POST /v1/chat/completions` with model `ag/gemini-3.7-flash-high` -> expects `200 OK`.

## Health URL Construction & Verification Pitfalls (Review Invariants)
When validating or formatting proxy URLs for reachability probing in `src/lib/db/settings.ts`:
1. **URL Scheme Whitelist:** Restrict `type` to valid schemes (`http`, `https`, `socks5`, `socks5h`, `socks4`).
2. **Authority & Delimiter Sanitization:** Reject control characters, spaces, and delimiters (`[\s/@?#\\]`) in raw hostnames to prevent SSRF / authority injection.
3. **IPv6 Literal Handling:** Ensure IPv6 literals with colons are bracketed (e.g. `[::1]`) before constructing URLs.
4. **Proxy Authentication:** Encode `username` and `password` if present (`${encodeURIComponent(user)}:${encodeURIComponent(pass)}@`) so authenticated proxies are probed with proper credentials.
5. **Default Port Normalization:** WHATWG `URL` normalizes `http:80` and `https:443` to empty string `parsed.port === ""`. Account for default ports when verifying parsed port matches the input port.
6. **Plan-Review via 9Router:** When invoking `plan-review` / `plan-review-hard` via HTTP on `127.0.0.1:20128`, obtain the authorization bearer token from `%LOCALAPPDATA%/hermes/config.yaml` (`api_key`).

## Git Remote Topology for OmniRoute Workspace
- Upstream repo: `https://github.com/diegosouzapw/OmniRoute.git` (read-only for `thanhdatbui`, push returns 403).
- Personal target repo: `https://github.com/thanhdatbui/AI-Tools.git` under branch `omniroute-main`.
- Remote setup:
  ```bash
  git remote rename origin upstream
  git remote add origin https://github.com/thanhdatbui/AI-Tools.git
  git push -u origin main:omniroute-main
  ```
