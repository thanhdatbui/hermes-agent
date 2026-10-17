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

## Sync Script Auto-Assignment & Fail-Closed Activation Invariant
Any script registering or syncing sessions to OmniRoute (e.g. `chatgpt_gpm_direct_reg.py`, `feed_one_acc_per_ip_omniroute.py`):
- **MUST** enforce the **Atomic 3-Step Fail-Closed Sequence** to prevent the mass ban catastrophe ("Cấm lặp lại lỗi làm ban 1 mớ acc của tao"):
  1. **Step 1 (Safe Staging):** Insert/Update `provider_connections` with `is_active = 0` (inactive by default).
  2. **Step 2 (Deterministic Proxy Assignment):** Query `proxy_registry` by exact `(host, port)` extracted from GPM profile / SoT. Insert into `proxy_assignments` (`scope='account'`, `scope_id=cid`).
     - *CẤM TUYỆT ĐỐI* `ORDER BY RANDOM()`.
     - *CẤM TUYỆT ĐỐI* gán chéo proxy giữa Kibe (5101..5138, 10001..10007) và Admin (10008..10035).
  3. **Step 3 (Gated Activation):** ONLY AFTER `proxy_assignments` row is confirmed to exist, execute:
     ```sql
     UPDATE provider_connections SET is_active = 1, test_status = 'active' WHERE id = ?;
     ```
  - *Hard Invariant:* If Step 2 fails (proxy dead or missing from registry), the connection **STAYS `is_active = 0`**. Never activate an account without confirmed proxy binding!
  - *Hard Anti-Deception Invariant:* Coordinator/Worker must NEVER report or conclude "Đang cho rà soát / Đang xử lý" without an active background process (`terminal(background=True)` or `delegate_task`). Stating an action as in-progress without an active PID or transcript handle is a critical violation.
  - *ChatGPT-Web Pool Auto-Feed Candidate Starvation Pitfall:* Trong cron nạp tài khoản tự động (`cron_auto_feed_chatgpt_pool.py`), nếu truy vấn chỉ lấy `LIMIT 10` từ GPM profiles mà không phân vùng, các tài khoản Gmail cũ bị hết hạn session token (kẹt ở màn hình Google OAuth `accounts.google.com/v3/signin/...`) sẽ chiếm trọn danh sách ứng viên, dẫn đến cron nạp `0/10` liên tục và bỏ đói hàng trăm tài khoản Hotmail mới reg. BẮT BUỘC phân vùng ứng viên (`cand_h` + `cand_g`), ưu tiên Hotmail trước.
  - *GPM Automation Trap - Login Modal & PID Mismatch*:
    1. **Early Break on Domain:** Never break the login loop merely because `page.url` contains `chatgpt.com` if login modals/dialogs are still visible. Only break when `__Secure-next-auth.session-token` is verified in `context.cookies()` or avatar/profile button is fully rendered.
    2. **GPM Profile ID Drift:** Hardcoded PIDs in scripts can drift if profiles are recreated. Always reconcile target accounts against `profile_data.db` (matching email and port) before calling `start_gpm(pid)`.
    3. **Playwright Mobile Auth Dialog Pointer Interception (`#mobile-auth-dialog`):**
       - *Symptom:* `Locator.click: Timeout 30000ms exceeded. <dialog id="mobile-auth-dialog"> intercepts pointer events` when attempting to click login button (`button:has-text("Đăng nhập")`).
       - *Root Cause:* ChatGPT's modern responsive layout automatically mounts `<dialog id="mobile-auth-dialog">` (bottom sheet modal) upon load. The standard "Đăng nhập" button sits in the background DOM, covered by the modal overlay, causing Playwright click actions to hang for 30s.
       - *Resolution:* Look for Google OAuth button (`button[data-provider="google"]`, `button:has-text("Continue with Google")`, `button:has-text("Tiếp tục với Google")`) INSIDE the dialog first. If present, click it directly with `force=True` and short timeout (5-7s). Only attempt background button if dialog is absent, wrapped in `try/except` with a short 5s timeout.
    4. **Anti-Deception & Real Execution Invariant (User Rule 15/10/2026):**
       - Coordinator/Worker must NEVER report "Đang cho rà soát / Đang xử lý" without an active background process (`terminal(background=True)` or `delegate_task`). Stating an action as in-progress without an active PID or transcript handle is a critical failure. Never attempt to rationalize away in-flight stall as "waiting for user" when a turn was left abandoned.

