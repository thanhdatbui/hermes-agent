# Antigravity Multi-Session Burst: TPM/RPM Quota vs max_concurrent

## Context & Incident
When multiple agent/worker sessions run concurrently (e.g. 10–17 parallel sessions firing 35–48 requests/min), OmniRoute may report mass HTTP 503 errors (`ALL_TARGETS_SKIPPED`) across combos like `omni-worker` or `ag-gemini-pool-3`.

## Root Cause Analysis
1. **Google Upstream Limits:**
   - Google Cloud Code / Antigravity enforces upstream rate limits on **TPM (Tokens Per Minute)** and **RPM (Requests Per Minute)** per account.
   - Each agent request carries tool schemas, system prompt, and turns (~35k–40k tokens / 170KB JSON).
   - 15 concurrent sessions firing at ~40 req/min generate ~1.4M TPM. Even with Pro accounts, minute-level TPM/RPM thresholds are breached.
2. **The Thundering Herd / Spillover Stampede:**
   - Account 1 hits 429 `RESOURCE_EXHAUSTED`.
   - OmniRoute combo router immediately fails over to Account 2, Account 3, etc.
   - Because all accounts are already handling parallel load from other sessions, the spillover rapidly triggers 429 on all remaining accounts within 2–3 minutes.
   - OmniRoute's resilience system trips:
     - `recordModelLockoutFailure`
     - `recordProviderCooldown` (Global Cooldown on provider `antigravity`)
   - Pre-dispatch filter skips 100% of targets -> Instant **HTTP 503 ALL_TARGETS_SKIPPED**.

## Critical Pitfall: Why Raising `max_concurrent` Does NOT Fix 429
- **Question:** "Should we increase `max_concurrent` (currently set to 5 for Pro accounts) so more requests can run?"
- **Answer: NO.**
  - `max_concurrent` is an internal OmniRoute semaphore gate (`open-sse/services/accountSemaphore.ts`) that limits in-flight requests per account.
  - Raising `max_concurrent` allows more parallel requests into the same Google account at once, which **burns the account's TPM and RPM quota faster**, accelerating 429 errors.
  - A value of `max_concurrent = 5` for Pro accounts is already optimal.

## Verified Solutions
1. **Scale the Pro Account Pool:**
   - Distribute load across more accounts (e.g. 40–50 Pro accounts instead of 22). More accounts = lower RPM/TPM per account under burst concurrency.
2. **Cross-Provider Combo Fallback:**
   - Do NOT construct combos where all tiers depend on a single upstream provider (`antigravity`).
   - Add independent fallback tiers (e.g. `chatgpt-web` with `gpt-5.6-luna-free` / `gpt-5.6-sol-high`, OpenRouter, or Codex) so that when Antigravity trips Global Cooldown, requests gracefully divert instead of collapsing with 503.
3. **Emergency Reset:**
   - Clear stalled circuit breaker/cooldown state via:
     `curl -X DELETE http://localhost:20129/api/monitoring/health`
