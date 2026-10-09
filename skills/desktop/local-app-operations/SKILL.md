---
name: local-app-operations
description: "Safely update and operate locally hosted web applications through their installed/runtime surface, keeping application management separate from source-repository maintenance."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [local-app, web-dashboard, app-update, browser-ui, proxy-import, credential-safety]
    category: desktop
---

# Local application operations

Use this skill when the user asks to update, configure, log into, or import data into a locally running application with a browser dashboard (for example, a gateway, proxy manager, or self-hosted admin UI).

## Core rule: app surface first, repository second

1. Interpret “update the app” as updating the installed/running application instance, not automatically updating its source repository.
2. Discover the runtime surface first: URL/port, process owner, installed package/shortcut, in-app version, and available updater or admin controls.
3. Do not enter a source repository, run `git fetch`, `rebase`, `reset --hard`, `stash`, or overwrite local code unless the user explicitly asks to update the source checkout or the application is demonstrably installed from that checkout and no safer app updater exists.
4. Never involve an unrelated repository merely because it is present on the machine. State the exact target path and port before acting.
5. Do not stop a process as a default prerequisite. Update through the app's own updater or package mechanism first. Restart only when required by the update and only after checking the process/port and scope.
6. If a source-based update is truly required, preserve local work visibly (named backup/stash/branch), report the exact conflict risk, and verify the application only after the update/build succeeds. Never silently discard local work.

## Operational sequence

1. **Scope lock:** write down target app, URL/port, allowed side effects, and explicit non-goals. For OmniRoute-like setups, keep its port separate from a neighboring gateway.
2. **Inspect, do not mutate:** check the app page/version, runtime process, endpoint health, and available UI controls. Use browser UI for settings and imports; use terminal only for read-only discovery unless the user explicitly authorized a runtime update.
3. **Credentials:** never echo, save, export, or repeat passwords, API keys, OAuth tokens, or workbook credentials. If the user explicitly supplies a credential for a local login, type it only into the intended field and do not include it in reports or logs. Prefer disabling the dashboard password through the app's Security settings when the user explicitly requests it; otherwise use the browser's session/password manager rather than source edits or plaintext automation.
4. **Configuration:** change settings through the application's own UI/API. After each state-changing click, refresh the accessibility snapshot and verify the resulting state.
5. **Configuration:** change settings through the application's own UI/API. After each state-changing click, refresh the accessibility snapshot and verify the resulting state.
6. **Catalog boundary:** distinguish the application's upstream `/v1/models` catalog from the client/model-picker catalog. Hiding provider rows in the app may not reduce a client's model count if the client probes `/v1/models` directly. Before claiming cleanup, inspect the actual picker data path and configure a supported client-side allowlist/static model set with discovery disabled when the goal is a curated picker. Verify both layers separately: the upstream catalog may remain large by design, while the picker must contain only the requested models.
7. **Verification:** verify the in-app version, relevant setting, imported item count/status, endpoint health, and that unrelated ports/processes remain unchanged. Report success only from fresh tool output. For model catalogs, perform a fresh picker-level count/list check and one minimal generation canary per retained model; do not treat `/v1/models` count alone as proof that the picker is cleaned.
8. **Account-pool/concurrency boundary:** when investigating a multi-account model proxy, inspect the actual route path before changing settings. A direct model request selects an account before the ordinary per-account semaphore; `maxConcurrent=1` then serializes that selected account and does not, by itself, re-run selection or spill a queued direct request to another account. A combo can implement a distinct pre-dispatch capacity spill path for concrete targets with different pinned `connectionId` values, but do not infer its exact helper or behavior from a version note: inspect the live source/runtime and verify the current implementation. The safe invariant is atomic, non-queueing admission for the priority path; an observation-only `isAccountSemaphoreFull(...)` check races under bursts and can still queue all work behind the first account. Any pre-acquired slot must have an explicit ownership handoff and must be released on every normal early return, thrown error, non-stream completion, and stream finalizer; a passing unit test for the admission primitive alone is not sufficient. Verify strategy, target order, pinned connection IDs, and whether the request is actually called by `combo/<name>`; a direct `provider/model` call will not use this combo fallback. Distinguish fill-first/priority, round-robin, quota/error failover, combo capacity skip, account semaphore, and queue timeout. `queueDepth=0` and `failoverBeforeRetry` are not substitutes for the combo capacity gate. Reproduce with at least two real connections and sanitized selected-connection/decision-trace evidence before claiming busy-aware behavior. Keep account rotation quota/cooldown-driven when the operator wants to avoid request-by-request round-robin.

**Burst-capacity correction:** never treat “five sessions failed” as proof that `maxConcurrent=2` is unsafe, and never treat one successful five/six-request run as proof that `maxConcurrent=2` is universally safe. First determine whether requests were concentrated on one account, rejected by process-wide heavy admission before routing, or rejected upstream after account selection. In the current OmniRoute implementation, the chat route calls the process-wide admission layer before combo/account dispatch; `CHAT_MAX_HEAVY_IN_FLIGHT` and structural `chat_admission_busy` therefore cap heavy requests independently of the number of provider accounts. A combo can only distribute requests that survive that gate. A light combo canary is insufficient: always run a realistic heavy-payload burst through the exact combo name used by the client and record pass/fail counts, latency, sanitized selected-connection evidence, and rejection reasons. Treat the operator’s workload as tool-heavy: one conversational session can issue many model requests through tool rounds, retries, compression, or handoffs, so “number of sessions” is not the same as “number of requests.”

**Pool-operation correction:** configure the account pool once; do not require the operator to assign an account or create a separate request for every session. A client-facing combo alias should contain the same production model on distinct pinned connection targets, and Hermes should call the alias. The pool/router must handle each request, including requests emitted by tool-heavy sessions. Report the distinction explicitly: one user turn may be one request, but a session with tools can generate many requests. Do not claim that request N will reach account C unless C is a real active target and the request passed global admission and reached combo dispatch. Adding a new provider connection does not automatically add it to a combo with pinned `connectionId` steps: update the existing combo target list (or deliberately create a new pool alias), then verify the combo has the expected distinct active targets. Do not tell the operator to manually map sessions to accounts.

**Concurrency-tuning correction:** do not reset every account to `maxConcurrent=1` or `2` solely out of theoretical caution. In heavy workloads where sessions spam multiple tools, artificially low per-account caps cause premature saturation and trigger `503 ALL_TARGETS_SKIPPED`. Follow the operator's sizing principle: set to the highest proven capacity ceiling (e.g. `maxConcurrent=3` per account with matching global `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT=9` for a 3-account pool), and only step down if genuine upstream 429/quota exhaustion occurs.

**Priority account-safety correction:** `priority` alone does not prove the declared pinned-account order is preserved. Two continuity layers can still promote a later account before pool-1: (1) first-message **session stickiness** and (2) rendezvous **prompt-cache affinity** within a single-model account pool. For a safety-first pool that must use `pool-1 → pool-2 → …` and spill only on real capacity/quota/cooldown/error gates, disable both per-combo flags:

```json
{
  "disableSessionStickiness": true,
  "disablePromptCacheAffinity": true
}
```

`disablePromptCacheAffinity` must be supported by the installed source schema/router before setting it through the management API. It prevents account-order re-ranking only; it does **not** delete or strip client/upstream `cachedContent`. After the source update/build/restart, configure through the official combo API, read back the exact flags, and verify one fresh request’s `combo_step_id` ends with its executing `connection_id`. If a later pool is selected after this change, inspect per-connection Gemini quota snapshots and safety-gate logs before treating it as a routing bug: a lower pool with healthy quota is the correct safe spill when earlier pools are exhausted or below quota cutoff. See `references/priority-account-safety.md`.

**Crash vs Throttling Taxonomy:**
- `WinError 10054 / APIConnectionError`: Local socket severed mid-stream because the proxy process was killed/restarted while sessions were active. Not an upstream failure.
- `503 ALL_TARGETS_SKIPPED`: All combo targets reached their configured `maxConcurrent` ceiling simultaneously. Solution: raise per-account `maxConcurrent` and global admission.
- `Priority vs Round-Robin`: Priority routing concentrates traffic on the primary account to exploit prompt caching, spilling over to secondary targets only on concurrency saturation or error. Round-robin rotates blindly on every request, defeating prefix caching.

For a pool of currently usable accounts, configure the pool once rather than assigning accounts to sessions. A combo with the same model pinned to distinct connection IDs can provide native capacity-aware target skipping; for example, three active connections with `maxConcurrent=2` expose up to six per-connection target slots, but only if the process-wide admission ceiling and upstream capacity allow six heavy requests. If the global gate is lower, raising per-account caps cannot help. If all pool targets are full, the combo must either wait through an explicitly configured outer queue/retry policy or return a retryable error; do not claim that the next request will “find account C” unless the pool has a real C target and the request reached combo dispatch.

When a live pool has fewer connections than the operator expects, report the exact `/api/providers` count and active/quota state. Do not infer that “quota 3” means four or five Omni connections; quota availability, stored connection rows, eligible connections, and process admission are separate measurements. See `references/account-pool-concurrency.md`.

**Restart/port pitfall:** before restarting a source-launched local app, inspect both the live PID command line and the repository launcher’s port resolver plus `.env`. A neighboring service may own the default port (for example, a 9Router on `20128`) while the target app normally listens on another port (for example, `20129`). Stop only the target PID, then relaunch with explicit target port variables when the launcher otherwise inherits the conflicting default. Verify the target listener and health endpoint before running canaries. A failed relaunch due to `EADDRINUSE` is not evidence that the app or configuration is broken; correct the port scope and retry.

