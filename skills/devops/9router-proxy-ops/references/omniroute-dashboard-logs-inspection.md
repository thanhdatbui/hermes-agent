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
- **`499 Request aborted`**: Client disconnected or cancelled before generation completed.
- **`502 Bad Gateway (chatgpt-web)`**: Upstream connection dropped abruptly by proxy (MobiProxy 4G tunnel timeout/reset) or Cloudflare edge disconnect before conversation response stream starts. OmniRoute immediately spins up child failover `↳` to the next pool account.
- **`403 Forbidden (Sentinel)`**: OpenAI web bot detection / Turnstile challenge triggered (`[403]: ChatGPT blocked the request (Sentinel)`). Combo router marks attempt failed and rotates target.
- **`Healed · N attempts` Visual Illusion**: Rows showing `<uuid> · 2 at...` or `· 3 at...` next to `healed` are NOT independent spam requests. They are a single logical caller whose first attempt failed (502/403) and subsequent child attempt succeeded (200 OK). When pool size shrinks due to stale sessions/sentinel blocks, surviving accounts (e.g. `sol-acc-12: voha03082002`) absorb multiple failovers, appearing repeatedly in log cascades.
- **All 200 OK with `↳`**: Normal behavior when an agent/client reuses the same correlation ID across multiple turns or tool calls.
