# OmniRoute ChatGPT-Web Pool Feeding from GPM Profiles

Patterns and pitfalls for harvesting and feeding ChatGPT-Web session tokens from local GPM profiles into an OmniRoute proxy instance (`storage.sqlite` / port 20129) with strict proxy alignment.

## 1. Domain Separation (Hotmail Direct Auth vs Gmail SSO)

- **Hotmail Registered ChatGPT Fleet**:
  - Accounts registered via Hotmail use **Direct Email + Password** auth.
  - **SSO Trap**: Never trigger Google SSO (`Continue with Google` / `accounts.google.com`) on Hotmail profiles. It causes a 40s timeout at the Google Account Chooser.
  - State machine check: Hotmail accounts in stage `WAIT_7D` are soaking the Hotmail mailbox, but their ChatGPT accounts are already registered and usable immediately.
- **Gmail Registered ChatGPT Fleet**:
  - Uses Google OAuth SSO. Handles `accounts.google.com/signin/oauth/v3/consent` and account chooser.

## 2. Fast Session Token Extraction (CDP Probe First)

- **Active Session Priority**: Over 80% of registered GPM profiles already hold a live `__Secure-next-auth.session-token` cookie in the browser profile.
- **Fast Extraction Pattern (< 5s per account)**:
  1. Start GPM profile via `GET http://127.0.0.1:19995/api/v3/profiles/start/{pid}?win_scale=0.8`.
  2. Connect Playwright over CDP to `remote_debugging_address`.
  3. Navigate to `https://chatgpt.com/` (`wait_until="domcontentloaded"`, timeout=15s).
  4. Immediately check `context.cookies('https://chatgpt.com')` for `__Secure-next-auth.session-token` (including chunked cookies `.0`, `.1`).
  5. If valid token exists (`len(token) > 20`): save evidence screenshot and return immediately.
  6. If session expired / login required: do not block or hang in 40s OAuth loops. Fail-fast or skip to the next candidate profile on that proxy port.
  7. Stop GPM profile immediately to release RAM and kill orphaned Chrome PIDs.

## 3. Strict Per-IP Ceiling & Proxy Assignment (`proxy_assignments`)

- **Capacity Invariant**:
  - Operators often request strict per-IP limits (e.g. max 2 accounts per IP).
  - Calculate exact deficit per proxy port: `needed = max(0, TARGET_PER_IP - current_active_count)`.
  - Skip any proxy that already has $\ge$ target accounts.
- **Fail-Closed Relational Binding**:
  - In `storage.sqlite`, each connection in `provider_connections` (`provider = 'chatgpt-web'`) MUST be paired with a row in `proxy_assignments`:
    - `scope = 'account'`
    - `scope_id = <connection_id>`
    - `proxy_id = <proxy_registry_id>`
  - Ensure `proxy_enabled = 1` in `provider_connections`.
  - Ensure the connection ID is appended to active combos (`chatgpt-web-pool`, `gpt-web-sol`).
- **Missing Port Trap in Feeder Results**:
  - Ensure the account result dict preserves `port`: `res["port"] = acc.get("port")`.
  - Omitting `port` in the result payload causes `sync_to_omniroute` to fail-closed and silently skip activation.

## 4. Concurrency Sizing

- Running GPM browser automation in parallel must be capped at 2–4 workers (`ThreadPoolExecutor(max_workers=3)`).
- Spawning > 5 simultaneous Chromium instances leads to GPM local API contention (port 19995), RAM bloat, and proxy socket saturation.
