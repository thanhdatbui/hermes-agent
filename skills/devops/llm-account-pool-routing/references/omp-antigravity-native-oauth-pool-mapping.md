# OMP Google Antigravity Native OAuth & Multi-Profile Pool Mapping

## Core Invariant & Head-to-Head Benchmark Rule
- **Fairness Invariant:** In any benchmark or head-to-head comparison between runners (such as `ag_cli.py` vs `omp_cli.py`), both tools **MUST** use identical direct native protocols.
- **NEVER** compare a native direct runner against a runner routed through a local adapter/proxy (like `omniroute`:20129) — proxy translation introduces artificial serialization/latency overhead and invalidates the benchmark.
- Both harnesses must talk directly to Google Cloud Code Assist via their respective native OAuth credentials over the same profile proxy egress.

---

## OMP OAuth Credentials & Architecture
Oh-My-Pi (OMP) includes built-in support for the `google-antigravity` provider:
- **Client ID:** `1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`
- **Client Secret:** `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` (decoded from base64 `R09DU1BYLUs1OEZXUjQ4NkxkTEoxbUxCOHNYQzR6NnFEQWY=`)
- **Token Endpoint:** `https://oauth2.googleapis.com/token`
- **Cloud Code Assist Endpoint:** `https://daily-cloudcode-pa.googleapis.com`
- **Default Project ID:** `default-gemini-project`

---

## Database Storage & Schema (`agent.db`)
OMP stores credentials in SQLite databases inside profile sandboxes:
- Canonical Paths:
  - `C:/Users/Kibe/.omp/profiles/<name>/agent/agent.db`
  - `C:/Users/Kibe/.omp/profiles/<name>/.omp/agent/agent.db` (when `USERPROFILE` / `HOME` is redirected to the profile directory).

### Table Schema: `auth_credentials`
```sql
CREATE TABLE IF NOT EXISTS auth_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    credential_type TEXT NOT NULL,
    data TEXT NOT NULL,
    disabled_cause TEXT,
    identity_key TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
```

### Record Format for `google-antigravity`:
- `provider`: `"google-antigravity"`
- `credential_type`: `"oauth"`
- `disabled_cause`: `NULL`
- `identity_key`: `"email:<active_account_email>"`
- `data`: JSON string:
  ```json
  {
    "refresh": "<refresh_token>",
    "access": "<access_token>",
    "expires": 1792545696624,
    "email": "user@gmail.com",
    "projectId": "default-gemini-project",
    "authorizedAt": 1792542097624
  }
  ```

---

## Headless Cross-Harness Token Exchange (AGY -> OMP)
When migrating or synchronizing profiles from Antigravity CLI (`agy_profiles`) to OMP without requiring interactive browser logins:
1. Extract `refresh_token` from `<profile_dir>/.gemini/oauth_creds.json`.
2. Extract active `email` from `<profile_dir>/.gemini/google_accounts.json`.
3. POST to Google's token endpoint using OMP's `client_id` and `client_secret` with `grant_type=refresh_token`.
4. Route the request through the profile's specific mobile proxy via `urllib.request.ProxyHandler` so Google associates the refresh traffic with the profile egress IP.
5. Write the resulting token payload directly into `auth_credentials` in `agent.db`.

---

## Sandbox & Fingerprint Isolation
When dispatching OMP subprocesses per profile:
- Set `USERPROFILE`, `HOME`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP` to `C:\Users\Kibe\.omp\profiles\<profile>`.
- Strip parent API keys (`GEMINI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`).
- Set `HTTPS_PROXY` and `HTTP_PROXY` to the profile's dedicated proxy.
- This ensures OMP cannot access machine-level `~/.omp/install-id` or leak host network egress.
