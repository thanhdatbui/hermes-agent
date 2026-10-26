# GPMLogin Local API & CDP Automation Pattern

Automating antidetect browser profiles in GPMLogin without `computer_use` (no mouse/keyboard hijacking, runs completely in the background).

## Architecture & Server Ports
* **GPMLogin v3 API:** Runs local server on port `19995` (`http://127.0.0.1:19995/api/v3`).
* **GPMLogin v1 API:** Runs local server on port `9495` (`http://127.0.0.1:9495/api/v1`).
* If port is occupied, GPM binds to a free port in `8000–10000` and writes the active port to `http.port` inside the app data directory.

## Core Endpoints (v3 API)
1. **List Profiles:** `GET /api/v3/profiles?page=1&per_page=100`
   * Returns list of profiles with `id`, `name`, `group_id`, `raw_proxy`, `created_at`.
2. **Create Profile:** `POST /api/v3/profiles/create`
   * Body: `{"profile_name": "ProfileName", "raw_proxy": "host:port:user:pass", "group_id": 1}`
   * **CRITICAL PITFALL:** Use `"profile_name"` (snake_case), NOT `"name"` or `"ProfileName"`. Passing `"name"` fails with `NOT NULL constraint failed: Profiles.Name`.
   * Returns: `data.id` (Profile UUID). Fingerprint parameters (Canvas, WebGL Renderer, MAC address, Audio, UA Chrome 142) are automatically randomized per profile.
3. **Start Profile (Launch Browser):** `GET /api/v3/profiles/start/{id}`
   * Returns: `data.remote_debugging_address` (e.g. `127.0.0.1:63909`), `data.process_id`, `data.profile_id`.
   * Connect with Playwright: `p.chromium.connect_over_cdp(f"http://{remote_debugging_address}")`.
4. **Stop Profile (Close Browser):** `GET /api/v3/profiles/stop/{id}`
   * Closes the profile browser and persists session/cookies.
5. **Delete Profile:** `GET /api/v3/profiles/delete/{id}?mode=1`
   * **CRITICAL PITFALL:** Must pass `?mode=1` (or `mode=2` to delete local data); omitting `mode` returns `{"success": false, "message": "INVALID_MODE"}`.

## Automation Flow (Python + Playwright via CDP)

```python
import requests
import time
from playwright.sync_api import sync_playwright

GPM_API_BASE = "http://127.0.0.1:19995/api/v3"

def create_gpm_profile(name: str, proxy: str = "") -> str:
    payload = {"profile_name": name, "raw_proxy": proxy}
    res = requests.post(f"{GPM_API_BASE}/profiles/create", json=payload).json()
    if not res.get("success"):
        raise RuntimeError(f"Failed to create profile: {res.get('message')}")
    return res["data"]["id"]

def start_gpm_profile(profile_id: str) -> str:
    res = requests.get(f"{GPM_API_BASE}/profiles/start/{profile_id}").json()
    if not res.get("success"):
        raise RuntimeError(f"Failed to start profile: {res.get('message')}")
    return res["data"]["remote_debugging_address"]

def stop_gpm_profile(profile_id: str):
    requests.get(f"{GPM_API_BASE}/profiles/stop/{profile_id}")

def delete_gpm_profile(profile_id: str):
    requests.get(f"{GPM_API_BASE}/profiles/delete/{profile_id}", params={"mode": 2})

def drive_profile_cdp(remote_debugging_address: str, task_fn):
    cdp_url = f"http://{remote_debugging_address}"
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        task_fn(page)
        browser.close()
```

## Profile Storage, Soft-Delete Mechanics & Recovery
* **Storage Location on Windows:** `C:\Users\<user>\AppData\Local\Programs\GPMLogin\profile\`
* **Port Discovery:**
  * `C:\Users\<user>\AppData\Local\Programs\GPMLogin\api_port.dat` (e.g. `19995` for API).
  * `C:\Users\<user>\AppData\Local\Programs\GPMLogin\local_port.dat` (e.g. `{"websocket_port": 6866, "http_port": 9996}`).
* **Database:** `profile\profile_data.db` (SQLite, table `Profiles`).
  * Columns: `Id`, `Name`, `ProfilePath`, `JsonData`, `GroupId`, `CreatedAt`, `LastRunAt`, `UpdatedAt`.
  * `JsonData` PascalCase Schema: The proxy string is saved under key `"Proxy"` (e.g. `host:port:user:pass` or `socks5://...`), and notes under `"Note"`.
  * Group IDs: `GroupId = 9` is group `cheat` (storing the active 15 Antigravity Pro profiles `01_Rua`..`15-...` mapped to `test.taadaa.click:5101..5117`).
* **Soft-Delete Behavior:** Deleting a profile via API (`GET /api/v3/profiles/delete/{id}?mode=1`) sets `GroupId = 0` in SQLite. The physical directory and session cookies on disk remain intact.
* **Emergency Recovery:**
  * To restore hidden profiles back to an active group (e.g. group 9):
    ```sql
    UPDATE Profiles SET GroupId = 9 WHERE Id = '<profile_uuid>';
    ```
