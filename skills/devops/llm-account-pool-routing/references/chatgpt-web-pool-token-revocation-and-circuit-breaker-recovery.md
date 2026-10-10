# ChatGPT-Web Pool Token Revocation & Circuit Breaker Recovery Runbook

## 1. Context & Architecture
OmniRoute (`port 20129`) hosts the `chatgpt-web` pool (used by `gpt-web-sol` and `consult_advisor.py`).
Each connection stores an encrypted cookie string in `provider_connections.api_key` (AES-256-GCM via `STORAGE_ENCRYPTION_KEY` from `AppData/Roaming/omniroute/server.env`).

## 2. Root Cause Pathology: False Captcha & Circuit Breaker Lockout
### The False Captcha Bug
When OpenAI deactivates an account or revokes its session token, calls to:
`POST https://chatgpt.com/backend-api/sentinel/chat-requirements/prepare`
return `HTTP 401` with body:
```json
{"error": {"code": "token_revoked", "message": "Encountered invalidated oauth token for user, failing request"}}
```
In legacy OmniRoute executors (`chatgpt-web.ts`), any `401` or `403` on `/prepare` was caught and thrown as:
`Sentinel /prepare blocked (HTTP 401)` -> wrapped into:
`[403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`

### The Cascading Circuit Breaker Freeze
OmniRoute's `circuitBreaker.ts` monitors consecutive provider failures:
- After **5 consecutive failures**, it trips: `🔴 Circuit breaker tripped for chatgpt-web: 5 consecutive failures. Blocked for 30min.`
- Once tripped, **all token refresh and model execution for the ENTIRE pool is blocked in RAM for 30 minutes**, even if 20+ healthy accounts exist in the pool.
- In Round-Robin combos (`gpt-web-sol`), dead accounts scattered in the list continuously trigger 5 consecutive failures, creating an infinite lockout loop.

## 3. Diagnosis & Classification Protocol
Run an offline script querying SQLite (`~/.omniroute/storage.sqlite`) and testing decrypted cookies directly:
```javascript
import { decrypt } from "./src/lib/db/encryption.ts";
// 1. Exchange cookie on /api/auth/session -> obtain accessToken
// 2. POST /backend-api/sentinel/chat-requirements/prepare with accessToken
```
Categorize accounts into 3 groups:
1. **LIVE (HTTP 200 OK):** `/prepare` returns prepare token cleanly. These accounts work immediately.
2. **TOKEN EXPIRED (`sResp.status !== 200` or no accessToken):** Account is alive, but browser cookie expired (>14-30d). Needs re-login in GPM.
3. **TOKEN REVOKED / BANNED (`token_revoked` or `account_deactivated`):** Account was disabled by OpenAI during a ban wave.

## 4. Remediation Standard (Farm Invariant)
1. **User Rule: "ban xóa DB giữ GPM"**:
   - Delete banned (`token_revoked`) rows from `provider_connections` in `storage.sqlite`.
   - DO NOT delete the profile folder in GPMLogin (keeps historical data intact).
2. **Strict Combo Lockdown**:
   - In combos (`gpt-web-sol`, `chatgpt-web-pool`, `gpt-web-luna`), filter the `models` array so it contains **ONLY verified LIVE `connectionId`s**.
   - NEVER leave unverified or inactive accounts inside the combo definition.
3. **In-Memory Circuit Breaker Reset**:
   - Kill the OmniRoute node process (`Stop-Process -Id <pid> -Force`).
   - The watchdog (`omniroute_watchdog.ps1`) restarts the process in ~20s, resetting `_circuitBreaker` in memory and loading the clean DB.
4. **Verification**:
   - Verify via focused probe: `python D:/Taadaa/tools/consult_advisor.py "test ping"`. Must return within 3s without timeout.

## 5. Hotmail Re-login via Microsoft Graph API + GPM
For expired Hotmail accounts:
### Proxy Selection (Critical)
- **DO NOT use Mobile proxies (`5101-5140`)**: High-frequency farm traffic triggers OpenAI login rate-limiting ("Chúng tôi đã gặp sự cố... vui lòng thử lại sau").
- **USE Mikrotik PPPoE proxies (`10001-10040`)**: Residential dynamic IPs bypass login rate-limiting cleanly.

### Automated OTP Retrieval
Do not ask the user for OTP. Hotmails have Microsoft Graph tokens in `D:/Taadaa/Hotmail/`:
```python
# 1. Exchange refresh_token for access_token on login.microsoftonline.com/common/oauth2/v2.0/token
# 2. Query messages: GET https://graph.microsoft.com/v1.0/me/messages?$top=3&$orderby=receivedDateTime DESC
# 3. Regex extract 6-digit OTP from subject/bodyPreview
```
### Visual Evidence Invariant (GATE 6)
- Checkpoint 1: Fill email / OTP -> screenshot pre-submit.
- Checkpoint 2: Submit -> screenshot post-submit response.
- Complete onboarding (name/age) -> verify landing on `https://chatgpt.com/` -> extract cookies -> encrypt and save to `provider_connections`.