- **Reference Implementation (`sync_registered_chatgpt_web_connection` - Deterministic Matching & Fail-Closed)**:
  ```python
  # 1. Khởi tạo / cập nhật ở trạng thái is_active = 0
  cur.execute("""
      INSERT INTO provider_connections (id, provider, auth_type, name, email, api_key, is_active, test_status, ...)
      VALUES (?, 'chatgpt-web', 'apikey', ?, ?, ?, 0, 'unavailable', ...)
  """, (cid, name, email, token))

  # 2. Match chính xác host:port từ GPM Profile / SoT (CẤM ORDER BY RANDOM!)
  cur.execute("SELECT id FROM proxy_assignments WHERE scope='account' AND scope_id=?", (cid,))
  pa_row = cur.fetchone()
  if not pa_row:
      cur.execute(
          "SELECT id FROM proxy_registry WHERE host = ? AND port = ? AND (status IS NULL OR status = 'active') LIMIT 1",
          (profile_proxy_host, profile_proxy_port)
      )
      px_row = cur.fetchone()
      if px_row:
          cur.execute(
              "INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at) "
              "VALUES (?, 'account', ?, 0, datetime('now'), datetime('now'))",
              (px_row[0], cid)
          )
          # 3. Kích hoạt an toàn sau khi đã gán proxy thành công
          cur.execute("UPDATE provider_connections SET is_active = 1, test_status = 'active' WHERE id = ?", (cid,))
      else:
          logger.error(f"[{email}] FAIL-CLOSED: Không tìm thấy proxy {profile_proxy_host}:{profile_proxy_port} trong registry! Giữ is_active=0 chống rò rỉ IP.")
  else:
      # Đã có proxy assignment từ trước -> an toàn kích hoạt
      cur.execute("UPDATE provider_connections SET is_active = 1, test_status = 'active' WHERE id = ?", (cid,))
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

## Gemini Web 4 Argon Architecture & Direct HTTP StreamGenerate RPC vs Playwright Trap
- **The Playwright Dependency Trap in `gemini-web.ts`**:
  - OmniRoute's native `gemini-web.ts` executor relies on Playwright (`chromium.launch({ headless: true })`). On Windows host environments, Playwright expects revision binaries in `~/.cache/ms-playwright` or `AppData/Local/ms-playwright/chromium-XXXX/chrome-win/chrome.exe`. If the binary directory is named `chrome-win64` or Playwright browser is uninstalled, OmniRoute aborts all `gemini-web` requests with HTTP 503 (`Gemini Web requires the Playwright Chromium browser`).
  - When all accounts in a `gemini-web` Combo fail with 503, OmniRoute marks all 5 connections `exhausted_connection` and falls through to the emergency fallback / auto recovery router.
- **The Proxy Fast-Fail 2000ms Timeout Trap**:
  - When OmniRoute falls through to fallback providers (e.g. `openrouter`, `antigravity`), it tests upstream proxy connectivity via `isProxyReachable()` (`src/lib/proxyHealth.ts`).
  - The health check enforces a strict 2-second timeout: `const FAST_FAIL_TIMEOUT_MS = parseInt(process.env.PROXY_FAST_FAIL_TIMEOUT_MS ?? "2000", 10)`.
  - If a fallback proxy (e.g. `mirotik1.taadaa.click:10001`) has high initial TCP handshake latency (>2000ms), OmniRoute instantly throws `[Proxy Fast-Fail] Proxy unreachable: http://mirotik1.taadaa.click:10001`.
  - **Diagnostic Discipline**: Coordinator/Worker MUST NOT conclude the target account's 4G Mobi proxy is dead! Check the actual egress IP and port: the failure is in the secondary fallback chain, triggered because the primary combo targets failed to launch.
- **Direct HTTP StreamGenerate Protocol (Zero-Playwright, 2.5s Latency)**:
  - Google Gemini Web interface does not require browser automation for chat inference. It exposes an internal RPC endpoint:
    `POST https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate?bl={build_label}&rt=c`
  - Authentication requires 3 elements extracted from the Google AI Pro session:
    1. Cookies: `__Secure-1PSID`, `__Secure-1PSIDTS`, `__Secure-1PSIDCC`.
    2. Request Token: `SNlM0e` (extracted via regex `\"SNlM0e\":\"([^\"]+)\"` from initial GET `https://gemini.google.com/app`).
    3. Payload: Form-urlencoded `f.req` containing JSON message structure and `at={SNlM0e}`.
  - Direct HTTP RPC completes in **~2.59s** (vs 15-20s for Playwright) and consumes 0MB browser RAM.

---

## Gemini Web Multi-Account Rotation Pool & Sticky Cache-Optimized Strategy
- **Why Free Web Pools Still Require Sticky Prompt Cache (`strategy: cache-optimized`)**:
  - While web sessions do not incur API token billing, switching accounts across consecutive turns of a multi-turn worker task discards server-side KV cache.
  - For large multi-turn tasks (8+ turns with code/test logs), re-ingesting 30K+ tokens on a fresh account increases Time-To-First-Token (TTFT) by 3-5 seconds per turn and disrupts conversation continuity.
  - **Optimal Strategy**: Set Combo `strategy: "cache-optimized"` with `config: { "sticky": true }`.
  - OmniRoute hashes the session identifier / prompt prefix to pin all turns of a single worker task to the same Google AI Pro account (leveraging warm KV-cache), while distributing concurrent, independent tasks across the remaining pool accounts via Least-Used.

