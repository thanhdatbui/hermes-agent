# OmniRoute Dashboard Logs Inspection & UI Indicators

Detailed guide for inspecting and interpreting the OmniRoute Dashboard Logs UI (`http://<ip>:20129/dashboard/logs`), backed by `src/shared/components/RequestLoggerV2.tsx`.

## 1. Request Grouping & Correlation
OmniRoute groups related requests using `correlationId` (e.g., when a request triggers automated retries, account rotation, or fallback models in a Combo cascade, or when a client passes `X-Correlation-Id`).

In `RequestLoggerV2.tsx`:
- All requests sharing the same `correlationId` form a correlation group.
- The first request in the sorted list is the root/parent request (`isRetry: false`).
- **All subsequent requests** in the group are marked as children (`isRetry: !isFirst`), regardless of whether previous requests failed or succeeded!
- Group health is computed as:
  * `"healed"`: At least one failure (`status >= 400` or `active`) followed by at least one success (`200 <= status < 300`).
  * `"failed"`: All attempts in the group failed.
  * `null`: Single request or all attempts succeeded.

## 2. Status Column Icons & Indicators

| Indicator | Code Condition | Meaning | Interaction |
| :--- | :--- | :--- | :--- |
| **Amber Arrow `↳`** | `log.isRetry` (i.e. `!isFirst` in correlation group) | **Child Request / Branching / Retry**: Rendered on any subsequent request in the same `correlationId` group. This includes both (a) failover retries after an error (422/429/499) and (b) multi-step client calls sharing the same correlation ID where both succeeded with 200 OK. | Clickable button (`title="Go to parent"`). Clicking navigates directly to the root/parent request's detail modal to view original parameters or failure reason. |
| **Green Checkmark `✓`** | `log.groupStatus === "healed" && !log.isRetry && log.status >= 400` | **Recovered by Retry**: The parent request failed, but a subsequent child retry succeeded in resolving the call. | Tooltip: `Recovered by retry`. |
| **Pill: `Healed`** | `groupStatus === "healed" && !log.isRetry` | Group had >= 1 failure followed by a success. | Shows count of retry attempts (`healedTitle`). |
| **Pill: `Failed`** | `groupStatus === "failed" && !log.isRetry` | All attempts in the correlation group failed. | Shows total attempts. |
| **Spinning Amber Circle** | `log.active` | Request currently in-flight. | Tooltip: `In progress`. |

## 3. Cache Source Column
- **`UPSTREAM`**: Direct response fetched from upstream LLM provider API.
- **`SEMANTIC`**: Response served from OmniRoute semantic vector cache.

## 4. Diagnostics & Troubleshooting Flow
When investigating an amber arrow `↳` next to `200`:
1. Click the `↳` icon to open the parent log entry.
2. Check the parent entry's status code (e.g. `429 Too Many Requests`, `408 Request Timeout`, `500 Internal Server Error`).
3. Note which upstream account/provider failed (Account column) to verify whether an account quota exhausted or an IP rate limit was encountered.
4. Verify if the combo failover strategy (e.g. `least-used`, `priority`, `round-robin`) correctly switched to the working child account.

### Fast SQLite Direct Inspection (when dashboard is inaccessible or analyzing batches):
Database path: `C:\Users\Kibe\.omniroute\storage.sqlite` (Table: `call_logs`).
```python
import sqlite3

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cur = conn.cursor()
# Inspect full chain for a correlationId
cur.execute('''
    SELECT timestamp, status, model, provider, account, error_summary, duration
    FROM call_logs
    WHERE correlation_id = ?
    ORDER BY timestamp ASC
''', (cid,))
for r in cur.fetchall():
    print(r)
conn.close()
```

### Common Upstream Failures Triggering Retries:
- **`422 Missing Google projectId`**: Antigravity Google account lacks Cloud Code onboarding or OAuth project mapping is lost. Fix: Reconnect OAuth in Providers → Antigravity.
- **`429 Antigravity upstream error`**: Quota / RPM limit reached for that specific Google account. Combo failover automatically shifts to the next pool target.
- **`499 Request aborted`**:
  * *Client Disconnect*: Client closed connection before response completed.
  * *Internal `targetTimeoutMs` Abort Cascade (Critical Trap)*: When a combo's `targetTimeoutMs` is set too low (e.g. 30s in `ag-gemini-pool-3`), complex requests such as Vision (base64 image) or heavy prompts needing 35-50s get aborted by OmniRoute's `targetTimeoutRunner` (`timeoutController.abort()`). This maps inside `chatCore.ts` (`isLocalStreamLifecycleError`) to HTTP `499 Request aborted` at exact durations ~`targetTimeoutMs` (e.g. ~30.000ms). The combo then cascades the identical heavy payload across all remaining pool accounts, creating a mass amber cascade of 499s (`failed · 5 at...`) despite accounts having full quota. Fix: Raise `targetTimeoutMs` in the combo config (e.g. 60000ms).
