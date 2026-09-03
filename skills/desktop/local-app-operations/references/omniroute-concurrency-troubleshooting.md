# OmniRoute Concurrency & Crash Diagnostic Taxonomy

Reference guide for diagnosing OmniRoute / Antigravity pool errors and sizing capacity for tool-heavy workloads.

## 1. Error Signatures & Root Causes

| Error Signature | Manifestation | Root Cause | Fix |
| :--- | :--- | :--- | :--- |
| `WinError 10054` / `APIConnectionError` | "The model provider failed after retries" | Local proxy was terminated (`taskkill` / restart) while Telegram sessions had open streams. | Do not restart proxy during live heavy usage; expect in-flight stream drops if restart is required. |
| `503 ALL_TARGETS_SKIPPED` | Bot fails turn or retries with 503 | All combo targets hit `maxConcurrent` capacity (`concurrency_cap`). | Raise `maxConcurrent` per connection (e.g. to 3) and raise `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT`. |
| `503 chat_admission_busy` / `structure_limit` | Immediate 503 rejection | Process-wide structural heavy admission gate blocked request before combo dispatch. | Raise boot-time `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT` and queue timeout (`OMNIROUTE_CHAT_ADMISSION_QUEUE_MS=120000`). |
| `403 VALIDATION_REQUIRED` | Google blocks generation | Account flagged for device/browser verification. | Extract `validation_url` from raw JSON, have user verify in browser, then Reconnect. |
| `429 RESOURCE_EXHAUSTED` | Google quota exceeded | Account daily or per-minute token quota exhausted. | Combo automatically fails over to next account target in priority list. |

## 2. Rate Limit Protection (`rateLimitProtection`) vs Adaptive Limiter

- **What it is:** A local Bottleneck token bucket limiter that throttles requests based on response headers (`x-ratelimit-*`, `retry-after`).
- **Target scope:** Intended for **API Key providers** (OpenAI, Anthropic) where RPM/TPM bursts trigger hard bans.
- **OAuth Providers (Google Antigravity):** Must remain **`false` / disabled**. Google internal endpoints (`daily-cloudcode-pa.googleapis.com`) do not send standard rate-limit headers. Enabling it forces an internal 350ms Bottleneck delay per request on that connection.
- **Toggle API:**
  - `POST /api/rate-limits` with `{"connectionId": "<id>", "enabled": false}`.
  - *Pitfall:* `PATCH /api/providers/<id>` with `{"rateLimitProtection": false}` will reject with `400 Invalid request: No valid fields to update`.

## 3. Dynamic Cooldown Skip (OmniRoute vs 9Router)

- **OmniRoute behavior on 429:**
  - Parses exact reset time from Google error payload.
  - Sets `rateLimitedUntil` timestamp on the connection in RAM/DB.
  - Subsequent requests through combo pre-check `rateLimitedUntil > Date.now()` (<1ms in RAM) and **skip the exhausted account without sending any HTTP request to Google**.
  - Requests fail over seamlessly to Target 2 (Account B). When cooldown expires, Account A automatically re-enters rotation.
- **9Router behavior on 429:**
  - Lacks pre-dispatch target skip on direct routes.
  - Often sets static `9999s` demote or auto-disables the connection.
  - Can cause `404 No active credentials for provider: antigravity` if all accounts trigger error once.

## 4. Capacity Sizing Principle ("Set Highest First")

For workloads where sessions execute multi-step tool loops (emitting dozens of model requests per user turn):
1. **Do not prematurely restrict concurrency:** Caps like `maxConcurrent=1` or `2` easily bottleneck multi-session tool execution, creating artificial `ALL_TARGETS_SKIPPED` failures.
2. **Standard High Capacity Sizing:**
   - `maxConcurrent`: Set to `3` per Antigravity account.
   - `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT`: Match total pool capacity (`3 accounts × 3 = 9`).
   - `OMNIROUTE_CHAT_ADMISSION_QUEUE_MS`: `120000` (120s queue buffer).
   - `OMNIROUTE_CHAT_ADMISSION_HEALTHY_HEADROOM`: `0` (enforces deterministic queue ordering).
3. **Downward Step-down:** Only reduce concurrency if genuine upstream rate limits (Google 429) persist across all targets.

## 5. Priority vs Round-Robin Routing

- **Priority Combo:** Sends traffic to Account 1 up to its concurrency limit (`maxConcurrent=3`), maximizing upstream KV prompt caching. Once Account 1 is full, requests spill over to Account 2, then Account 3.
- **Round-Robin:** Forces equal rotation on every request, fragmenting prompt cache across multiple accounts and increasing latency.
