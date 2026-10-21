# Dual-Pool (OmniRoute + AGY CLI) OAuth Token Desync & 429 Quota Triage

Runbook for diagnosing Antigravity / Gemini Pro accounts failing across the dual execution pool: OmniRoute (`:20129`) vs native AGY CLI sandboxes (`D:/Taadaa/agy_profiles`).

## 1. Symptom & Illusion of Account Checkpoint

When an account (e.g. `chuanh250416@gmail.com` / `acc_24`) stops serving requests:
- **OmniRoute log**: Returns `HTTP 403 [403]: Antigravity upstream error (403)` classified as `project_route_error`. Operators frequently misdiagnose this as Google triggering security checkpoints, SMS verification, or account deactivation.
- **AGY CLI pool status**: Profile shows `COOLDOWN` with reason `AGY_ERROR: {"short_error":"RESOURCE_EXHAUSTED (code 429): Individual quota reached. Please upgrade your plan"}`.

## 2. Root Cause Analysis

### A. Dual-Pool Refresh Token Invalidation (`invalid_grant`)
- When an account is registered in both OmniRoute (`storage.sqlite` -> `provider_connections`) and AGY CLI (`acc_XX/.gemini/oauth_creds.json`), both stores initially share the same OAuth tokens.
- When AGY CLI (`agy.exe`) executes requests, it independently refreshes the token against Google OAuth (`https://oauth2.googleapis.com/token`) upon expiry and updates its local `oauth_creds.json`.
- Google's OAuth 2.0 implementation supersedes or revokes the prior refresh token in that family.
- Consequently, OmniRoute's stored refresh token becomes stale. When OmniRoute attempts token refresh, Google rejects it with:
  ```json
  HTTP 400 Bad Request
  {"error": "invalid_grant", "error_description": "Bad Request"}
  ```
- Because `open-sse/services/errorClassifier.ts` groups non-deactivation 403s on Antigravity as `PROJECT_ROUTE_ERROR`, the failure surfaces cryptically as `[403]: Antigravity upstream error (403)` rather than clearly displaying an OAuth invalidation.

### B. 429 Quota Exhaustion (Individual Quota Reached)
- In the native AGY CLI pool, Google Cloud Code / Gemini Pro enforces a rolling quota per individual account.
- When an account exceeds its request/token quota, Google returns `RESOURCE_EXHAUSTED (code 429): Individual quota reached`.
- `D:/Taadaa/tools/ag_cli.py` automatically catches this error and places the profile in a 1800s (30-minute) cooldown to allow the rolling window to reset. This is strictly a rate limit / quota exhaustion, NOT a security checkpoint.

## 3. Triage Protocol (3-Step Verification)

1. **Verify Master Account Status (Rule out Checkpoint/Die):**
   - Check `D:/OneDrive/TaadaaData/kibe/master_gmail_manager.xlsx`.
   - If the email is present in `Master_All` and marked `LIVE`, Google has **NOT** suspended or forced a security challenge on the account.

2. **Inspect AGY Pool Cooldown Reason:**
   - Run `python D:/Taadaa/tools/ag_cli.py pool-status`.
   - Inspect `D:/Taadaa/agy_profiles/pool_state.json`. If `reason` contains `RESOURCE_EXHAUSTED (code 429)`, the account is alive but temporarily rate-limited. Wait for cooldown expiration.

3. **Check Token SHA-256 Consistency:**
   - Hash the `refresh_token` in OmniRoute (`provider_connections`) and compare against the `refresh_token` in `D:/Taadaa/agy_profiles/acc_XX/.gemini/oauth_creds.json`.
   - If the hashes differ, test the OmniRoute refresh token directly against `https://oauth2.googleapis.com/token`. An `invalid_grant` response confirms token desync between the dual pools.

## 4. Remediation

- **For 429 Quota Exhaustion:** Allow the cooldown window to elapse (~15-30 mins) or allow `ag_cli.py` to route to other available profiles in the pool.
- **For `invalid_grant` Desync:** Re-sync the newly issued tokens from the active AGY CLI sandbox back into OmniRoute's `provider_connections` table, or re-authenticate via OAuth flow to issue a synchronized credential set to both targets.