---

## GPM Google AI Pro Cookie Extraction via CDP (Headless O(1))
To extract clean Google session cookies from GPM profiles without manual browser copying:
1. Start GPM profile: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
2. Query `http://{remote_debugging_address}/json` to obtain `webSocketDebuggerUrl`.
3. Open WebSocket connection, send `{"id": 1, "method": "Storage.getCookies"}`.
4. Extract `__Secure-1PSID`, `__Secure-1PSIDTS`, `__Secure-1PSIDCC` for domain `.google.com`.
5. Stop GPM profile: `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}` and kill orphan `gpm_browser_chromium_core.exe` processes.
6. Register connection into OmniRoute (`POST http://127.0.0.1:20129/api/providers`) and bind to the account's dedicated 4G Mobi proxy port in `proxy_assignments`.

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

---

## PA1 Native HTTP StreamGenerate Implementation & Runtime Findings (October 2026)
- **Playwright Elimination in `gemini-web.ts`**:
  - The native executor was successfully refactored from Playwright Chromium automation to direct HTTP `StreamGenerate` (`+237 / -282` lines).
  - Uses `globalThis.fetch` to ensure OmniRoute's `runWithProxyContext()` injects the connection's dedicated 1:1 4G Mobi proxy into the request dispatcher.
  - Kept intact: prompt flattening (`buildGeminiPrompt`), tool emulation (`buildGeminiToolPrompt` / `buildGeminiToolResponse`), pseudo-SSE streaming, cookie rotation (`mergeRotatedGeminiCookies`), and explicit `501` error for unsupported image generation.
  - Passes core typecheck (`npm run typecheck:core`), and passes live canary probe on `:20129` with ~5-6s latency.
  - Legacy tests in `tests/unit/gemini-web.test.ts` that mock `playwright.chromium.launch` return 401 instead of 502/503 because the runtime no longer invokes Playwright.

- **Reasoning Effort Capability Matrix: Sol Web vs Gemini Argon**:
  - **Sol Web (`chatgpt-web` / `gpt-web-sol`)**: Fully supports `thinking_effort` parameter on the wire (`standard`, `extended`, `max`), selected via model slugs:
    - `gpt-5.6-sol-instant` (effort: null / instant ~2.5s)
    - `gpt-5.6-sol-medium` (effort: standard)
    - `gpt-5.6-sol-high` (effort: extended - expert analysis)
    - `gpt-5.6-sol-xhigh` (effort: max - deep reasoning)
  - **Gemini Argon Web (`gemini-web-argon-pool`)**: Does **NOT** support `reasoning_effort`.
    - OmniRoute's `checkGeminiWebUnsupportedControls()` guard rejects requests specifying non-minimal `reasoning_effort` with `400 invalid_request_error: unsupported_control_for_provider`.
    - Google's `BardFrontendService/StreamGenerate` RPC wire protocol has no parameter for setting thinking budget. Google controls reasoning server-side per model version.

- **Request Limit & Quota Profile for Gemini Web Pro Accounts**:
  - **Official Stance**: Google does **NOT** publish numerical request limits (RPM/RPD) for Gemini Advanced Web; terms cite only fair use and dynamic demand throttling.
  - **Empirical Limits**:
    - Burst: ~5–10 requests/min per account before temporary 429 throttling.
    - Rolling Window: ~50–100 Pro queries per 3–4 hour window per account.
    - Daily: ~150–300 Pro queries per account before falling back to Flash.
  - **5-Account Pool Capacity**:
    - With 5 accounts in `gemini-web-argon-pool` bound 1:1 to Mobi 4G proxies, total pool throughput is ~250–500 Pro prompts per 3–4h rolling window (~1,000–1,500/day).
    - Under `cache-optimized` (sticky) strategy, single worker tasks stay on one warm account to preserve prompt cache, while 429/failures trigger circuit-breaker failover to adjacent pool accounts.

- **Worker Dispatch & Naming Convention**:
  - **Short Alias**: `Argon` or `Argon Pool` (maps to `gemini-web-argon-pool` on `:20129`).
  - **System Role**: Dedicated heavy-lifting worker/subagent for code refactoring, algorithm debugging, and long-context processing (0đ quota).
  - **Coordinator Invariant**: Hermes Coordinator remains on official native API (`ag-gemini-pool-3`), as web reverse RPC lacks hardware function calling and is subject to web session safety filter drops.
