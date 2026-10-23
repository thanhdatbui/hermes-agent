# OmniRoute Masked Key Liveness Probe & GPM Cookie Preservation

## Context & Problem Statement
When diagnosing multi-account pools on OmniRoute (`:20129`) — such as `chatgpt-web-pool`, `codex`, or `antigravity`:
- Accounts may temporarily get marked `is_active=0` or `test_status='banned'` / `'soaking'` by OmniRoute when facing upstream Sentinel/Turnstile challenges or temporary 429 backoffs.
- An automated watchdog or operator script inspecting `GET /api/providers` attempts to verify if the account's existing session token is still valid before initiating browser-based recovery.

## The Masked Key Trap (False-Negative Token Expiry)
1. **Masked Egress**: For security, OmniRoute's `GET /api/providers` endpoint masks sensitive credentials (e.g. `apiKey` appears as `"__Secure****sTow"` or is stored encrypted in SQLite as `"enc:v1:..."`).
2. **False Validation Failure**: If a recovery script reads `c.get('apiKey')` and submits it to `POST /api/providers/validate`:
   - Upstream (e.g., OpenAI `backend-api`) rejects the masked string (returning HTTP 400 Bad Request or `EMPTY_SESSION_TOKEN`).
   - The script falsely concludes that the session token has expired, even when the underlying token in OmniRoute is 100% valid.
3. **Destructive Auto-Recovery (Unsafe Churn)**:
   - Believing the session is dead, the script opens the corresponding GPMLogin profile over CDP.
   - Calling `context.clear_cookies()` in an attempt to start a fresh login wipes working browser cookies.
   - For accounts without stored plaintext credentials in local sheets (e.g., Hotmail accounts or secondary pool reserves), the login flow halts, leaving the account genuinely logged out with `EMPTY_SESSION_TOKEN`.

## Correct Pattern: Native Provider Connection Test Endpoint
Do **NOT** validate masked keys from `/api/providers` via `/api/providers/validate`.
Instead, call OmniRoute's native internal test endpoint:
```http
POST http://127.0.0.1:20129/api/providers/{connection_id}/test
Content-Type: application/json

{}
```

### Verification Semantics:
- **`valid: true`**: OmniRoute uses its decrypted internal key to test upstream. The session is alive and functional.
  - Action: Simply re-activate the connection via DB/API without opening GPMLogin:
    ```sql
    UPDATE provider_connections
    SET is_active = 1, test_status = 'active', last_error = NULL, last_error_at = NULL, backoff_level = 0, rate_limited_until = NULL
    WHERE id = ?;
    ```
- **`valid: false`**: Upstream confirmed expired (e.g. `"ChatGPT session expired — log into chatgpt.com and copy a fresh cookie"`).
  - Action: Only now route to browser automation (GPMLogin CDP login flow), preserving existing cookies until authentication challenge explicitly demands a clean state.
