# ChatGPT-Web Pool Feeding & Multi-Account Proxy Distribution

## 1. Domain Separation: Hotmail Soaking vs ChatGPT Account Usability
- **Hotmail 7-Day Soak (`WAIT_7D`)**: Appears in the Hotmail account lifecycle before `CHANGE_INFO` (changing recovery mail/password on Microsoft accounts). This is strictly to avoid Microsoft suspicious activity locks.
- **ChatGPT Account Usability**: Once ChatGPT registration succeeds and valid cookies/session tokens exist (`__Secure-next-auth.session-token`), the ChatGPT account is **immediately usable** and does NOT require a 7-day soak. Do not hold back ChatGPT account pool expansion due to Microsoft email lifecycle states.

## 2. Multi-Account Proxy Density & Allocation Invariant
- **Minimum Density per IP**: In multi-account web pools (such as `chatgpt-web`), distribute accounts across active proxies with a density floor: **at least 2 accounts per IP/proxy** (`count >= 2`).
- **Proxy Matching**: Each account extracted from a GPM profile running on a specific proxy (e.g. port `51xx` for MobiProxy or `100xx` for MikroTik) must be assigned that exact proxy in OmniRoute.

## 3. Relational Proxy Binding in OmniRoute SQLite (`storage.sqlite`)
When registering or updating `chatgpt-web` provider connections:
1. **`provider_connections` row**:
   - `provider`: `'chatgpt-web'`
   - `auth_type`: `'apikey'`
   - `api_key`: `__Secure-next-auth.session-token` value
   - `proxy_enabled`: `1`
   - `per_key_proxy_enabled`: `0`
2. **`proxy_assignments` row**:
   - `scope`: `'account'`
   - `scope_id`: `<connection_id>` (`provider_connections.id`)
   - `proxy_id`: `<proxy_id>` (`proxy_registry.id` matching the profile's proxy host:port)
   - `position`: `0`
3. **Canary Validation**:
   - Test each connection immediately after feeding via `POST /v1/chat/completions` with model `chatgpt-web/gpt-5.6-luna-free` and header `x-omniroute-connection-id: <connection_id>`.
   - Verify HTTP 200 before activating or adding to combos (`chatgpt-web-pool`).