**Watchdog RAM Staleness Pitfall:** modifying a watchdog script (`omniroute_watchdog.ps1`) on disk does NOT take effect in memory if an existing PowerShell watchdog process is running in an infinite loop. Always inspect running supervisor PIDs (`Get-CimInstance Win32_Process`), gracefully kill the old watchdog process, and launch a fresh headless instance (`-WindowStyle Hidden`) so the newly patched supervisor logic is loaded into RAM.

**Proxy Fail-Closed vs Direct Fallback:** in multi-account proxy aggregators/pools, never permit `PROXY_FAIL_OPEN=true` or direct-IP fallback. When a proxy fails or times out, the router must fail-closed immediately to protect account fleets from IP leaks and mass Sentinel/Turnstile blocks.

**Burst-test interpretation:** when a real 5–6-session burst fails, identify the boundary before changing caps. A failure can mean (a) all requests selected one account under direct fill-first routing, (b) the process-wide heavy/structural admission gate rejected requests before account selection, (c) combo capacity skipped all targets, or (d) upstream admission rejected requests after selection. Do not use the count of failed sessions alone to declare `maxConcurrent=2` unsafe. Test both a lightweight burst and a production-shaped heavy burst through the exact combo alias, then inspect sanitized selected-connection logs and rejection reasons. See `references/omniroute-account-pool-burst.md`.
9. **Communication:** use the user's requested language and format. For this user, report in concise Vietnamese with three labels when useful: `Mục tiêu`, `Kết quả`, `Blocker`. Answer the exact requested check first; do not substitute a screenshot description or a generic canary result for the requested root-cause/configuration verification. Do not narrate internal policy or tool mechanics unless they directly block the task.

## Shared OmniRoute: catalog curation and single-account admission control

When multiple Hermes machines share one OmniRoute/OpenAI-compatible proxy, separate two problems:

1. **Picker catalog:** a client may probe `/v1/models` and show hundreds of upstream IDs even when OmniRoute's provider dashboard hides models. To curate the client picker, configure the client/provider with an explicit `models:` allowlist and `discover_models: false`. Verify the picker payload separately from the proxy's upstream catalog count.
2. **Runtime admission:** `HTTP 503 chat_admission_busy` can coexist with successful short canaries. It means the proxy could not admit a request at that moment, commonly because several large sessions share one upstream OAuth account. A successful `/v1/models` call or one short generation is not proof that concurrent large requests are healthy.

For a shared OAuth connection with only one active account:

1. Reproduce with two realistic concurrent requests, not only a one-message probe. Record status, latency, message/tool scale, and response code.
2. Read `/api/providers` and `/api/resilience` before changing anything. Confirm the connection is active/healthy, note whether `maxConcurrent` is unset, and record global queue values.
3. Set the affected connection's `maxConcurrent` to `1` through the official `PUT /api/providers/<connection-id>` endpoint. This serializes requests for that account without throttling unrelated providers. Never edit the runtime SQLite database for this.
4. If logs show local queue expiration (for example a `504` after a short `maxWaitMs`), raise only `requestQueue.maxWaitMs` through the official `PATCH /api/resilience` endpoint, preserving unrelated fields. A longer queue wait prevents false queue failures but does not create upstream capacity.
5. Re-read both endpoints, then run two concurrent canaries. Acceptance is both requests returning `2xx`; the second may take longer because it is correctly queued. Report that latency trade-off.
6. Treat `403 with x-goog-user-project` followed by retry without that header and intermittent `TruncatedStreamError` as secondary transport/provider behavior until a fresh probe proves persistent authentication failure. Do not rotate or delete OAuth credentials based on those messages alone.

**Communication rule:** when the user asks to investigate a live model failure, inspect the live endpoint and logs first. State the exact failing component; do not merely re-describe an attached screenshot or treat an earlier short canary as current proof.

See `references/remote-omni-admission.md` for the focused evidence sequence, error taxonomy, official endpoint payloads, and verification recipe. See `references/omniroute-pool-burst-notes.md` for the consolidated tool-heavy pool-routing and burst-capacity lessons.

## Common pitfalls

- **Lưu cấu hình & SOP vào chính repository dự án (Repo-First Documentation Invariant)**:
  - Khi user yêu cầu "chốt lưu cấu hình / lưu quy trình update": **BẮT BUỘC lưu thành file tài liệu trực tiếp trong repository của ứng dụng** (ví dụ `docs/deployment/UPDATE_RUNBOOK.md`, `AGENTS.md`) và git commit/push lên remote branch của repo.
  - Tuyệt đối không chỉ lưu vào memory nội bộ của Agent rồi bỏ qua việc ghi vào repo mã nguồn. Người vận hành và các công cụ/AI khác cần tài liệu nằm trong mã nguồn để tham chiếu độc lập.
- **OmniRoute Production Update & Build Protocol (`build:backend` Invariant)**:
  - Trên Windows host với Next.js 16 đồ sộ (>800 trang UI dashboard): **TUYỆT ĐỐI CẤM** chạy full `npm run build` (ngốn >8GB RAM, CPU 100%, gây OOM / timeout kéo sập server) và **TUYỆT ĐỐI CẤM** chạy `run-next.mjs dev` dưới watchdog (gây nghẽn event loop, lock file conflict và crash-loop).
  - **Lựa chọn duy nhất chuẩn xác:** Chạy `npm run build:backend` (chỉ mất 2–3 phút, stub toàn bộ UI dashboard, compile API routes hot-path sang production bundle `.build/next/server/`), sau đó dừng tiến trình Node cũ để watchdog tự nạp bundle mới.
- **Windows SQLite Database Lock on In-Place Restoration**: On Windows, SQLite databases (`*.sqlite`, `*.db`) and accompanying `-wal` / `-shm` files are locked with exclusive sharing by active Node.js / Python daemon processes. Running `cp` or `Copy-Item` to overwrite a database while the server is active fails immediately with `Permission denied` / sharing violation.
  - *Correct sequence*: Stop/kill the owning process *before* restoring the SQLite file.
  - *WAL cleanup*: Always remove stale `<dbname>.sqlite-wal` and `<dbname>.sqlite-shm` files when restoring a `.bak` snapshot; leaving orphaned WAL files causes SQLite to attempt transaction recovery against the restored file, potentially resurrecting mutated state or causing corruption.
  - *Watchdog coordination*: If an aggressive watchdog supervisor (e.g. `omniroute_watchdog.ps1`) is running, be aware of its failure threshold or create the designated stop flag (e.g. `watchdog.stop`) so the supervisor does not race to restart the process and re-lock the database mid-copy.
- “Update OmniRoute” does not mean “update the TikTok repository.”
- `taskkill` is not an update step; do not add it just because a port exists.
- A successful source build is not proof that the running app was updated; check the runtime version and HTTP endpoint.
- A disabled dashboard password is convenient but removes a local management boundary; mention that trade-off briefly, without blocking an explicitly requested local-only change.
- A proxy workbook may look like ordinary `host:port:user:pass` data while containing secrets. Never print sample rows or copy credentials into chat.
- Browser element references change after navigation; always take a fresh snapshot before clicking a newly rendered control.

## Missing-config recovery for installed local apps

When an installed app is launched through a shortcut or wrapper and fails because its config path is missing:

1. Inspect the shortcut or launcher target, arguments, and working directory first; do not assume the app's default config location.
2. Search the target runtime directory and known backup/sync locations for an existing config. Never overwrite a candidate before making a timestamped backup.
3. If no prior config exists, reconstruct only from the exact installed version's shipped example/template, preserving the app's existing data/auth directory where the format supports it. Do not invent or copy credentials into the new file.
4. Align only the runtime values required by the launcher contract, especially the configured port; remove placeholder/example secrets rather than enabling them.
5. Restart only the target app after the config change and verify the process command line, listening port, root/dashboard endpoint, and logs.
6. Distinguish `service restored` from `accounts/config restored`: a template-based recovery may bring the server up while leaving zero auth/provider entries. Report that as a separate blocker instead of claiming full recovery.

A session-specific recovery transcript and validation pattern is recorded in `references/missing-config-recovery.md`.

For the reusable distinction between an upstream model catalog and a client-side curated picker, see `references/catalog-picker-boundary.md`.

## Runtime supervision and crash recovery

For source-launched Windows apps that must recover after a child process exits, follow `references/runtime-supervisor-and-crash-recovery.md`. Verify the actual listener/PID and health endpoint; do not treat a surviving npm/cmd window as proof of liveness. Prefer production mode, use a mutex-guarded watchdog, and use the user's Startup folder only when Task Scheduler is unavailable or denied. Distinguish verified child-process exit from an unobserved exact exception.

### Windows Persistent Background Autostart (Startup VBS + pythonw)
When an operator requests a local dashboard or utility script to auto-start silently on Windows boot/restart without cmd popup windows:
1. Do not rely on `schtasks /Create /RL HIGHEST` if running under un-elevated non-admin context (`ERROR: Access is denied`).
2. Write a minimal `.vbs` wrapper into user's Startup directory (`C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\<name>.vbs`):
   ```vbs
   Set WshShell = CreateObject("WScript.Shell")
   WshShell.Run "pythonw.exe <path/to/script.py> [args]", 0, False
   ```