- **`502 Bad Gateway (chatgpt-web)`**: Upstream connection dropped abruptly by proxy (MobiProxy 4G tunnel timeout/reset) or Cloudflare edge disconnect before conversation response stream starts. OmniRoute immediately spins up child failover `↳` to the next pool account.
- **`403 Forbidden (Sentinel)`**: OpenAI web bot detection / Turnstile challenge triggered (`[403]: ChatGPT blocked the request (Sentinel)`). Combo router marks attempt failed and rotates target.
- **`Healed · N attempts` Visual Illusion**: Rows showing `<uuid> · 2 at...` or `· 3 at...` next to `healed` are NOT independent spam requests. They are a single logical caller whose first attempt failed (502/403) and subsequent child attempt succeeded (200 OK). When pool size shrinks due to stale sessions/sentinel blocks, surviving accounts (e.g. `sol-acc-12: voha03082002`) absorb multiple failovers, appearing repeatedly in log cascades.
- **All 200 OK with `↳`**: Normal behavior when an agent/client reuses the same correlation ID across multiple turns or tool calls.

## 5. Unexplained Background Traffic: Hermes Cron vs Session Context Bloat

When dashboard logs show steady request intervals (e.g. every 10m or 30m) while the user is away or after chat sessions appear broken:

### A. Diagnosing Perceived Pool Outage vs Single-Session Context Bloat
- **Symptom**: User reports "all sessions out of quota / failed after 2h", but OmniRoute logs show active requests succeeding (200 OK) at 3h, 4h, 5h.
- **Root Cause**:
  * The main interactive chat session suffered **Context Bloat** (e.g. 150k+ input tokens). Large prompts repeatedly hit upstream TPM limits (429) or gateway timeouts (504/408), causing Hermes to fail after 15 retries.
  * The upstream account pool is **NOT out of quota**. Smaller requests (7k–40k tokens) from other sessions or cron jobs continue to succeed with 200 OK in seconds.
- **Triage**: Inspect `call_logs.tokens_in`. If the failing session has `tokens_in > 100,000` while passing requests have `tokens_in < 10,000`, the issue is isolated session context bloat, fixable immediately via `/new`.

### B. Correlating Background Traffic to Cron Jobs (Zero-Disk-Scan Playbook)
1. **Identify Session Tag & Artifact**:
   Query periodic requests in OmniRoute SQLite `storage.sqlite` (table `call_logs`):
   ```sql
   SELECT timestamp, status, model, tokens_in, tokens_out, session_tag, artifact_relpath
   FROM call_logs
   WHERE session_tag LIKE 'conv_%'
   ORDER BY id DESC LIMIT 10;
   ```
2. **Inspect Request Payload Artifact**:
   Read `.omniroute/call_logs/<YYYY-MM-DD>/<artifact_relpath>.json`.
   Examine `requestBody.messages[1].content`. If it starts with:
   `[IMPORTANT: You are running as a scheduled cron job...]`
   the request is definitely generated by a Hermes cron job.
3. **Trace Cron Job ID & Executions**:
   Query `hermes/cron/executions.db` (table `executions`):
   ```sql
   SELECT job_id, started_at, finished_at, status
   FROM executions
   WHERE started_at >= '<incident_start_time>'
   ORDER BY started_at ASC;
   ```
   Match execution timestamps with OmniRoute `call_logs` timestamps.
4. **Inspect Cron Markdown Output**:
   Check `hermes/cron/output/<job_id>/` for markdown logs showing job name, schedule, prompt, and LLM responses.

### C. The `prompt` vs `no_agent: true` Watchdog Trap
- **The Trap**: Creating a cron watchdog using `prompt="Chạy lệnh terminal: python script.py ..."` without setting `no_agent: true`. Hermes treats it as an autonomous LLM agent, booting the full system prompt (~7.8k tokens), invoking `terminal` tool (Turn 1: ~34 tokens), and generating `[SILENT]` (Turn 2: ~4 tokens). This wastes ~7.9k tokens every tick (e.g. 10m) all night long.
- **The Fix**: Script watchdogs MUST be registered with `no_agent=True` and `script="<relative_or_absolute_path>"`. Deterministic Python runs offline on CPU with 0 tokens, and Hermes auto-delivers stdout verbatim without touching LLM providers.
