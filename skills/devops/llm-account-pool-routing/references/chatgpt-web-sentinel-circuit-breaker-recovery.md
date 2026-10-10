# ChatGPT-Web Pool Sentinel False-Flag, Token Revocation, and Circuit Breaker Recovery Runbook

## Context & Symptoms
- Advisor (`gpt-web-sol` on port 20129 via `consult_advisor.py`) times out (>45s) or fails with `EMPTY_RESPONSE`.
- OmniRoute logs show:
  ```text
  [ERROR] [403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.
  {"level":50,"service":"omniroute","tag":"TOKEN_REFRESH","msg":"🔴 Circuit breaker tripped for chatgpt-web: 5 consecutive failures. Blocked for 30min. Provider needs re-authentication."}
  ```
- Any caller (including `consult_advisor.py`) fails cleanly or times out because the provider-level circuit breaker in OmniRoute halts all traffic to `chatgpt-web` for 30 minutes.

---

## Root Cause Analysis: The False-Positive "Turnstile" Diagnosis

1. **Misleading Error Surface**:
   In `open-sse/executors/chatgpt-web.ts`, any HTTP 401 or 403 returned by `/backend-api/sentinel/chat-requirements/prepare` throws `SentinelBlockedError`:
   ```ts
   if (prepResp.status === 401 || prepResp.status === 403) {
     throw new SentinelBlockedError(`Sentinel /prepare blocked (HTTP ${prepResp.status})`);
   }
   ```
   This error is then transformed into: `"ChatGPT blocked the request (Sentinel/Turnstile required)"`.
   **In reality, HTTP 401 on `/prepare` almost always means `token_revoked` (account deactivated / session revoked) or `token_expired`, NOT a Cloudflare Turnstile captcha challenge.**

2. **Cascade Circuit Breaker Trip**:
   When dead or revoked accounts remain inside the `gpt-web-sol` or `chatgpt-web-pool` round-robin combo:
   - A request iterates through up to `maxGlobalAttempts` (default 8) targets.
   - If 5 consecutive failures occur across any accounts, the in-memory `_circuitBreaker['chatgpt-web']` triggers:
     `failures >= 5 -> blockedUntil = Date.now() + 30min`.
   - **Result**: Even if 20+ accounts in the pool are 100% healthy, NO request can execute or refresh tokens until the 30-minute lockout expires or the runtime restarts.

---

## Fast Triage & Recovery Protocol O(1)

### Step 1: Probe the Pool to Separate LIVE vs DEAD Accounts
Do NOT ask the user to manually solve captchas before checking the backend response payload.
Run a Node script using OmniRoute's decrypted credentials (`STORAGE_ENCRYPTION_KEY` from `server.env`):

```js
// Test each account against /session and /prepare
const prepResp = await fetch("https://chatgpt.com/backend-api/sentinel/chat-requirements/prepare", {
  method: "POST",
  headers: {
    "User-Agent": "Mozilla/5.0 ... Chrome/142.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
    "Cookie": cookie,
  },
  body: JSON.stringify({ p: "" }),
});
```

- **HTTP 200 OK**: Account is 100% **LIVE** and can answer questions immediately (no captcha needed).
- **HTTP 401 `token_revoked`**: Account has been deactivated by OpenAI (`errorCode: account_deactivated`). Must be **quarantined / deactivated in DB** (`is_active = 0`, remove from combo). Do NOT delete GPM profile unless user directs.
- **HTTP 401 `token_expired`**: Session cookie expired. Needs fresh login in GPM.

### Step 2: Clean OmniRoute Database (`storage.sqlite`)
1. In `provider_connections`:
   - Set `is_active = 1, test_status = 'active', last_error = NULL` for all verified LIVE accounts.
   - Set `is_active = 0, test_status = 'banned'` for revoked/expired accounts.
2. In `combos` (`gpt-web-sol`, `chatgpt-web-pool`, `gpt-web-luna`):
   - Rewrite `models` array so it **ONLY contains the verified LIVE connection IDs**.
   - Update `data` JSON and set `updated_at = new Date().toISOString()`.

### Step 3: Flush the In-Memory Circuit Breaker
Since `_circuitBreaker` is an in-memory object in OmniRoute, DB updates alone won't unblock an active 30-minute lockout.
- Terminate the OmniRoute Node process (`Stop-Process -Id <PID> -Force`).
- `omniroute_watchdog.ps1` will automatically detect the absence of the listener on port 20129 and launch a fresh production runtime in ~20-30 seconds.
- The new process starts with clean circuit breaker state (`failures: 0`) and reads the sanitized combo from SQLite.

### Step 4: Verify
Run the standalone advisor probe:
```bash
python D:/Taadaa/tools/consult_advisor.py "Ping! Trả lời ngắn gọn."
```
Exit code 0 and immediate streamed response confirms end-to-end recovery.