* **Session Preservation Rule:** Never delete or recreate profiles that already have active logged-in Google sessions mapped to stable farm proxies. Re-logging from scratch carries high checkpoint/verification risks.

## Backup & Disaster Recovery Protocol (OneDrive)
* **Cloud Sync Caveat:** GPMLogin Cloud Sync requires an active S3 / Private Server plan (`S3Path` in `profile_data.db` is populated). If `S3Path` is NULL, all profile data lives 100% locally on disk.
* **Fast Compressed Backup Procedure:**
  1. Copy raw database `profile_data.db` (stores metadata of all 256+ profiles) to `D:\OneDrive\backup\GPM\profile_data.db`.
  2. Use GPMLogin's bundled 7-Zip (`C:\Users\<user>\AppData\Local\Programs\GPMLogin\7za.exe`) to archive active profile directories with fast compression and open-file sharing:
     ```bash
     7za.exe a -tzip -mx3 -ssw D:\OneDrive\backup\GPM\gpm_active_profiles_<timestamp>.zip @backup_list.txt
     ```
  3. OneDrive automatically syncs the resulting archive and database to Microsoft Cloud.

## Farm Proxy Mapping & 69 Profile Pool Architecture
* **Mapping Source of Truth:** `D:\OneDrive\TaadaaData\proxy_combined_pool.txt` (69 unique proxy endpoints).
* **Pool Composition:**
  * 32 MobiProxy 4G Kibe (`test.taadaa.click:5101..5138`) -> Profiles `01`..`32` (`01`..`15` are the existing active Gmail sessions).
  * 7 MikroTik Kibe (`mirotik1.taadaa.click:10001..10007`) -> Profiles `33`..`39`.
  * 28 MikroTik Admin (`mirotik1.taadaa.click:10008..10035`) -> Profiles `40`..`67`.
  * 2 auxiliary ports (`khoalee:16002`, `WAN2:18009`) -> Profiles `68`, `69`.
* **1 Profile : 1 Gmail Account Invariant:**
  * Never log multiple Gmail accounts into the same browser profile (avoids account linking checkpoints and Google Account Chooser popups during Antigravity OAuth).
  * Scaling to 5 accounts/IP: expand in discrete batches across days (Batch 1: Profiles 1–69, Batch 2: Profiles 70–138, etc.). Each proxy gets at most 1 login action per day.

## Canonical Repository
* `D:\Taadaa\GPM auto`: Main repository containing `GPMClient` (`src/gpm_client.py`), Playwright CDP runner (`src/cdp_auth.py`), and batch orchestrator (`scripts/run_auth_batch.py`).

## Antigravity / Google Pool Operational Rules
* **Mandatory Check-Live Preflight:** Always verify Gmail accounts are live (via `checkmail.live` CDP / automated check) BEFORE executing batch logins. Batch logging stale or unverified lists leads to high checkpoint failure rates (phone SMS / 2FA checkpoints) and wasted proxy slots.
* **No `computer_use` Needed:** Drive via Playwright CDP directly on DOM selectors (`input[type="email"]`, `#identifierNext`, `input[type="password"]`, `#passwordNext`, OAuth consent buttons).
* **Playwright Navigation Guard during Login:**
  * After submitting the password (`#passwordNext`), Google immediately navigates through several redirect URLs (`challenge/pwd` -> `gds.google.com` -> `myaccount.google.com`).
  * Calling `page.content()` during this transition raises `Page.content: Unable to retrieve content because the page is navigating and changing the content`.
  * **Fix:** Wait for `page.wait_for_load_state("domcontentloaded", timeout=15000)` and wrap all `page.content()` or `page.url` inspections in `try/except` with a small sleep.
* **Starter (Free) vs Pro Tier Quota:**
  * *Starter:* Reset cycle ~7 days (`6d 23h 59m`), quota ~3-5% of Pro.
  * *Pro:* Reset cycle ~5 hours (`4h 50m`).
* **Profile Cleanliness:** Do not reuse old airdrop profiles loaded with crypto wallet extensions (causes high RAM usage ~500MB/profile and popup interference). Create fresh clean profiles.
* **Proxy Allocation:** Maximum 5 accounts per static residential/datacenter proxy IP.
* **Timing & Rate Limits:** Add 5–15s delay between account logins/auth calls to avoid triggering Google OAuth rate limits.
* **Checkpoint Handling:** Detect `challenge` / Recovery Email prompts during sign-in; fill recovery email if requested; log failing profiles separately to avoid halting the batch run.

