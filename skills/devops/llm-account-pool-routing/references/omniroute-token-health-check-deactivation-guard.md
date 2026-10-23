# OmniRoute Token Health-Check & Account Deactivation Guard

## Scope
Use this reference when Antigravity/AGY (or other OAuth) accounts in OmniRoute show red "Token expired" or switch to `isActive: false` unexpectedly, and you need to distinguish between actual session death and background sweep deactivation.

## Key Operational Findings

### 1. The "Token expired" False-Positive on Inactive Accounts
- **Root Cause in `tokenHealthCheck.ts`:**
  OmniRoute runs a proactive token health check sweep every 60s. For performance and rate-limit safety, the sweep explicitly skips inactive connections:
  ```typescript
  if (!conn.isActive) return;
  ```
- **Symptom:** When an account is turned off (`isActive: false`), the background sweep stops refreshing its OAuth access token. After 3,600s (Google's standard token TTL), the access token expires.
- **UI Presentation:** The Dashboard reads `tokenExpiresAt` and displays a red `Token expired` warning, giving the false impression that the account's session was dropped or revoked upstream by Google.
- **Verification Rule:** Check `provider_connections` in SQLite (`storage.sqlite`) or `GET /api/providers`:
  * If `testStatus == 'active'` and `lastError == null` (or non-terminal error): the refresh token is completely intact.
  * Test connection validity directly via:
    `POST http://127.0.0.1:20129/api/providers/{connectionId}/test`
    Or probe via chat completion with header `x-omniroute-connection-id: {connectionId}`.
    If it returns HTTP 200, the session is 100% alive.

### 2. Guarding Antigravity Pool from Proactive Health-Check Churn
- To prevent OmniRoute's 60s background health-check sweep from probing, rotating, or deactivating Antigravity/AGY accounts:
  Configure:
  ```env
  OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS=antigravity,agy
  ```
- **Persistence Across Restarts and Watchdog:**
  1. Add to `server.env` (`%APPDATA%\omniroute\server.env`).
  2. Add to `omniroute_watchdog.ps1` (`%APPDATA%\omniroute\omniroute_watchdog.ps1` and repo `scripts/ops/omniroute_watchdog.ps1`):
     ```powershell
     $psi.EnvironmentVariables["OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS"] = "antigravity,agy"
     ```
  3. This ensures tokens are only refreshed reactively when a user request actually routes to the account, eliminating sweep churn and false deactivation.

### 3. UI Quota Visibility & Dual-Window Monitoring
- **Hiding Unwanted Models:**
  In Provider Limits dashboard card, clicking the `visibility_off` icon next to Claude/other rows hides them and persists the preference to `settings.quotaVisibility` via `PATCH /api/settings`, leaving only Gemini Flash Lite visible.
- **5h vs Weekly Window Tracking:**
  * 5h rolling quota is tracked per-model via `retrieveUserQuota`.
  * Weekly quota is tracked per model-family ("Gemini Models") via `retrieveUserQuotaSummary`.
  * When weekly quota hits zero, countdown switches to weekly reset (`Resets in Xd Yh`).
  * Per-window cutoffs can be set via `Edit cutoffs` (`QuotaCutoffModal`).
