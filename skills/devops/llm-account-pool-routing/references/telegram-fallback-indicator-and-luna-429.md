# Telegram Fallback Indicator & Luna 429 Diagnostics

## Why this happens
When users report seeing "waiting on gpt-5.6-luna" or "waiting 5.6 luna" in Telegram status messages, it is not a manual model change or stuck prompt, but the automated Hermes fallback cascade in action.

## Diagnostic Flow
1. **Primary Provider Stutter**:
   - The primary model (e.g. `omni-worker` on OmniRoute `:20129`) experiences a transient failure, connection reset, or upstream timeout.
2. **Fallback Cascade Activation**:
   - Hermes gateway activates `fallback_providers` in sequence:
     `primary (omni-worker) → fallback (custom:9router/gpt-5.6-luna) → secondary (ag-gemini-pool-3)`
   - The Telegram platform adapter streams the active model target in the typing status message (`waiting on gpt-5.6-luna`, showing latency/duration like `5.6s`).
3. **Upstream Luna Rate-Limit (HTTP 429)**:
   - When 9Router `:20128` responds with HTTP 429 (Rate Limit / Quota) on `gpt-5.6-luna`, Hermes records:
     `API call failed (attempt 1/6) error_type=RateLimitError ... model=gpt-5.6-luna summary=HTTP 429`
   - Hermes immediately cascades to the next configured fallback (`ag-gemini-pool-3` on OmniRoute).
4. **Verification via Logs**:
   - Inspect `agent.log` for lines matching:
     - `Fallback activated: <primary> → gpt-5.6-luna (custom:9router)`
     - `RateLimitError ... model=gpt-5.6-luna`
     - `Fallback activated: gpt-5.6-luna → ag-gemini-pool-3`
   - This proves the transient failure resolved automatically without manual intervention.