## Raw WebSocket CDP Connection Pitfall (Chromium 142+ & `websocket-client`)
- **Origin Handshake 403 Forbidden:**
  - *Symptom:* Direct connection `websocket.create_connection(ws_url)` fails with `WebSocketBadStatusException: Handshake status 403 Forbidden ... Rejected an incoming WebSocket connection from the http://127.0.0.1:<port> origin. Use the command line flag --remote-allow-origins=...`
  - *Root Cause:* Modern Chromium (v111+ / v142) enforces target origin checks on CDP DevTools WebSocket connections. By default, `websocket-client` sends an `Origin: http://127.0.0.1:<port>` header which Chromium rejects unless explicitly allowed.
  - *Fix:* Always pass `suppress_origin=True` when connecting:
    ```python
    import websocket
    ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
    ```

## GPM Zombie Chrome Process Cleanup & Port Scoping
- **API `stop` vs Residual Chromium Instances:**
  - Calling `GET /api/v3/profiles/stop/{id}` signals GPM to close the browser, but background extensions or stalled navigations (e.g. Cloudflare WAF challenges) can leave orphan `chrome.exe` processes holding the debugging port.
  - *Safe Cleanup Pattern:* Iterate running processes via `psutil`, filter for `--remote-debugging-port={port}`, and terminate child processes before killing the parent.
  - *Critical Exclusion:* Explicitly check command lines to NEVER kill the user's primary desktop Chrome (`"google\\chrome\\user data"`).

## Anti-Purge Safety Invariant on Cloudflare WAF / Proxy 403
- **Transient vs Fatal Account State:**
  - When inspecting web accounts (e.g. ChatGPT) through residential/mobile proxies, Cloudflare WAF may block requests with HTTP 403, empty DOM (`document.body.innerText == ''`), or WebSocket timeouts.
  - *Rule:* Only classify accounts as `DEAD_DEACTIVATED` upon finding unequivocal deactivation strings (e.g. `account_deactivated`, `đã bị xóa hoặc vô hiệu hóa`). Any network/WAF/proxy timeout MUST be classified as `UNKNOWN` to prevent destructive purges of live user accounts.

## ChatGPT Account Health Audit & Purge Pipeline (`login_audit_and_purge_deactivated.py`)
- **Script Location & Canonical Invocations:**
  - Tool script: `D:/Taadaa/tools/login_audit_and_purge_deactivated.py`.
  - Batch limit execution: `pythonw D:/Taadaa/tools/login_audit_and_purge_deactivated.py --limit 5` (safe 5-account chunk).
  - Canary mode: `--canary` (2 accounts); Single target: `--email <target_email>`.
- **Headless Execution & Console Window Guard (`CONSOLE_WINDOW_BLOCKED`):**
  - Running bare `python ...` in cron or guarded worker sessions triggers `[CONSOLE_WINDOW_BLOCKED]` to protect full-screen games/graphics apps from popping console windows (`conhost.exe`).
  - *Fix:* Always invoke via `pythonw` or use detached execution with `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`).
- **Execution Timing & Coordinator Foreground Timeout (`Command timed out after 60s`):**
  - Running `--limit 5` sequentially takes ~150–200s (each GPM profile start, navigation, OTP wait, and process cleanup takes 25–40s).
  - Calling in foreground terminal on Coordinator triggers `Command timed out after 60s`.
  - *Fix:* Always launch batch audits in the background:
    `terminal(command='python D:/Taadaa/tools/login_audit_and_purge_deactivated.py --limit 5', background=True, notify_on_complete=True)`
    followed by `process(action='wait', timeout=180, session_id=...)` to await completion cleanly.
- **Worker Delegation Contract Requirements:**
  - When delegating audit tasks to a Worker subagent, Coordinator dispatch rules enforce:
    1. Integer budget <= 8 calls: `BUDGET: <= 8 calls` (investigate tasks > 8 calls fail closed with `INVESTIGATE_BUDGET_EXCEEDED`).
    2. Mandatory Fail-Fast: Must include `FAIL_FAST: NẾU trong <= 3 iterations đầu nhận thấy GPM API (19995) không truy cập được hoặc lỗi môi trường thì PHẢI DỪNG NGAY (ABORT)...`.
- **Artifacts & Lifecycle State Paths:**
  - State file: `D:/Taadaa/runtime/chatgpt_account_lifecycle.json` (maps email to `LIVE`, `DEAD_DEACTIVATED`, or `UNKNOWN`).
  - Audit trail (NDJSON): `D:/Taadaa/logs/chatgpt_audit_trail.jsonl`.
  - Batch report: `D:/Taadaa/reports/chatgpt_lifecycle_report.json`.
  - Visual proof: `D:/Taadaa/runtime/artifacts/deactivated_<safe_email>.png`.
- **OmniRoute / 9Router Re-OAuth Token Sync:**
  - Live session detection (`New chat`, `Cuộc trò chuyện mới`) extracts `__Secure-next-auth.session-token` cookie via CDP `Network.getCookies` and synchronizes to OmniRoute (`127.0.0.1:20129`) and Router (`127.0.0.1:20128`).
  - Dead accounts trigger automatic removal from OmniRoute SQLite DB (`storage.sqlite`).

