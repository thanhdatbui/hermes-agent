# OmniRoute Proactive Sweep Skip & Inactive Token Expiry Diagnosis

## 1. Cosmetic "Token Expired" vs True Session Invalidation

### Symptom
On the OmniRoute Dashboard (`/dashboard/usage` or `/dashboard/providers`), one or more accounts show the red warning `Token expired` with the `isActive` switch toggled OFF. Operators often suspect a Google/OAuth session revocation (`invalid_grant`, password change, or Google account lockout).

### Core Mechanism
1. In `OmniRoute/src/lib/tokenHealthCheck.ts:516`:
   ```typescript
   // Proactive sweep interval check:
   if (intervalMin <= 0) return;
   if (!conn.isActive) return; // Inactive connections are skipped!
   ```
2. When an account is toggled inactive (`isActive = false`) — whether manually, by an operator script, or after a batch deactivation — OmniRoute's background proactive refresh sweep deliberately skips it to avoid wasteful API calls to Google OAuth.
3. Google OAuth access tokens have a fixed 3,600s (1-hour) TTL. Once the hour passes, the existing access token expires. OmniRoute's UI flags it cosmetically as `Token expired`.
4. **The underlying OAuth refresh token is usually 100% alive.**

### Diagnostic Verification (O(1))
Do NOT immediately conclude the session is dead. Run an isolated probe targeting the specific connection ID:
```python
import requests

headers = {
    'Content-Type': 'application/json',
    'x-omniroute-connection-id': '<connection_id>'
}
payload = {
    'model': 'antigravity/gemini-3.8-flash-tiered',
    'messages': [{'role': 'user', 'content': 'ping'}]
}
res = requests.post('http://127.0.0.1:20129/v1/chat/completions', json=payload, headers=headers, timeout=20)
print('Status:', res.status_code) # 200 OK confirms fresh access token minted
```
If status is `200 OK`, reactive refresh (`tokenRefresh.ts`) successfully minted a new access token using the stored refresh token. Simply toggle `isActive: true` via `PUT /api/providers/<id>`.

---

## 2. Hardening: Exempting Providers via `OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS`

### Problem
Periodic background health-check sweeps can trigger rate limits or inadvertently clobber state on sensitive accounts.

### Native Solution
OmniRoute natively supports a comma-separated provider exclusion list (`tokenHealthCheck.ts:296`):
```typescript
function getHealthCheckSkipProviders(): Set<string> {
  const raw = process.env.OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS || "";
  return new Set(raw.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean));
}

// In checkConnection():
if (getHealthCheckSkipProviders().has(String(conn.provider || "").toLowerCase())) {
  return;
}
```

### Configuration Deployment
To exempt Antigravity/AGY accounts permanently:
1. In `server.env` (`%APPDATA%\omniroute\server.env`):
   ```env
   OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS=antigravity,agy
   ```
2. In supervisor watchdog (`omniroute_watchdog.ps1`):
   ```powershell
   $psi.EnvironmentVariables["OMNIROUTE_HEALTHCHECK_SKIP_PROVIDERS"] = "antigravity,agy"
   ```

### Operational Impact
- **Antigravity/AGY:** Proactive sweeps are bypassed. Tokens refresh reactively and safely on genuine user requests via `serializeRefresh()` with mutex protection.
- **Other Providers (Codex, OpenAI, Claude):** Continue to be proactively monitored and refreshed as usual.

---

## 3. UI Quota Card Visibility Controls

- On `/dashboard/usage`, clicking the eye icon (`visibility_off`) on any model row toggles its visibility on the card.
- Saved in browser `localStorage` under `omniroute_quota_visibility_overrides`.
- **Google Quota Architecture:**
  - **5-Hour Quota:** Tracked independently per model (Flash vs Pro).
  - **Weekly Quota:** Upstream Google pools Flash and Pro usage into a single shared bucket (`Gemini Models`).
  - Warning thresholds can be adjusted per model via the `Edit cutoffs` button on the card footer.
