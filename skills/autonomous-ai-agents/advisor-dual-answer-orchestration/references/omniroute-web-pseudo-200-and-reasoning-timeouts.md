# OmniRoute ChatGPT-Web Pseudo-200 Limit & Reasoning Timeout Pathology

## 1. ChatGPT Web Pseudo-200 Rate Limit Masquerade
- **Phenomenon:** User questions why a pool with 100+ accounts (e.g. `chatgpt-web-pool` with 118 total, 89 active connections) fails with `[Error: You've hit your limit. Please try again later.]`.
- **Root Cause:**
  - Upstream ChatGPT Web interface does NOT return HTTP 429 when an account reaches its 3-hour model capacity. Instead, it responds with **HTTP 200 OK** and streams the error message as normal content text: `[Error: You've hit your limit. Please try again later.]`.
  - OmniRoute evaluates HTTP 200 with text content as a valid, successful completion.
  - Because OmniRoute sees success, combo strategies (`round-robin`, `priority`, `least-used`) do NOT invoke `failoverBeforeRetry`. The single exhausted account's error message is forwarded to the client, effectively masking all other active accounts.
- **Client/Adapter Defense:**
  - The client adapter must inspect incoming chunks or the final text for `You've hit your limit` or `rate limit`.
  - When detected, the adapter must NOT accept this as valid model output. It must treat it as an upstream 429 and either:
    1. Re-query OmniRoute with a sticky-bypass flag to force rotation to the next pool connection.
    2. Or failover directly to the next tier in the review combo (e.g. Tier 1 / Tier 2).

## 2. Reasoning Model Timeout Mismatch in Cascading Combos
- **Phenomenon:** Calling Tier 1 (`ag-opus-pool` / `codex-terra`) hits terminal timeout (`Exit 124: Command timed out after 55s/60s`) or OmniRoute internal abort.
- **Root Causes:**
  1. **OmniRoute Combo Config Flaw (`targetTimeoutMs: 8000`):**
     - In `ag-opus-pool`, `targetTimeoutMs` was configured to 8000ms (8s).
     - Reasoning models like Claude Opus 4.6 Thinking on Antigravity require 25s–45s TTFT (Time-To-First-Token) to emit thinking tokens. An 8s target timeout causes early aborts before generation begins.
     - Target timeout for deep-reasoning pools must be at least 60000ms (60s).
  2. **Cumulative Waterfall Timeout in Foreground Commands:**
     - The coordinator foreground terminal guard strictly limits execution to <= 60s.
     - When Tier 0 (`chatgpt-web-pool`) takes 10–15s to deliver pseudo-200 limit text, and failover shifts to Tier 1 (`ag-opus-pool`) which takes 35–45s to think, total wall time reaches 50–60s+, triggering the foreground timeout guard.
- **Remediation Pattern:**
  - **Early Fail-Fast on Tier 0:** Socket read timeout for Tier 0 should be tightly bounded (e.g. <= 12s). If pseudo-200 or stall occurs, abort immediately so the caller retains 45s+ budget for Tier 1 reasoning.
  - **Always Stream:** Always invoke with `stream: true` (SSE) and handle keepalive packets (`chatcmpl-keepalive`) to keep the socket alive during long reasoning preambles.

## 3. Permanent OmniRoute Engine Fix & Database Calibration (Applied)
- **Engine Patch (`open-sse/services/combo/validateQuality.ts`):**
  - **Streaming:** In `isStreamingUpstreamError()`, detect chunks where `delta.content` starts with `[Error: ` (e.g. `[Error: You've hit your limit. Please try again later.]`). Returning `true` triggers immediate stream abort and engages `failoverBeforeRetry` to rotate to the next pool connection.
  - **Non-streaming:** In `validateResponseQuality()`, check if `content` starts with `[Error: `. If so, return `{ valid: false, reason: "upstream error in choice content" }` so the combo engine rejects the pseudo-200 and advances to the next account or tier.
  - **Regression Test:** `tests/unit/validate-response-quality-synthetic-error.test.ts` covers both streaming chunk and non-streaming response quality invalidation.
- **SQLite Database Calibration (`C:/Users/Kibe/.omniroute/storage.sqlite`):**
  - `ag-opus-pool`: `targetTimeoutMs` raised from `8000` (8s) to `60000` (60s), ensuring reasoning models have sufficient TTFT budget.
  - `review` combo: `targetTimeoutMs` raised from `30000` (30s) to `60000` (60s).
  - *Pitfall on REST PUT `/api/combos/<id>`:* May fail with `COMBO_004` (name collision) if legacy rows exist with the same name. Safe fallback is a direct read-modify-write on `combos.data` JSON blob in `storage.sqlite` followed by `/api/restart`.
- **Runtime Verification:**
  - Restart service via POST `http://127.0.0.1:20129/api/restart`.
  - Live probe against `http://127.0.0.1:20129/v1/chat/completions` with model `review` confirms failover bypasses limit accounts and resolves successfully (e.g. `gpt-5.6-sol-high` responding in ~37s).