3. Use explicit `pythonw.exe` from active venv instead of `python.exe` so Windows suppresses the console window completely (zero cmd flash/tray distraction).
4. **`pythonw.exe` sys.stdout / sys.stderr is None pitfall**:
   - Under Windows `pythonw.exe`, standard streams are not attached, so `sys.stdout` and `sys.stderr` are `None` (not open file streams).
   - Any unhandled `print(...)` or `sys.stderr.write(...)` (such as `BaseHTTPRequestHandler.log_message`) immediately throws `AttributeError: 'NoneType' object has no attribute 'write'`, crashing the daemon on startup or on the first incoming HTTP request.
   - Always guard both streams at module import time and in custom handlers:
     ```python
     import sys, os
     if sys.stdout is None:
         sys.stdout = open(os.devnull, "w", encoding="utf-8")
     if sys.stderr is None:
         sys.stderr = open(os.devnull, "w", encoding="utf-8")
     ```
     And defensively guard `log_message`:
     ```python
     def log_message(self, format, *args):
         if sys.stderr is not None:
             try:
                 ts = time.strftime("%H:%M:%S")
                 sys.stderr.write(f"[{ts}] {args[0]}\n")
             except Exception:
                 pass
     ```
5. Combine with Tailscale IP/MagicDNS so remote access survives host reboots automatically without manual command intervention.
6. **Self-Healing Watchdog Companion Pattern for Long-Running Local Daemons (ERR_EMPTY_RESPONSE / Socket Saturation)**:
   - On Windows, long-running single-file HTTP servers (`http.server.ThreadingHTTPServer`) serving active fleets often encounter silent socket descriptor exhaustion or client connection buildup after 24–72 hours of continuous uptime, resulting in browser `ERR_EMPTY_RESPONSE` or socket dropouts.
   - To make services truly immortal and zero-maintenance, pair the primary daemon with a companion watchdog script (`<service>_watchdog.ps1`) invoked via a hidden VBS wrapper (`start_<service>_watchdog_hidden.vbs`) also placed in Windows Startup:
     ```powershell
     # Probe health endpoint every 60s
     try {
         $req = [System.Net.WebRequest]::Create("http://127.0.0.1:<PORT>/api/health")
         $req.Timeout = 8000
         $resp = $req.GetResponse()
         if ($resp.StatusCode -eq 200) { $isHealthy = $true }
         $resp.Close()
     } catch { $isHealthy = $false }

     if (-not $isHealthy) {
         # Auto-kill stuck listener PID and relaunch via hidden VBS
         Get-NetTCPConnection -LocalPort <PORT> -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
             Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
         }
         Start-Sleep -Seconds 2
         Start-Process "wscript.exe" -ArgumentList "`"<PATH_TO_VBS_LAUNCHER>`""
     }
     ```
   - This guarantees automatic failover and recovery within 60–120s without operator intervention or manual terminal debugging.
- **Table column shift on in-memory server restart pitfall**: When altering table columns (`<th>` in `<thead>` and `<td>` in `renderTable` / `<tbody>`), if a background server process is still serving the old template or cached in-memory response, adding/reordering columns will shift cell values across adjacent columns (e.g. Likes displaying under Following, Videos displaying under Likes). Always check `Get-NetTCPConnection` or `Get-Process`, kill the pre-existing worker process PID explicitly, start the new instance, and verify rendered cell output via `curl` / `urllib` before handing off to the operator.
- **Python ThreadingHTTPServer Long-Running Socket Leak & `ERR_EMPTY_RESPONSE`**:
  - When Python `ThreadingHTTPServer` or `BaseHTTPRequestHandler` runs for days in a background terminal/console whose parent pipe or shell session has closed, accumulated client socket descriptors and thread state can become stuck (`CLOSE_WAIT` / `ESTABLISHED`).
  - *Symptom*: Chrome/browser connects to the port, but immediately receives `ERR_EMPTY_RESPONSE` ("kibe không gửi bất kỳ dữ liệu nào" / curl: `(52) Empty reply from server`).
  - *Diagnosis*: Check process start time and thread count (`(Get-Process -Id <PID>).Threads.Count`). If thread count has accumulated into dozens while curl returns exit code 52 with zero bytes, the daemon socket loop is jammed.
  - *Resolution*: Kill the stuck PID (`Stop-Process -Id <PID> -Force`), launch via the dedicated detached VBS launcher (`pythonw.exe`), verify HTTP 200 with `urllib`, and ensure the launcher is installed in Windows Startup (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`) for persistent survival across reboots.
- **Full-Page Browser Vision Screenshot Decompression DOS Warning & Pillow Crop**:
  - Full-page browser snapshots on large tables (e.g. 1.000+ rows) can generate massive images (>80-90 Megapixels).
  - Attempting to convert or save such raw PNGs directly with PIL can trigger `DecompressionBombWarning: Image size exceeds limit...` or `OSError: broken data stream when writing image file` (exceeding maximum JPEG dimensions of 65,500 pixels).
  - *Solution*: Set `Image.MAX_IMAGE_PIXELS = None` and crop to the visible header/KPI area (`top_part = im.crop((0, 0, im.width, min(im.height, 1600)))`) before converting to JPEG for compact `MEDIA:` delivery.
- **On-Demand Dashboard vs Push Notification Fatigue**:
  When monitoring farm or fleet metrics (e.g. TikTok Farm account status, device states), operators prefer viewing live data on-demand via the web dashboard over daily report spam.
  - Cronjobs scanning fleet metrics should use `deliver: "local"` to silently update the local SQLite database in the background without blasting daily messages to Telegram.
  - Scraper/tracker scripts must not auto-generate Excel reports (`.xlsx`) on every periodic tick; gate file generation strictly behind an explicit `--export <path>` CLI argument.
  - Expose newly requested dimensions (such as `Ngày Tạo` / Creation Date from Snowflake UID) directly on the web table as sortable columns (`onclick="sortTable('created_at')"`) and searchable strings (`item.created_at.includes(query)`) so operators can inspect, sort, and filter on-demand without manual exports.



## Mobile and remote access to local web dashboards

When operators access local tools/dashboards (e.g. MikroTik Web Manager, OmniRoute, proxy tools) from mobile devices (especially iOS / Safari):

1. **iOS Safari single-label hostname failure:**
   - Typing bare `hostname:port` (e.g. `kibe:2310`) in Safari often fails because Safari interprets it as a search query or attempts an automatic HTTPS upgrade on an HTTP-only local server.
   - iOS does not support NetBIOS/WINS name resolution on local Wi-Fi.
   - Tailscale MagicDNS single-label queries can be dropped or intercepted by iCloud Private Relay or cellular DNS.
2. **Access fallback order:**
   - LAN Wi-Fi: prefer explicit HTTP with local LAN IP: `http://<lan_ip>:<port>` (e.g. `http://192.168.110.123:2310`).
   - Tailscale VPN: prefer explicit HTTP with Tailscale IP: `http://<tailscale_ip>:<port>` (e.g. `http://100.88.164.111:2310`) or MagicDNS FQDN: `http://<host>.<tailnet>.ts.net:<port>`.
   - Never omit the `http://` scheme on mobile browsers.

## Embedded single-file dashboard coupling (frontend / backend)

When inspecting or maintaining single-file Python HTTP dashboards (e.g. `server.py` serving inline `HTML_PAGE`):
1. **Python f-string escaping in inline templates**:
   - When HTML/CSS/JS is embedded inside Python f-strings (`f"""..."""`), all literal CSS blocks, JS functions/objects, and regexes containing braces must be escaped with double curly braces (`{{` and `}}`). Dynamic Python values use `{variable}`.
   - For JS template literals inside f-strings, write `${{item.property}}`. Single `${item.property}` will cause Python to attempt interpolating `item.property` as a Python expression, raising `NameError` or `KeyError`.
   - Always run `python -m py_compile <path/to/server.py>` immediately after modifying inline templates to catch bracket escaping issues before restarting the service.
2. **SQL Window Function & CTE schema parity for snapshot deltas**:
   - When calculating snapshot-to-snapshot deltas using SQLite window functions (`ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC)`), any newly added metric delta (e.g. `delta_following`) requires updating three coupled locations in lockstep:
     1. SQL `SELECT`: Include `r2.<metric> AS prev_<metric>` in the join against `Ranked r2 (rn = 2)`.
     2. Cursor row unpacking: Update the tuple unpack signature `(..., prev_f, prev_following, prev_h, ...)` to avoid `ValueError: too many/not enough values to unpack` or silent column misalignment.
     3. Default empty state & item dict: Update the default fallback `summary` dict and the per-item dictionary with default `0` values so clients consuming `/api/data` never hit `KeyError`.
   - **Unbounded Historical Window vs Midnight Rollover / Partial Scan Trap**:
     - *Anti-Pattern 1 (Resurrection of Retired Accounts)*: Querying `WHERE rn = 1` across an unpartitioned historical `snapshots` table without scoping retrieves the last known record for *every account ever tracked*, resurrecting deleted or retired accounts from prior runs (e.g. 27 old accounts scanned days ago inflating count from 992 to 1019).
     - *Anti-Pattern 2 (The Midnight Partial Scan Collapse)*: Attempting to fix Anti-Pattern 1 by filtering `WHERE substr(timestamp, 1, 10) = (SELECT substr(MAX(timestamp), 1, 10) FROM snapshots)` is FATALLY FLAWED. When an auxiliary watchdog (e.g. `feed_session_watchdog`, avatar uploader, or single-machine canary) scans a small batch (e.g. 54 accounts) past midnight (00:10 AM), `max_dt` instantly shifts to the new calendar day. The entire dashboard collapses from 1,042 accounts down to 54, hiding 988 accounts whose latest scan was on the previous day until the morning 07:00 batch runs.
     - *Correct Canonical Pattern (Anchor to Active Fleet Roster)*: Never filter by single calendar date `max_dt`. Always anchor `WHERE rn = 1` to the active fleet roster table (e.g. `farm_account_info`), taking the latest snapshot per active account regardless of calendar date boundary:
       ```sql
       WITH Ranked AS (
           SELECT *, ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
           FROM snapshots
           WHERE username IN (SELECT username FROM farm_account_info)
       )
       SELECT r1.*, f.may, f.host_id, f.tik
       FROM Ranked r1
       LEFT JOIN Ranked r2 ON r1.username = r2.username AND r2.rn = 2
       LEFT JOIN farm_account_info f ON r1.username = f.username
       WHERE r1.rn = 1
       ```
       This simultaneously eliminates retired accounts (they are not in `farm_account_info`) AND keeps all active accounts visible 24/7 across midnight partial runs.
   - **Batch Timestamp Observability vs Misleading "Live Data" Labels**:
     - On dashboards fed by periodic batch crons (e.g. 07:00 daily scan), hardcoding `<span id="farm-meta">Live Data</span>` with a pulsing green dot causes alert fatigue and confusion: operators opening the site hours later see static numbers and assume the poller or service crashed.
     - Include `last_scan = items[0]["timestamp"] if items else ""` in the `summary` payload.
     - Bind header telemetry to the latest snapshot timestamp: `🕒 Quét: {_fmt_scan(summary.get('last_scan', ''))}` both in the initial server HTML template and in the client-side `/api/data` auto-refresh JS loop (`if (s.last_scan) document.getElementById('farm-meta').textContent = '🕒 Quét: ' + formatScanTs(s.last_scan);`). Keep date formatting compact (`DD/MM HH:MM`).
