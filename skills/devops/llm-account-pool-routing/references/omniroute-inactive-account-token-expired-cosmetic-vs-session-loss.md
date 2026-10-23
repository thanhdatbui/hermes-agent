# OmniRoute Inactive Account "Token Expired" Cosmetic vs Session Loss

## Context
When multi-account LLM pools on OmniRoute (port 20129) show connections with red `Token expired` and `toggle_off` (deactivated `isActive: false`), operators or automated checkers often conclude the account has suffered "văng session" (Google OAuth revocation, forced logout, password change).

## Root Cause & Architecture Mechanics

1. **Selective Background Health-Check Sweep:**
   - In `src/lib/tokenHealthCheck.ts`:
     ```ts
     const oauthConns = (connections || []).filter((c) => c.isActive && c.refreshToken);
     ```
   - OmniRoute intentionally skips proactive OAuth refresh sweeps for any connection with `isActive: false`.
2. **Cosmetic Expiry on Inactive Accounts:**
   - Because inactive accounts are not refreshed, their 1-hour Google OAuth `access_token` naturally elapses.
   - UI components (`QuotaCardHeader.tsx`, `ConnectionRow.tsx`) compute countdown from `tokenExpiresAt || expiresAt`. When past, it renders `Token expired` in red text.
   - **Crucial Distinction:** `Token expired` on the card indicates an expired temporary access token, NOT a dead refresh token or lost session.
3. **Audit Log Evidence:**
   - Deactivations often originate from programmatic loops or batch scripts (e.g., following rate-limit 429 isolation or pool rotation) calling `PATCH /api/providers` or `PUT /api/providers/{id}`.
   - Audit log in `storage.sqlite` records: `action: "provider.credentials.updated"`, `actor: "admin"`, `changedFields: ["isActive"]`.

## Verification & Recovery Protocol

1. **Verify Database Location (Windows Host):**
   - Active database: `C:\Users\Kibe\.omniroute\storage.sqlite` (~1.5GB).
   - Inactive/skeleton database: `C:\Users\Kibe\AppData\Roaming\omniroute\storage.sqlite` (do NOT use for live status).
2. **Differentiate True Expiry from Inactive Staleness:**
   - Check `testStatus`:
     - If `testStatus == 'active'` and `isActive == false`: Highly likely healthy session with stale access token.
     - If `testStatus == 'expired'` and `lastErrorType in ('invalid_grant', 'unrecoverable_refresh_error', 'unauthorized')`: Genuine session loss (requires re-auth / GPM QR / SMS).
3. **Zero-Guess Live Probe:**
   - Run a test probe directly: `POST http://127.0.0.1:20129/api/providers/{id}/test` (timeout: 15s).
   - Expected healthy response: `{"valid": true, "refreshed": true, ...}`.
   - Or send an isolated chat completion with header `x-omniroute-connection-id: <id>`: returns HTTP 200 OK with fresh completion.
4. **Reactivation:**
   - Once verified healthy, restore routing via `PUT http://127.0.0.1:20129/api/providers/{id}` with body `{"isActive": true}`.
   - The next health-check sweep will resume automatic token rotation.

## UI Quota Visibility Steering
- To monitor only specific models (e.g., track only Gemini Flash and hide Claude in an Antigravity card), click the eye-slash icon (`visibility_off`) on the model row in `/dashboard/usage`.
- This persists to `settings.quotaVisibility` without affecting underlying combo execution.