## 4. Multi-Account Pool Waterfall Latency & Client Abort Pathology
- **User Question:** "Why does a 90+ account pool hit limits instead of rotating to another account? Is rotation broken / uneven?" ("Vô lí 94 acc k thể hết nhanh v đc. Hay cơ chế xoay acc ngu, có xoay đều k")
- **Reality from `call_logs` in `storage.sqlite`:**
  - OmniRoute **DOES** rotate strictly evenly across accounts via atomic in-memory `rrCounters`: log entries show `[502]: You've hit your limit` on account 1 (`10c4332c` - voha, 22.6s), immediately rotating to account 3 (`0b1deb07` - buitrang, 18.0s).
  - Crucially, healthy accounts deeper in the pool **DO succeed normally**: immediately after accounts 1 and 3 failed, rotation reached account 5 (`199ffdf4` - chuloan) and account 6 (`12ca9dc9`), both succeeding with `Status 200`, `None` error, and 13.5s–19.5s latency. The pool is NOT depleted.
- **The Waterfall Trap:**
  - Because ChatGPT Web takes 15–23s of keepalive streaming per exhausted account to deliver the limit message, rotating through just 2 exhausted accounts incurs $22.6s + 18.0s = 40.6s$ cumulative delay.
  - Callers with bounded socket timeouts (e.g. `advisor_consult` timeout 15s, client-side 30s/45s limits) abort (`[499] Request aborted`) *before* the router reaches live accounts deeper in the pool.
  - **Missing Immediate Cooldown Lockout:** When an account hits `[Error: You've hit your limit]`, if it is not immediately locked out in-memory (`rate_limited_until = now + 2h` or `isModelLocked`), the round-robin counter re-visits it on the next turn, re-incurring the 20s hold penalty.
- **Diagnostic Runbook & Verification Query:**
  - Inspect exact account rotation via SQLite:
    ```sql
    SELECT timestamp, connection_id, model, error_summary, duration
    FROM call_logs
    WHERE model LIKE '%sol%' OR requested_model LIKE '%chatgpt%'
    ORDER BY rowid DESC LIMIT 15;
    ```
- **Remediation & Fail-Fast Rule:**
  - If the primary web pool does not produce valid tokens within 15–20s, do not allow the client to hang on successive 14s–22s pseudo-200 rotations.
  - Fail fast and engage Tier 2 (`ag-gemini-pool-3`), which responds in <2s, avoiding hanging/frozen sessions while clearly labeling the fallback.
  - Ensure detected `[Error: ` accounts trigger immediate cooldown exclusion in OmniRoute so subsequent turns skip them in $O(1)$ without paying the 20s hold penalty.

## 5. Permanent Cooldown Flag Engine Wiring & Runtime Activation (Applied)
- **The Missing Link in Combo Routing:**
  - Previously, when `validateResponseQuality` flagged `[Error: You've hit your limit...]` as invalid (returning 502), `handleRoundRobinCombo` and `handleComboChatInner` broke to the next model in rotation for the *current* request, but NEVER recorded a cooldown on `target.connectionId`.
  - As a result, the next request's round-robin rotation re-probed the exhausted account, paying another 15s–23s keepalive hold penalty.
- **Engine Patch (`open-sse/services/combo.ts`):**
  - In `handleRoundRobinCombo` (around line 3465) and `handleComboChatInner` (around line 1750), right after pushing the 502 quality error outcome:
    ```typescript
    if (
      resilienceSettings.providerCooldown.enabled &&
      provider &&
      provider !== "unknown"
    ) {
      recordProviderCooldown(
        provider,
        target.connectionId ?? undefined,
        resilienceSettings
      );
    }
    ```
  - This ensures `providerCooldownTracker` stores a cooldown record for `chatgpt-web:<connectionId>`, causing `isProviderInCooldown(provider, target.connectionId, resilienceSettings)` to return `true` on subsequent requests and skip the account in $O(1)$ before dispatch.
- **SQLite Database Calibration (`C:/Users/Kibe/.omniroute/storage.sqlite`):**
  - In table `key_value` row `resilienceSettings`:
    ```json
    "providerCooldown": {
      "enabled": true,
      "minRetryCooldownMs": 300000,
      "maxRetryCooldownMs": 7200000
    }
    ```
  - Set `minRetryCooldownMs = 300000` (5 minutes) and `maxRetryCooldownMs = 7200000` (2 hours), matching the OpenAI 3-hour rolling limit window.
- **Verification Runbook:**
  - Run typecheck: `npm run typecheck:core` (0 errors).
  - Run unit test: `node --import tsx/esm --test tests/unit/combo-round-robin-streaming-lock-3811.test.ts` (PASS).
  - Restart service: `POST http://127.0.0.1:20129/api/restart`.
  - Live probe: `review` responds with `SOL_ONLINE` in 2–3s with no hanging waterfall delay.