3. **HTML Class & CSS Selector Drift ("Font/Style Breakage"):**
   - When users report "lỗi font" (font bug/ugliness) on KPI/card elements in custom web dashboards, check for HTML class mismatch before assuming missing system fonts or UTF-8 charset bugs.
   - If an element uses `<div class="card card-trend">` while the CSS stylesheet only defines `.kpi-card`, `.kpi-title`, `.kpi-value`, the element falls back to unstyled browser defaults (Times New Roman / tiny serif text), which users perceive as "lỗi font".
   - Keep ID bindings strictly aligned between backend HTML templates and dynamic JavaScript pollers/refresh intervals (`document.getElementById(...)`). Mismatched IDs (e.g. HTML `card-trend` vs JS `kpi-trend`) cause stale UI or broken live updates.
2. **Grid Layout Parity:** When adding cards to a KPI grid (e.g. from 4 to 6 cards), update CSS media queries (e.g. `repeat(4, 1fr)` -> `repeat(3, 1fr)` / `repeat(6, 1fr)`) so cards wrap or distribute evenly across desktop displays.
3. **Tab switching & Leaderboard Views completeness:** 
   - UI tab buttons (`switchTab('tab_name')` or view-mode tabs) must have their corresponding JavaScript handler implemented in `<script>` to toggle active classes, table layouts, and `.tab-content` styles. Missing JS causes silent `ReferenceError` on mobile/desktop, making tabs appear broken/unresponsive.
   - **Leaderboard / Ranking View Pattern for Farm Monitoring:**
     When building metric-delta leaderboards (e.g. Top Followers Gained/Lost, Top Likes, Top Following):
     - Always include rank indicators (🥇 #1, 🥈 #2, 🥉 #3, #N) and highlighted delta badges (`+X` green, `-X` red, `0` gray).
     - Provide sub-filters for delta direction (`All`, `Only Positive (+)`, `Only Negative (-)`) so users can isolate drops vs surges instantly. Essential for risk watchdogging: pure sorting by descending delta pushes account losses (drops/unfollows/shadowban signals) to the very bottom where operators miss them.
     - **Leaderboard Semantics & UX Labeling Trap (Cumulative Volume vs Delta Growth & Inbound vs Outbound):**
       * **Cumulative Volume vs Delta Growth:** When operators click a bare `📈 BXH Follower` tab, they intuitively expect the leaderboard to rank by total cumulative audience (`follower` DESC, where e.g. an account with 244 followers is 🥇 #1). If the view silently sorts by snapshot delta (`delta_follower` DESC), operators perceive it as broken when the largest account appears at #4 behind smaller accounts that gained +5 today. Explicitly label delta-based leaderboards as `📈 Tăng Trưởng Follower` / `📈 Tăng Follower (+)` or reserve `BXH Follower` strictly for cumulative total ranking.
       * **Inbound (Followers) vs Outbound (Following) Terminology:** In social media farm dashboards, inbound followers (fans/audience following the farm) and outbound following (accounts the farm followed during interaction scripts) are easily conflated. Never label an outbound following growth filter as bare `🔗 Tăng Follow` because operators assume it means gaining followers. Always use explicit unambiguous labels like `👥 Tăng Đã Follow` or `👥 Tăng Following` paired with the corresponding outbound KPI card.
       * **Primary Population View Rank Column & Deterministic Secondary Tie-Breaker:** When dashboards provide leaderboard views with rank badges (`🥇 #1`, `🥈 #2`, `🥉 #3`, `#N`), operators expect the default comprehensive population tab (e.g. `📋 Toàn Bộ Farm` / `All`) to ALSO display the rank column and badges matching its default sort order (e.g. total followers descending). Hiding the `Hạng` column only on the default tab causes UX dissonance when users switch to delta leaderboards seeking ranks and see accounts out of expected order. Always display rank numbers/badges on the default view as well. When sorting large fleets by metric (e.g. `follower`), dozens of accounts share identical counts (e.g. 0, 80, 88). An unstable default JS sort comparator returning 0 causes random row oscillation across re-renders; always inject a secondary tie-breaker in the comparator (e.g. `if (sortColumn === 'follower') return (b.heart || 0) - (a.heart || 0);`).
     - **Toolbar / Filter Bar Overflow & Scrollbar Suppression:**
       When adding multiple leaderboard tabs or filter buttons to a dashboard toolbar, never let horizontal scrollbars clutter the interface.
       Apply compact button typography (`font-size: 0.78rem - 0.8rem`), tight padding (`6px 10px`, `gap: 6px`), concise labels (e.g. `📈 BXH Follower` instead of `📈 BXH Biến Động Follower`), and suppress overflow scrollbars (`scrollbar-width: none; -ms-overflow-style: none; .filter-buttons::-webkit-scrollbar { display: none; }`).
     - **Farm Watchdog Anomaly Indicators & 0 FYP Sensor Hierarchy (Sol Standard):**
       * **Micro (Account-level):** Never flag individual accounts with alarming `0 FYP` badges based solely on $\Delta Video \ge +1$ and $\Delta Heart = 0$. Video distribution has algorithmic lag (15m-1h upload review, 1-6h initial test pool, 6-24h distribution ramp). For new accounts, 1-2 initial low/zero-view videos are normal variance; stopping uploads or manual account tinkering breaks warming momentum. Tagging individual rows creates alert fatigue and un-actionable noise. Remove per-row 0 FYP tags and sub-filter buttons to keep dashboard clean.
       * **Slow Burn & Delayed Spike Window:** TikTok video lifecycle follows waves: initial test (0-24h), secondary distribution (24-48h), delayed spike (48-72h). Never judge a video under 24h; 48h evaluates trajectory, and 72h is required before concluding dead distribution.
       * **Data Boundary (Profile vs Video Level):** Profile scrapers only capture aggregate `video_count` and `heart_count`, not per-video views or upload timestamps. Do not attempt video-level 0-view alerts without a dedicated video scraper. At profile level, track account-level engagement ratios (`is_potential`), follower drops (`is_anomaly_drop`), and cluster-level health instead.
       * **Macro (Farm-level Infrastructure Sensor):** 0 FYP is valuable strictly as an aggregate infrastructure health sensor. Track 0 FYP rates across clusters: baseline < 15% is healthy. A sudden spike (> 30%) concentrated in a specific machine range, proxy pool, or content batch indicates systemic failure (tainted proxy subnet, duplicate content hash / video deduplication strike, or ROM/device fingerprint blacklist) requiring proxy rotation or content source changes, not account-by-account micro-management.
     - **Farm Cluster Partitioning & Machine Badging:** When monitoring multi-machine farms (e.g. Kibe `< 200` vs Admin `≥ 200`), join snapshot records with account mapping tables (e.g. `LEFT JOIN farm_account_info f ON r1.username = f.username`) with graceful fallback if the table is absent. Add quick cluster filter buttons (`All`, `Cluster Kibe`, `Cluster Admin`) and render compact machine tags (e.g. `[M67]` cyan for Kibe, `[M212]` purple for Admin) directly beside the account name.
     - **Engagement Outlier Badging & Tier Graduation (🚀 TIỀM NĂNG vs 🔥 ĐỀ XUẤT):**
       * Calculate engagement spikes or ratio thresholds (e.g. `heart >= 50 and follower <= 30` or `delta_heart >= 30`) to flag viral/breakout accounts before their follower count catches up.
       * **Mutually Exclusive Tier Invariant:** A breakout account that has successfully caught FYP waves (`is_trending`: $\Delta F \ge 20$ or $\Delta H \ge 50$ or $F \ge 1000$) must NOT simultaneously carry the incubator badge (`is_potential`). Enforce mutual exclusivity in backend scoring: `is_potential = not is_trending and ((h_val >= 50 and f_val <= 30) or (delta_h >= 30))` so accounts visibly graduate from "tiềm năng" into "đề xuất" without row badge collisions.
       * **Four-Layer UI Exposure Parity:** Exposing an emergent account category requires synchronizing 4 layers:
         1. Summary metric: `summary["potential"] = sum(1 for it in items if it.get("is_potential"))`.
         2. KPI summary card: `<div class="kpi-card clickable" id="kpi-card-potential" onclick="setView('potential')">...</div>`.
         3. Toolbar filter pill: `<button class="btn-filter" id="btn-potential" onclick="setView('potential')">🚀 Tiềm Năng</button>`.
         4. Client-side navigation & filter state: Bind `kpiCardMap['potential']`, `btnMap['potential']` in `setView()`, and branch `if (currentView === 'potential') return item.is_potential;` in `filterData()`.
     - **Guarded Code Dispatch on Embedded Monoliths (Double-Brace & Delimiter Traps):**
       * When delegating edits on single-file dashboards wrapped in Python f-strings:
         - All literal JS/CSS braces are doubled (`{{` and `}}`). Anchor strings matching JS blocks (such as `const kpiCardMap = {{ ... }};`) MUST preserve doubled braces `{{` / `}}`, or the contract fails with `ANCHOR_NOT_FOUND`.
         - Patch contracts for subagents must use exact `OLD_STRING: <<<` and `NEW_STRING: <<<` block delimiters (not markdown backticks).
         - Keep cumulative diff <= 30 lines to stay within atomic surgery budgets.
     - **Windows In-Memory Daemon Reload Sequence:**
       * Editing single-file server scripts does NOT hot-reload running python code. Relaunching the VBS runner while the old process still listens causes silent bind failures (`Address already in use`).
       * Identify the active listener PID (`tasklist /V /FI "IMAGENAME eq pythonw.exe"`), terminate it explicitly (`taskkill /F /PID <pid>`), and trigger `wscript D:\Taadaa\tools\start_<dashboard>_hidden.vbs`. Verify the new PID and test the updated endpoint via browser navigation.
     - **Multi-Metric Leaderboard Extensibility & Contextual Sub-filters:**
       When scaling from 1-2 leaderboards to multiple metrics (e.g. Followers, Following, Hearts/Likes):
       * Avoid binary ternary logic (`const deltaKey = (view === 'follower') ? 'delta_f' : 'delta_h'`) which silently misroutes when a 3rd metric is added; use an explicit mapping lookup dictionary for `deltaKey`.
       * Adapt sub-filter labels and visibility contextually per active leaderboard: change negative delta labels (`Tụt Follow (-)` vs `Giảm Following (-)` vs `Giảm Tim (-)`), and conditionally hide metric-specific anomaly filters (e.g. hide follower-drop or 0-FYP video filters when viewing Following leaderboard) to prevent confusing empty results.
       * Keep `btnMap`, `isLeaderboard` checks, and table sorting handlers aligned across all leaderboard view keys.
     - **Toolbar Button Row Overflow & Scrollbar Suppression:**
       * When adding multiple filter/view buttons beside a search bar in a single toolbar, avoid giving the search box `flex: 1` as it squeezes the button row and triggers horizontal scrollbars. Use a fixed or bounded basis (`flex: 0 0 220px`).
       * Keep button labels concise (e.g. `📈 BXH Follower`, `👥 BXH Following`, `💖 BXH Tim` instead of verbose `BXH Biến Động ...`) to save 30-40% horizontal width.
       * Tune button styling to compact dimensions: `padding: 6px 10px; font-size: 0.78rem; border-radius: 7px; gap: 6px;`.
       * Enable `flex-wrap: wrap` and suppress browser scrollbars cleanly via CSS (`scrollbar-width: none; -ms-overflow-style: none; ::-webkit-scrollbar { display: none; }`) so the row remains seamless without ugly horizontal scrollbars under navigation tabs.
     - **Farm Watchdog Anomaly Indicators & 0 FYP Sensor Hierarchy (Sol Standard):**
       * **Micro (Account-level):** Never flag individual accounts with alarming `0 FYP` badges based solely on $\Delta Video \ge +1$ and $\Delta Heart = 0$. Video distribution has algorithmic lag (15m-1h upload review, 1-6h initial test pool, 6-24h distribution ramp). For new accounts, 1-2 initial low/zero-view videos are normal variance; stopping uploads or manual account tinkering breaks warming momentum. Tagging individual rows creates alert fatigue and un-actionable noise. Remove per-row 0 FYP tags and sub-filter buttons to keep dashboard clean.
       * **Slow Burn & Delayed Spike Window:** TikTok video lifecycle follows waves: initial test (0-24h), secondary distribution (24-48h), delayed spike (48-72h). Never judge a video under 24h; 48h evaluates trajectory, and 72h is required before concluding dead distribution.
       * **Data Boundary (Profile vs Video Level):** Profile scrapers only capture aggregate `video_count` and `heart_count`, not per-video views or upload timestamps. Do not attempt video-level 0-view alerts without a dedicated video scraper. At profile level, track account-level engagement ratios (`is_potential`), follower drops (`is_anomaly_drop`), and cluster-level health instead.
       * **Macro (Farm-level Infrastructure Sensor):** 0 FYP is valuable strictly as an aggregate infrastructure health sensor. Track 0 FYP rates across clusters: baseline < 15% is healthy. A sudden spike (> 30%) concentrated in a specific machine range, proxy pool, or content batch indicates systemic failure (tainted proxy subnet, duplicate content hash / video deduplication strike, or ROM/device fingerprint blacklist) requiring proxy rotation or content source changes, not account-by-account micro-management.
     * **Interactive KPI Cards as Direct Navigation Shortcuts (Clickable KPI Pattern):**
     * Never leave top KPI summary cards (Total Followers, Following, Hearts, Live, Trending, Missing Avatar) as passive text blocks. Operators intuitively tap/click cards expecting immediate navigation or filtering.
     * Bind each KPI card's `onclick` to the corresponding view, sorting, or leaderboard action:
       - Metric rankings (`Followers`, `Following`, `Hearts`) -> route directly to the respective leaderboard sorted descending (`setView('bxh_follower')`, etc.).
       - Status / categorical metrics (`Live`, `🔥 Cắn Đề Xuất`, `⚠️ Chưa Avatar`) -> route directly to the corresponding filtered subset (`setView('live')`, `setView('trend')`, `setView('no_avatar')`).
       - Population baseline cards (`Total Accounts`) -> remain non-clickable if representing the full unfiltered population.
     * Visual affordance: explicitly add `style="cursor: pointer;"`, hover border/shadow highlight, and descriptive `title="..."` tooltips so desktop and touch users know cards are interactive.
     - **Substring Collision vs Exact Match in Fleet Entity Search (`m<ID>` / `tik<ID>` Query Pollution):**
     * When providing a unified search input on farm/fleet dashboards that searches across multiple fields (username, machine `m<ID>`, slot `tik<ID>`, status, created date):
     * A naive substring search `item.username.toLowerCase().includes(query)` causes false-positive account collisions when querying by machine prefix (e.g. searching `m16` for Machine 16 matches `@lenam16696` belonging to Machine 63 because `m16` is a substring of the username).
     * Similarly, jumping to a machine from a heatmap or health table by injecting `m<ID>` into the search box causes phantom accounts to bleed into the machine's account list.
     * **Canonical Pattern:** Detect structured query patterns using regex and branch search behavior:
       ```javascript
       const isMachineQuery = /^m\d+$/i.test(query);
       const isTikQuery = /^(t|tik\s*)\d+$/i.test(query);

       let matchQuery = false;
       if (!query) {
           matchQuery = true;
       } else if (isMachineQuery) {
           matchQuery = !!(item.may && ('m' + item.may).toLowerCase() === query);
       } else if (isTikQuery) {
           matchQuery = !!(item.tik && (query === 't' + item.tik || query === 'tik ' + item.tik || query === 'tik' + item.tik));
       } else {
           matchQuery = (item.created_at && item.created_at.includes(query)) ||
                        item.username.toLowerCase().includes(query) ||
                        item.status.toLowerCase().includes(query) ||
                        (item.may && ('m' + item.may).toLowerCase() === query) ||
                        (item.tik && (query === 't' + item.tik || query === 'tik ' + item.tik || query === 'tik' + item.tik));
       }
       ```
     * When `isMachineQuery` is true, match strictly against `item.may`. Do NOT evaluate `username.includes(query)` to prevent false ghost account alerts.
     - Ensure the default table view (e.g. "Toàn bộ Farm") preserves standard search, status filters, and multi-column sorting when switching back from a leaderboard tab.
     - In auto-refresh loops (`setInterval` fetch `/api/data`), ensure in-memory state (`initialData.items`) updates without resetting the user's active view tab, search input, or pagination.
     - **Auto-Refresh Scroll-Jumping & Page-Snapping to Top Pitfall (Height Collapse in `setInterval`):**
       * In polling/auto-refreshing dashboards (e.g. 30s `setInterval`), calling `tbody.innerHTML = ''` and triggering forced reflow / fade animations (`void tbody.offsetWidth`) causes the table/container height to instantaneously collapse to near-zero.
       * When document height shrinks below the current scroll offset, the browser automatically clamps `window.scrollY` to 0. When new rows populate, the user gets abruptly snapped back to the top of the page while browsing mid-list.
       * **Seamless Update Invariant:**
         1. Pass an `isAutoRefresh` flag to render functions during periodic intervals.
         2. Skip fade/empty animations entirely when `isAutoRefresh` is true.
         3. Lock container height before rendering: `container.style.minHeight = container.offsetHeight + 'px'`.
         4. Build all rows into a `DocumentFragment` and swap atomically via `tbody.replaceChildren(fragment)` instead of wiping innerHTML.
         5. Record `prevScrollY = window.scrollY` and restore position inside `requestAnimationFrame(() => { container.style.minHeight = ''; if (Math.abs(window.scrollY - prevScrollY) > 5) window.scrollTo({ top: prevScrollY, behavior: 'instant' }); })`.
     - **False-Positive Anomaly Drop Alert on Small Accounts (-1/-2 Normal Variance vs Real Drop):**
       * On accounts with ~50-100 followers, losing just 1 follower yields a `drop_rate` of ~1.0%. A naive threshold like `delta_f < 0 and drop_rate >= 1.0%` falsely brands normal accounts losing 1 follower (`-1 | 1.01%`) with alarming red badges (`⚠️ TỤT BẤT THƯỜNG`), causing operator panic and alert fatigue.
       * On social media platforms (TikTok/IG), drops of 1 or 2 followers (-1, -2) are standard daily variance (accidental unfollows, periodic bot sweeps).
       * **Alert Hardening Invariant:** Hardcode an exclusion floor: losing only 1 or 2 followers (`delta_f >= -2`) must NEVER be flagged as an anomaly, regardless of drop percentage. Anomaly alerts must require significant volume (`delta_f <= -5`) OR non-trivial loss count combined with high drop rate (`delta_f <= -3` AND `drop_rate >= 5.0%`).
     - **Client-Side RAM Cache vs Auto-Refresh Data Pitfall**:
       * When UI code (HTML/JS template in `renderTable`) is updated on the server, clients already keeping an open browser tab (especially mobile Safari/Chrome) will NOT automatically receive the new render code via `/api/data` background polling. Polling only fetches raw JSON data; the in-memory JS closure continues running the old render function.
       * When users report that an old badge or element is "still appearing" after code was deployed and verified clean on the server, check the client device's open tab timestamp against deployment time before suspecting code rollback or database residue. Direct them to hard-reload / pull-to-refresh the browser tab so the newly served HTML/JS template is loaded into RAM.
     - **Thorough Cleanup Contract for Removed Features (Zero Residue)**:
       * When an operator requests removing a metric, badge, or filter from a single-file dashboard, ensure a comprehensive cleanup across all 6 coupling layers in one pass:
         1. Inline Table Badges: Remove badge generation logic and interpolation `${badge}` from `renderTable`.
         2. Filter Buttons: Remove `<button>` elements from HTML filter rows.
         3. Dynamic Filter State & Visibility: Remove button IDs from active-toggle lists, dictionary mappings (`dfMap`), and view-switching visibility checks (`isEligible`, `btn.style.display`).
         4. Client-side Filter Logic: Remove filter branches in `filterData()` (e.g. `if (filter === 'X') return ...`).
         5. CSS Selectors: Remove dedicated button active/hover classes (e.g. `.btn-filter.delta-X.active`).
         6. Test Assertions: Add negative assertions (e.g. `assert "badge" not in html`, `assert "btn-id" not in html`) to the test suite to permanently prevent regression.
         7. Process Restart: Kill the listening process PID và relaunch để đảm bảo in-memory server template phản ánh code sạch.
     * **Python BaseHTTPRequestHandler Socket Hang, Keep-Alive Exhaustion (os error 10060) & Subagent Probe Timeout:**
       - Trên Windows, `http.server.ThreadingHTTPServer` kết hợp `BaseHTTPRequestHandler` mặc định `timeout = None` và không gửi header `Connection: close`.
       - Khi các client HTTP/1.1 (như `curl` không có cờ `--http1.0`, browser tabs hoặc test scripts) gửi request, connection sẽ được giữ ở trạng thái `ESTABLISHED` / `CLOSE_WAIT` vô thời hạn nếu client không chủ động đóng socket.
       - **Bẫy Subagent Timeout 600s:** Khi subagent hoặc terminal gọi `curl -s "http://127.0.0.1:..."` kiểm tra endpoint sau restart mà thiếu cờ HTTP/1.0 hoặc max-time, lệnh `curl` sẽ bị treo cứng chờ server đóng kết nối. Subagent bị đứng ở call đó và cạn toàn bộ budget timeout 600s!
       - Khi nhiều client/tab truy cập cùng lúc, server cạn kiệt worker threads và socket descriptors, khiến các kết nối tiếp theo văng lỗi: `os error 10060 (WSAETIMEDOUT: A connection attempt failed because the connected party did not properly respond after a period of time)`.
       - **Giải pháp dứt điểm:**
         1. Thiết lập `timeout = 10` trên class kế thừa `BaseHTTPRequestHandler`.
         2. Override hàm `end_headers()` để tự động bơm `Connection: close` và `self.close_connection = True` cho mọi response (HTML, JSON, 400, 404) một cách DRY và triệt để:
            ```python
            class AppHandler(BaseHTTPRequestHandler):
                timeout = 10

                def end_headers(self):
                    self.send_header("Connection", "close")
                    super().end_headers()
                    self.close_connection = True
            ```
         3. Trong mọi lệnh probe của Worker/Subagent hoặc script tự động, luôn dùng Python `urllib` có timeout (`urllib.request.urlopen(url, timeout=5)`) hoặc `curl --http1.0 -m 5 -s ...` để đảm bảo lệnh trả về ngay lập tức <0.1s, không bao giờ block subagent.
     * **Time-Series Growth Charts & On-Demand Historical Query Pattern (O(1) Data Path):**
       * Khi bổ sung biểu đồ tăng trưởng lịch sử (growth curve: Followers, Tim, Following, Videos theo ngày) cho từng tài khoản/thực thể trên web dashboard:
       * **Composite Index Preflight:** Bảng `snapshots` SQLite lưu dữ liệu lịch sử thường chưa có index theo username. Truy vấn `WHERE username = ? ORDER BY timestamp ASC` sẽ scan toàn bảng (hàng chục ngàn dòng), gây nghẽn I/O khi nhiều lượt click. Luôn đảm bảo composite index:
         `CREATE INDEX IF NOT EXISTS idx_snapshots_user_ts ON snapshots (username, timestamp ASC);`
         giúp câu query giảm từ hàng trăm ms xuống < 1ms.
       * **On-Demand Route vs Payload Bloat:** Tuyệt đối không nhồi mảng lịch sử toàn bộ tài khoản vào payload chính `/api/data` hay HTML ban đầu (farm 1.000 acc x 15 snapshots sẽ thổi phình JSON từ ~200KB lên >5MB, gây giật lag và tốn băng thông auto-refresh trên mobile Safari). Thay vào đó, tách route chuyên biệt `GET /api/history?username=...` chỉ fetch theo yêu cầu khi người dùng bấm xem chi tiết từng nick.
       * **Farm-wide Historical Aggregation & Status != 'ERROR' Filtering Trap**:
         - **The Single-Glitch Cascade Trap:** Trong farm 1.000+ acc, chỉ cần duy nhất 1 nick gặp sự cố proxy timeout/bot-check tạm thời khiến script cào trả về `status = 'ERROR'` với mặc định `follower = 0, following = 0` (như nick `@m.ngc4624` 54 fl / 109 following), cú tụt ảo $-54$ fl và $-109$ fl này sẽ nuốt chửng toàn bộ mức tăng thật của 30-50 nick khác, làm toàn farm bị đảo chiều báo âm ($-17$ fl, $-85$ following). BẮT BUỘC lọc `WHERE status != 'ERROR'` trong tất cả các CTE `RankedAll`, `RankedPrev`, `DayUser` để hệ thống tự động bỏ qua snapshot lỗi và giữ lại snapshot `LIVE` hợp lệ gần nhất.
         - **Midnight Partial Scan Dip Trap & The Flawed 50% Threshold on Farm Growth Charts:**
           * Khi người dùng yêu cầu "Biểu đồ tăng trưởng toàn farm" (`get_farm_history` / `farmHistoryModal`), nếu truy vấn gom nhóm theo ngày (`substr(timestamp, 1, 10)`), một đợt quét dở dang (ví dụ 1.129/1.252 nick) sẽ khiến tổng hôm nay bị thiếu hụt 123 nick.
           * Nếu tính delta bằng phép trừ bulk thô (`SUM(hôm nay) - SUM(hôm qua)`), 123 nick chưa quét bị coi là 0, dẫn đến sụt ảo hàng nghìn follower/tim ($-1.082$ fl, $-2.810$ tim) và báo đỏ lòm ("đỏ lòm").
           * **Bẫy ngưỡng 50% (`< 0.5 * prev`):** Chốt chặn cũ chỉ fallback khi quét `< 50%`. Khi quét được 90% (1.129 nick), ngưỡng 50% không kích hoạt, khiến số liệu dở dang lọt ra ngoài.
           * **Giải pháp chuẩn:** Thắt chặt ngưỡng fallback lên `< 0.98 * prev` (hoặc so sánh trực tiếp với tổng fleet active `get_farm_data()`), hoặc áp dụng carry-forward: nick chưa có snapshot hôm nay tự động kế thừa snapshot gần nhất hôm qua để đảm bảo quy mô fleet luôn đủ 100% trước khi tính delta ngày.
         - **Farm Growth Chart Modal Composition:** Cung cấp nút mở `📈 Biểu Đồ Farm` trên Header và `📊 Biểu Đồ Toàn Farm` trên Toolbar. Modal hỗ trợ tab mặc định `[⭐ Tổng Quan]` (4 card lớn kèm mini sparklines + bảng chi tiết ngày) và 3 tab đồ thị đường SVG độc lập (`Follower`, `Tim`, `Đã Follow`) kèm hover tooltip trực quan.
       * **Zero-Dependency Embedded SVG Line Chart Pattern:** Khi làm biểu đồ trên single-file Python dashboard (không dùng thư viện ngoài/CDN như Chart.js hay D3 để chạy offline/LAN độc lập):
         - Dùng thẻ `<svg viewBox="0 0 W H" preserveAspectRatio="none">`.
         - Map mốc tọa độ tuyến tính: `x = padX + (idx / (len - 1)) * (W - 2 * padX)`, `y = padY + (1 - (val - minVal) / (maxVal - minVal || 1)) * (H - 2 * padY)`.
         - Tạo gradient fill bằng `<defs><linearGradient>` kết hợp `<polygon points="... padY_bottom" fill="url(#grad)"/>` và đường nét viền `<polyline points="..." stroke="var(--accent)" fill="none" stroke-width="2"/>`.
         - Gắn các `<circle cx="x" cy="y" r="4">` có event mouseover / touchstart để hiện floating tooltip (ngày, số lượng, delta so với ngày trước).
         - Xử lý edge case: Nếu chỉ có 1 điểm dữ liệu lịch sử hoặc mảng rỗng -> ẩn SVG, hiện `div.chart-empty` thông báo "Chưa có đủ dữ liệu lịch sử để vẽ biểu đồ".
       * **Mobile-Responsive Chart UX (Modal + Metric Tabs):** Trên màn hình điện thoại (Safari/iOS), tránh vẽ dồn cả 4 chỉ số vào 1 biểu đồ gây rối. Thiết kế modal dạng trượt, có thanh chuyển tab chỉ số (`Follower` | `Tim` | `Đã Follow` | `Video`), hỗ trợ touch tooltip hiển thị rõ ngày + số lượng + delta, kèm bảng tóm tắt lịch sử dạng số (`Ngày | Giá trị | Biến động`) bên dưới biểu đồ.
       * **CSS Flexbox Text Squeeze in SVG/Modal Containers Pitfall:**
         - Khi container (.chart-wrapper) dùng `display: flex; align-items: center; justify-content: center;` chứa cả `<svg width="100%">` và các khối trạng thái (`.chart-loading`, `.chart-empty`), flexbox sẽ bóp nghẹt các khối text con xuống bề ngang tối thiểu (~30-40px). Điều này làm văn bản bị ép thành một cột dọc 1 chữ/1 từ kỳ quái (`Chưa / có đủ / dữ liệu...`).
         - Giải pháp: Định vị tuyệt đối `.chart-loading, .chart-empty { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 480px; z-index: 5; }`, hoặc ẩn hoàn toàn `<svg style="display:none">` khi đang loading hoặc rỗng để SVG không tham gia tính toán flex layout.
       * **Modal Metric Tab Race Condition & Mutually Exclusive States:**
         - Trong modal có nhiều tab chỉ số, nếu người dùng bấm chuyển tab (`switchMetric`) trong khi API fetch dữ liệu lịch sử vẫn đang chạy ngầm (`currentHistoryData === null`), việc gọi render sớm sẽ khiến code tưởng lầm là "không có dữ liệu" và hiển thị `.chart-empty` đè lên `.chart-loading`, dẫn đến lỗi cả 2 dòng thông báo hiển thị đè nhau cùng lúc.
         - Luôn chặn: `if (currentHistoryData && currentHistoryData.history && currentHistoryData.history.length > 0) renderModalChartAndTable();` trong hàm `switchMetric`.
         - Khi mở modal mới, luôn reset sạch sẽ trạng thái: gán `currentHistoryData = null`, ẩn cả empty & SVG, reset tiêu đề cột về mặc định, và chỉ render sau khi fetch trả về 200 OK.
       * **SQLite Read-Only Connection vs DDL Index Execution:**
         - Kết nối SQLite qua URI `file:<path>?mode=ro` (chế độ chỉ đọc để tránh database lock với writer processes) sẽ văng lỗi `OperationalError: attempt to write a readonly database` nếu chạy `CREATE INDEX IF NOT EXISTS`.
         - Tuyệt đối không nhồi câu lệnh DDL `CREATE INDEX` vào trong các hàm query GET đọc dữ liệu. Luôn dùng `WHERE username = ? COLLATE NOCASE` để tránh lỗi so khớp phân biệt chữ hoa/chữ thường.
       * **Fleet Tracking Metric Boundary (Tại sao KHÔNG tích hợp Lượt Xem / Views vào Profile Dashboard):**
         - Kỹ thuật: TikTok public profile HTML (`__UNIVERSAL_DATA_FOR_REHYDRATION__` / `webapp.user-detail`) hoàn toàn KHÔNG có trường tổng view kênh, chỉ có video-level view (`playCount`).
         - Rủi ro vận hành: Muốn lấy view phải gửi request bóc tách toàn bộ video của từng nick. Với farm ~1.000 acc, số request tăng 5x-10x, kích hoạt SlardarWAF / HTTP 429 chặn proxy pool, làm sập/timeout phiên cào Daily 07:00 sáng.
         - Bản chất dữ liệu: Tim (Likes/Hearts) và Follower chính là tấm gương phản chiếu trực tiếp của View. Nick cắn đề xuất hay 0 view/flop đều được bộc lộ qua `delta_heart` và `delta_follower` mà không cần cào view chi tiết.
         - Quy tắc: Giữ profile tracker nhẹ, nhanh, an toàn O(1). Chỉ cào view khi có scraper chuyên biệt dành riêng cho tập mẫu video nhỏ cần phân tích sâu.
       * **Multi-Metric Scale Mismatch & Chart Composition Pattern (Sol & Claude Consensus):**
         - Khi xây dựng biểu đồ tăng trưởng lịch sử đa chỉ số (Likes, Followers, Following, Videos): Tuyệt đối KHÔNG ép 4 chỉ số vào chung một đồ thị có trục Y tuyến tính duy nhất. Tim (vài chục nghìn) sẽ đè bẹp Followers (vài trăm) và Videos (vài chục) xuống sát đáy thành một đường thẳng lì mất hết độ dốc.
         - Giữ các tab chỉ số độc lập cho màn hình di động (Mobile Safari), hoặc triển khai **Small Multiples** (lưới mini-sparkline 2x2, mỗi ô tự co giãn trục Y theo min/max riêng) hoặc **Indexed Chart** (chuẩn hóa về mốc ngày đầu = 100%) để so sánh nhịp độ tăng trưởng.
       * **Defensive Schema Projection for Sub-entity Slot Mapping (Tik 1 -> Tik 8):**
         - Khi join bảng phụ trợ ánh xạ máy và slot (ví dụ `farm_account_info` chứa `may`, `tik`, `host_id`), kiểm tra sự tồn tại của cột bằng `PRAGMA table_info` trước khi dựng SQL: `tik_select = "f.tik" if has_tik_col else "NULL AS tik"`. Điều này giúp code chạy an toàn tuyệt đối, không crash khi chạy với test fixtures hoặc schema SQLite cũ.
         - Định dạng tag hiển thị máy & slot tinh gọn: `[Mxx · Ty]` (ví dụ `M39 · T1`) kèm tooltip đầy đủ `Máy 39 (Tik 1)`, đồng thời hỗ trợ tìm kiếm linh hoạt trên toolbar (`tik 3`, `t3`, `m56`).
       * **Engagement Ratio (Tim / Follower) trong Farm Nuôi Chéo:**
         - Trong farm chạy kịch bản follow chéo nội bộ, số follower bị thổi phồng đồng đều giữa các acc. Lượt Tim (Like) chỉ có được khi video được thuật toán TikTok phân phối lên For You Page (FYP) cho người xem thật.
         - Tỷ lệ `Tim / Follower` chính là bộ lọc "săn nick vàng" tách biệt acc vỏ rỗng (chỉ có follow chéo) với acc cắn đề xuất thật sự. Áp dụng ngưỡng động (bội số của median toàn farm, ví dụ > 2x median) và bỏ qua nick non (< 50 fl) để loại bỏ nhiễu.
       * **Machine Fleet Health (Cảm Biến Bắt Lỗi Hạ Tầng Đồng Loạt):**
         - Sự cố hạ tầng (proxy subnet bẩn, rớt IP, ROM/app crash) luôn mang tính chất đồng loạt trên cùng một thiết bị. 1 nick die là bình thường, nhưng 5-6 nick trên cùng một máy đứng hình hoặc die cùng ngày là cảnh báo lỗi máy/mạng.
         - Thiết kế bảng tóm tắt Heatmap 160 máy (xanh/vàng/đỏ) sắp xếp theo dải proxy, chỉ làm nổi bật các máy có vấn đề (vàng/đỏ) để xử lý triệt để trước khi lan rộng toàn dàn.
       * **Farm Metric Delta Disconnect vs Population Expansion (New Account Asymmetry & Churn Dissonance):**
         - Khi farm bổ sung hàng chục tài khoản mới (ví dụ +50 nick, nâng tổng từ 992 lên 1.042), các nick mới chưa có snapshot ngày trước (`prev is None`) nên được gán `delta = 0`.
         - Tổng tích lũy (`total_followers`, `total_hearts`) tăng mạnh nhờ lượng tài sản mới nhập vào (+41 followers, +1.034 tim), nhưng chỉ số Delta tổng (`total_delta_follower`, `total_delta_following`) chỉ phản ánh biến động của riêng nhóm nick cũ ($\sum \delta_{old}$).
         - Nếu một số nick cũ bị tụt follow hoặc TikTok quét nhả follow vượt lượng tăng tự nhiên của nick cũ khác, Delta tổng sẽ báo âm (ví dụ `-17` fl, `-85` following) dù toàn farm đang nở ra.
         - Luôn phân định rõ giữa **Tổng tích lũy toàn farm** (Macro Expansion) và **Tăng trưởng thực thể cũ** (Cohort Delta) khi giải thích cho người vận hành, tránh hoang mang "mới thấy tăng giờ thấy ghi giảm".
       * **Leading Plus Hardcoding & Double-Sign String Glitch ('+-' Trap):**
         - Tuyệt đối CẤM ghép chuỗi cứng dấu `+` đằng trước biến delta (ví dụ `+{summary['total_delta_following']}` hoặc `+${formatNum(totDeltaFl)}`). Khi giá trị âm, chuỗi sẽ biến thành dị dạng `+-85` (ví dụ `📈 Tổng tăng: +-85`).
         - Bắt buộc dùng hàm format có điều kiện: `(delta > 0 ? '+' : '') + formatNum(delta)` và đổi nhãn động (`Tổng tăng:` khi delta >= 0 vs `Biến động:` khi delta < 0). Xem chi tiết tại `references/farm-metric-delta-and-population-expansion-pitfalls.md`.
2. **Route alignment:** Every UI tab that promises data or actions (e.g. Schedules, API & cURL) must be backed by corresponding routes in `do_GET` / `do_POST`.
3. **Background daemon runners:** Any scheduler or poller thread (e.g. `schedule_runner`) must be started in `main()` as a daemon thread and include per-minute debounce so scheduled tasks do not trigger repeatedly in the same interval.
4. **Safe in-place update & port-bound background restart:**
   - Always run `python -m py_compile <path/to/server.py>` before restarting to ensure no syntax errors brick the service.
   - Do not use generic `taskkill /f /im python.exe`. Target only the process owning the listening port. Note: on MSYS/Git-Bash shells on Windows, POSIX-style `//F //PID <PID>` or native `/F /PID` can fail with `ERROR: Invalid argument/option - '//F'`; invoke through `cmd.exe /c "taskkill /F /PID <PID>"` or PowerShell:
     ```bash
     cmd.exe /c "taskkill /F /PID <PID>"
     ```
     Or via PowerShell:
     ```powershell
     powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort <PORT> -State Listen).OwningProcess -Force -ErrorAction SilentlyContinue; Start-Process (Get-Command python).Source -ArgumentList '<PATH_TO_SCRIPT>' -WindowStyle Hidden"
     ```
   - For dashboards with a hidden launcher VBS (e.g. `wscript "<path>/start_<dashboard>_hidden.vbs"`), invoke `wscript` directly from bash after killing the old PID to ensure non-blocking, headless operation without console popups.
   - **Multi-tenant / Sub-dashboard route integration:**
     - When mounting an auxiliary dashboard (e.g. `/tiktok` into an existing manager like MikroTik Web Manager on port 2310), ensure both the document route (`/route` and trailing slash `/route/`) and any associated JSON APIs (`/api/route`) are registered.
     - Add navigation anchors in the header for fast cross-dashboard switching.
     - Dynamically append import search paths (`sys.path.insert(0, ...)` if outside the app root) inside route handlers to avoid hard import failures if module locations differ.
   - **Post-restart verification cycle:** Wait 2s (`sleep 2`), then verify:
     1. Live HTTP response: Note that Python `BaseHTTPRequestHandler` instances typically only implement `do_GET` (not `do_HEAD`), causing `curl -I` to return `501 Unsupported method ('HEAD')`. Verify using GET via Python urllib or curl status check:
        `python -c "import urllib.request; resp = urllib.request.urlopen('http://127.0.0.1:<PORT>/'); print(resp.status, resp.reason)"`
     2. HTML grep check (e.g. `curl -s http://127.0.0.1:<PORT>/ | grep -o "<token>"`)
     3. Initial GET state check
     4. Ephemeral canary POST creation
     5. Populated GET state confirmation
     6. Canary POST deletion and empty state confirmation

## Verification checklist

- Target URL/port is reachable and identifies the intended app/version.
- Requested setting reflects the new value after reload.
- Import preview/parser reports the expected count and no unexpected parse failures.
- No unrelated application, repository, cron job, lease, or credential store was changed.
- Final response is concise, in the requested language, and distinguishes completed work from blockers.

### Windows Background HTTP Server Long-Running Hangs & Watchdog Production Standards
When maintaining locally hosted Python HTTP servers (like `ThreadingHTTPServer` or `BaseHTTPRequestHandler`) running 24/7 on Windows:
1. **Root Cause of `ERR_EMPTY_RESPONSE` over Time**:
   - Long-lived processes spawned under transient terminal sessions (e.g. MSYS bash or temporary cmd) remain attached to dead parent pipes.
   - High-frequency client polling (`setInterval` auto-refresh every 30s) across multiple browser tabs causes gradual socket descriptor / worker thread exhaustion on Windows. The server accepts incoming TCP connections but drops them immediately without writing HTTP headers or body.
2. **Watchdog Hardening Standards (Sol Auditor / Production Standard)**:
   - **Process Identity Verification**: Never blindly kill any process listening on the target port via `Get-NetTCPConnection`. Always inspect `(Get-CimInstance Win32_Process -Filter "ProcessId = $pid").CommandLine` to verify it matches the target script path (e.g. `*tiktok_dashboard.py*`) before calling `Stop-Process`.
   - **Persistent Telemetry**: Write watchdog events (health check failures, target PIDs terminated, restart timestamps, recovery latency) to a dedicated persistent log file (`runtime/logs/<app>_watchdog.log`) instead of only standard output.
   - **Circuit Breaker / Exponential Backoff**: Implement restart limits (e.g. max 3 consecutive restarts within a 5-minute rolling window). If an underlying syntax error or port collision causes continuous restart failure, back off or halt to prevent CPU exhaustion and log flooding.
   - **Dual Autostart Parity**: Deploy both the application launcher and its watchdog supervisor as hidden `.vbs` shortcuts in `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\` so resilience survives Windows reboots.
When maintaining locally hosted Python HTTP servers (like `ThreadingHTTPServer` or `BaseHTTPRequestHandler`) running 24/7 on Windows:
1. **Root Cause of `ERR_EMPTY_RESPONSE` over Time**:
   - Long-lived processes spawned under transient terminal sessions (e.g. MSYS bash or temporary cmd) remain attached to dead parent pipes.
   - High-frequency client polling (`setInterval` auto-refresh every 30s) across multiple browser tabs causes gradual socket descriptor / worker thread exhaustion on Windows. The server accepts incoming TCP connections but drops them immediately without writing HTTP headers or body.
2. **Watchdog Hardening Standards (Sol Auditor / Production Standard)**:
   - **Process Identity Verification**: Never blindly kill any process listening on the target port via `Get-NetTCPConnection`. Always inspect `(Get-CimInstance Win32_Process -Filter "ProcessId = $pid").CommandLine` to verify it matches the target script path (e.g. `*tiktok_dashboard.py*`) before calling `Stop-Process`.
   - **Persistent Telemetry**: Write watchdog events (health check failures, target PIDs terminated, restart timestamps, recovery latency) to a dedicated persistent log file (`runtime/logs/<app>_watchdog.log`) instead of only standard output.
   - **Circuit Breaker / Exponential Backoff**: Implement restart limits (e.g. max 3 consecutive restarts within a 5-minute rolling window). If an underlying syntax error or port collision causes continuous restart failure, back off or halt to prevent CPU exhaustion and log flooding.
   - **Dual Autostart Parity**: Deploy both the application launcher and its watchdog supervisor as hidden `.vbs` shortcuts in `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\` so resilience survives Windows reboots.

## CLIProxyAPI management and OAuth validation

For CLIProxyAPI/CPAMC-like local proxy dashboards, keep three credential layers separate:

1. **Management Key** controls `/v0/management/*` and the dashboard. It has no universal default. `remote-management.secret-key: ""` disables the management routes and produces `404`; after configuring a key, unauthenticated requests should produce `401`, while an authenticated request should produce `200`. Never confuse it with a neighboring gateway's dashboard password or an upstream API key.
2. **Client API keys** authenticate `/v1/*`. Never leave `your-api-key-*` values from an example config enabled; remove placeholders rather than treating the endpoint as healthy.
3. **OAuth/auth files** are upstream account state. A running process, a listening port, or a successful `/v1/models` catalog request does not prove that a provider can complete a model request.

For a model smoke test, first verify the actual process/listener port and query `/v1/models`. Select a model returned by that exact instance, then send exactly one minimal `POST /v1/chat/completions` request and record only HTTP status, returned model, finish reason, and a short response prefix. Do not retry-loop or print tokens/account data. Interpret `403 PERMISSION_DENIED` with `VALIDATION_REQUIRED` / `Verify your account to continue` as an upstream OAuth account-verification issue: do not delete, disable, or rewrite the auth file. Preserve the raw upstream JSON and extract `details[].metadata.validation_url` (or the provider-equivalent validation URL) before the proxy reduces the error to a generic 403; have the operator verify in the browser signed into the affected account, then reconnect and perform one fresh smoke test. A connection test, token refresh, quota read, or model catalog response alone does not prove generation is authorized.

When using a screenshot, verify the address bar port against the live listener; `6018`, `60818`, and neighboring gateway ports may be different instances. For the CLIProxyAPI recovery transcript, safe header probes, and Antigravity validation interpretation, see `references/cliproxy-antigravity-recovery.md`.

## Supporting detail

- `references/runtime-app-update-and-import.md` — Reusable OmniRoute-style workflow, UI paths, and credential-safe proxy import handling.
- `references/omniroute-watchdog-resilience-and-fail-closed-runbook.md` — OmniRoute Fail-Closed Proxy & Watchdog Resilient Supervision Runbook: two-tier liveness/health checks, preventing false-positive restarts on pool 401/403 errors, and RAM/repo synchronization.
See `references/google-drive-desktop-lost-found.md` for diagnosing and resolving Google Drive for Desktop "Lost and Found" (`Bị thất lạc và đã tìm thấy`) sync conflicts and notifications.
See `references/gpm-antidetect-local-api-and-proxy-mapping.md` for GPMLogin local REST API endpoints (port 19995, `/api/v3/profiles`), payload specifications (`profile_name`, `raw_proxy`), profile preservation rules, and 5:1 multi-account proxy pool batching.
See `references/farm-metric-delta-and-population-expansion-pitfalls.md` for resolving metrics dissonance between macro population expansion and cohort delta drops on farm tracking dashboards, along with safe string formatting invariants.
See `references/time-window-mismatch-and-dashboard-daemon-reload.md` for resolving Time Window Mismatch between daily web scrape and intraday bot telemetry on farm dashboards, in-memory pythonw daemon reload, and closeout gate binding safety.
