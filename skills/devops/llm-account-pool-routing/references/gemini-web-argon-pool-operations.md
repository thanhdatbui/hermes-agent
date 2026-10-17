# Gemini Web 4 Argon Pool Operations & Sticky Session Routing

## Architecture & Background
1. **Google AI Pro Model Surface**:
   - `gemini.google.com/app` holds exclusive access to **`4 Argon`** (labeled: `4 Argon - Nhiệm vụ phức tạp - MỚI`) and `Cấp độ tư duy` (Thinking Level).
   - These models are NOT exposed via the standard Antigravity IDE API (`daily-cloudcode-pa.googleapis.com:fetchAvailableModels`).
   - Accounts with `g1-pro-tier` subscriptions unlock `4 Argon` directly on the Web UI.

2. **Authentication via Web Session Cookies**:
   - The `gemini-web` provider does not use OAuth tokens. It authenticates via cookies:
     - `__Secure-1PSID` (primary session secret, ~150 chars)
     - `__Secure-1PSIDTS` (rolling timestamp signature, ~75 chars)
     - `__Secure-1PSIDCC` (client check token, ~70 chars)

---

## Automated Extraction via GPM Chrome DevTools Protocol (CDP)
To extract cookies without manual copy-paste:
1. **Start Profile**: Query GPM local API `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
2. **Read Remote Debugging Address**: Retrieve `remote_debugging_address` (e.g. `127.0.0.1:59568`).
3. **Connect via WebSocket CDP**:
   - Connect to `ws_url` from `http://{debug_addr}/json`.
   - Issue CDP method `Storage.getCookies`.
   - Filter cookies for domain `.google.com` matching `__Secure-1PSID*`.
4. **Clean Shutdown**:
   - Issue `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.
   - Scan and terminate orphaned `gpm_browser_chromium_core.exe` processes via `psutil` to prevent RAM exhaustion.

---

## Direct HTTP StreamGenerate vs Headless Playwright
OmniRoute (`open-sse/executors/gemini-web.ts`) originally relies on Playwright Chromium (`chromium.launch({ headless: true })`).
- **Playwright Trap**: Missing Chromium builds or folder structure mismatches (e.g. `chrome-win64` vs `chrome-win`) cause HTTP 503 `Playwright Chromium browser is not installed`.
- **Direct HTTP RPC Protocol**:
  Gemini Web's streaming RPC can be dispatched directly over HTTP POST in ~2.6s without Playwright:
  ```http
  POST https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate?bl={build_label}&rt=c HTTP/1.1
  Host: gemini.google.com
  Cookie: __Secure-1PSID=...; __Secure-1PSIDTS=...
  Content-Type: application/x-www-form-urlencoded;charset=UTF-8
  
  f.req=[null,"[[\"PROMPT\",0,null,null,null,null,0],[\"vi\"],[...]]"]&at={SNlM0e_token}
  ```
  - `SNlM0e` token and `cfb2h` (build label) are parsed from the initial `GET https://gemini.google.com/app` HTML payload.

---

## DOM Dynamics for Selecting `4 Argon`
On the web UI, requests default to `Gemini Flash`:
1. Find the model switcher button: `div.chat-app button[aria-haspopup="menu"]` (displays text `Gemini\nFlash`).
2. Click button to open the Angular overlay menu (`div.cdk-overlay-container`).
3. Select menu item matching text `4 Argon` (or `Argon`).
4. Enter prompt into `.ql-editor` or `[contenteditable=true]`.
5. Click send button `button[aria-label*="Send"]` or dispatch `Enter` key event.

---

## Rotation Strategy: Least-Used vs Cache-Optimized (Sticky Session)
In OmniRoute (`open-sse/services/combo.ts`), multi-account pools support various strategies:
1. **The Round-Robin Flaw**:
   - Round-robin rotates turns across accounts ($1 \to 2 \to 3 \to 4 \to 5$).
   - In multi-turn tasks (ReAct agents, iterative bug-fixing), changing accounts every turn destroys server-side KV-cache affinity. Each turn forces Google servers to re-process tens of thousands of prefix tokens from scratch, increasing TTFT latency by 3–5 seconds.
2. **Cache-Optimized (Sticky Session) Advantage**:
   - `strategy: "cache-optimized"` with `config: { sticky: true }`.
   - Hashes the session prefix or session ID to pin all consecutive turns of a single task to one account.
   - Preserves Google's warm KV-cache across turns, slashing latency by ~50% and improving multi-turn context retention.
   - Independent tasks are distributed across sibling accounts (`dokieu`, `namdung`, `vuthao`, `ninhvan`, `tachau`).
3. **Failover**:
   - If the pinned account encounters HTTP 429 / 503, OmniRoute's circuit breaker unpins and fails over to the next eligible account in the pool.

---

## OmniRoute Proxy Fast-Fail Trap
- **Mechanism**: `open-sse/utils/proxyFetch.ts` runs a non-blocking TCP reachability probe before dispatching upstream requests.
- **Trap**: If an unrelated dead proxy (e.g. legacy `mirotik1.taadaa.click:10001` assigned to `antigravity` or `openrouter`) experiences a socket drop, `[Proxy Fast-Fail]` can fire globally, causing immediate HTTP 503 `Proxy unreachable` across all pool targets before per-connection proxies (`proxy_assignments`) are tried.
- **Remediation**: Check `proxy_registry` and remove dead proxies from `proxy_assignments` scopes (`scope='provider'`, `scope='global'`).
