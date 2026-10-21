# Stale Token Reuse & False "Full Quota" UI Illusion Runbook

## 1. Symptom & The False-Green Illusion
- **Dashboard UI**:
  - Shows green status dot, `Antigravity • Pro`.
  - Quota displays **`100% left`** across all models (e.g. Gemini 3.1 Flash Lite, Claude Opus 4 6, Claude Sonnet 4 6).
  - Countdown displays `"Token expires in 0h 53m"` or similar plausible remaining lifetime.
- **Request Failure**:
  - Live model requests fail immediately with `403 Antigravity upstream error (403)` / `project_route_error`.
  - Client / Caller receives: `Error code: 403 - {'error': {'message': '... [403]: Antigravity upstream error (403)', 'type': 'permission_error', 'code': 'insufficient_quota'}}`.
  - In AGY CLI, dispatch errors with synthetic or misinterpreted `RESOURCE_EXHAUSTED (code 429)`.

## 2. Root Cause Mechanism
1. **Local Quota Computation vs Real-Time Probe**:
   - OmniRoute / 9Router dashboard cards calculate `"100% left"` by comparing recorded local token consumption against window limits. When an account has 0 recorded requests, the UI shows **100% remaining**, regardless of whether upstream Google accepts the credentials.
   - The `"Token expires in..."` badge is calculated from the local database column (`expires_at` in `provider_connections`), which may be pushed forward or stale.
2. **Reusing Stale Historical DB Rows (The `setup_agy_profile_creds` Trap)**:
   - When a Gmail account (e.g. `chuanh250416@gmail.com`) is upgraded to Google AI Pro / Gemini Pro 18M via GPM CDP, the operator or script must generate **fresh OAuth credentials**.
   - If an onboarding script merely executes:
     ```sql
     SELECT access_token, refresh_token FROM provider_connections WHERE email = ?
     ```
     it retrieves a historical connection record created weeks or months prior.
   - That historical refresh token has already been revoked or expired by Google (`invalid_grant`).
   - Copying these stale tokens into AGY CLI (`.gemini/oauth_creds.json`) and adding the connection to Pro combos (`ag-gemini-pool-3`) poisons the pool.
3. **Upstream Rejection Cascade**:
   - The stale `access_token` is rejected by Google Cloud Code with `401 Unauthenticated`.
   - OmniRoute attempts a refresh against `https://oauth2.googleapis.com/token`.
   - Google returns `HTTP 400 Bad Request: {"error": "invalid_grant", "error_description": "Bad Request"}`.
   - OmniRoute classifies this as a `project_route_error` / `403 Antigravity upstream error (403)` and marks the target failed.

## 3. Diagnostic Protocol (O(1) Verification)
Before declaring an account "Pro Active with Full Quota":
1. **Check Connection Age & Refresh Token Validity**:
   ```python
   import sqlite3, urllib.request, urllib.parse, json

   conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
   cur = conn.cursor()
   cur.execute('SELECT id, created_at, updated_at, refresh_token FROM provider_connections WHERE email = ?', (email,))
   row = cur.fetchone()
   conn.close()

   # If created_at is weeks old and no fresh OAuth flow was run, the token is stale!
   ```
2. **Execute Active Refresh Probe**:
   Directly probe Google OAuth with `grant_type=refresh_token` through the account's assigned proxy port:
   - If response is `HTTP 400 {"error": "invalid_grant"}`, the credential is dead.
   - Do NOT add to combos or AGY profiles until a fresh OAuth flow runs on the GPM profile.

## 4. Remediation Workflow
1. Open the Gmail's assigned GPM profile via GPM Local API (`19995`).
2. Run the dedicated Antigravity OAuth authorization flow to capture fresh `access_token` and `refresh_token`.
3. Update both `provider_connections` in OmniRoute SQLite and `.gemini/oauth_creds.json` in the AGY CLI profile.
4. Verify by running one single-token test probe before returning to active combo rotation.
