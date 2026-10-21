# Antigravity Account Onboarding: OmniRoute Combos & AGY CLI Sandboxing

SOP for onboarding and permanently anchoring Google Antigravity OAuth accounts into both OmniRoute (`:20129`) combos and the AGY Headless CLI multi-profile pool.

## 1. OmniRoute Connection Post-OAuth Alignment

When an account is authenticated via `/api/oauth/antigravity/authorize` and code exchange:
1. **Verify Connection in SQLite / API:**
   - Query `GET /api/providers` or `SELECT id, email, access_token, refresh_token FROM provider_connections WHERE provider = 'antigravity'`.
2. **Explicit Proxy Binding (Crucial - Prevent Direct IP Leak):**
   - OmniRoute does NOT fail-closed if `proxy_enabled = 1` but `proxy_assignments` is missing; it will silently leak direct residential IP.
   - Assign dedicated 4G Mobi egress proxy via:
     ```python
     requests.put(
         "http://127.0.0.1:20129/api/settings/proxies/assignments",
         json={"scope": "account", "scopeId": connection_id, "proxyId": proxy_id},
         timeout=10,
     )
     ```
3. **Align Concurrency & Rate Limits:**
   - For Pro tier (`g1-pro-tier`): `PATCH /api/providers/<id>` with `{"maxConcurrent": 8}`.
   - Enable rate-limit protection: `POST /api/rate-limits` with `{"connectionId": "<id>", "enabled": true}`.
   - Sync upstream models: `POST /api/providers/<id>/sync-models`.

## 2. Anchoring into OmniRoute Combos

Add target definitions to the 4 core Antigravity combos via `PUT /api/combos/<combo_id>`:
- **`ag-gemini-pool-3`** (`22975610-b162-41b9-b6b3-30be076265bd`):
  - Model: `antigravity/gemini-3.8-flash-tiered`
  - Strategy: `least-used`
- **`ag-sonnet`** (`d8d1affe-94a6-4fa5-ab53-ff5e5ce6adea`):
  - Model: `antigravity/claude-sonnet-4-6`
  - Strategy: `least-used`
- **`ag-opus-pool`** (`combo-ag-opus-pool`) & **`ag-opus`** (`308174c9-2821-4ac3-ae93-1c487364d830`):
  - Model: `antigravity/claude-opus-4-6-thinking`
  - Strategy: `reset-aware` / `least-used`

*Canary verification:*
Always execute a minimal non-cached test call through `POST /v1/chat/completions` with `model: "ag-gemini-pool-3"` verifying `status_code == 200` and returned completion.

## 3. Purge Protection Safeguard

To ensure persistent accounts (e.g. VIP / user-owned accounts) are never evicted by automated cleanup/purge jobs:
- In `omniroute_purge_helper.py`, enforce an explicit skip guard in `purge_account(email, ...)`:
  ```python
  if (email or "").lower().strip() in PROTECTED_ACCOUNTS:
      logger.info("[PURGE] Account %s is protected from purge; skipping", email)
      return
  ```

## 4. AGY Headless CLI Profile Sandboxing

To provision a corresponding AGY CLI profile under `D:/Taadaa/agy_profiles/`:
1. **Initialize Sandbox:**
   ```bash
   python D:/Taadaa/tools/ag_cli.py init-profile <profile_name> --proxy "<proxy_url>"
   ```
   This generates isolated `AppData/Roaming`, `AppData/Local`, `Temp`, `installation_id`, and registers into `profiles_config.json`.
2. **Populate Credentials & Settings in `<profile_dir>/.gemini/`:**
   - `google_accounts.json`: `{"active": "<email>", "old": []}`
   - `oauth_creds.json`:
     ```json
     {
       "access_token": "<token_from_omniroute>",
       "refresh_token": "<refresh_token_from_omniroute>",
       "id_token": null,
       "token_type": "Bearer",
       "scope": "<scope_from_omniroute>"
     }
     ```
   - `settings.json`: `{"security": {"auth": {"selectedType": "oauth-personal"}}}`
   - `projects.json`: standard project mapping dictionary.
   - `state.json`: `{"startupWarningCounts": {"home-directory": 1}, "tipsShown": 2}`
3. **Verify Pool Status & Smoke Test:**
   - `python D:/Taadaa/tools/ag_cli.py pool-status` (check status `READY`).
   - `python D:/Taadaa/tools/ag_cli.py ask "ping" --profile <profile_name> --timeout 40` (verify execution returns non-empty output with exit code 0).
