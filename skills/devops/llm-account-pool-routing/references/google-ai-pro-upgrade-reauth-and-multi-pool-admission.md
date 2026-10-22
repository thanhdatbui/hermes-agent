# Google AI Pro Upgrade Re-auth, Validation Bypass & Multi-Pool Admission

## Problem Context
When an existing Google account in the farm/pool is upgraded to **Google AI Pro** (e.g. via SumiStore Google One 18M link or Family invitation), two major failure modes occur if not handled correctly:
1. **Stale Token Quota Lock (429 RESOURCE_EXHAUSTED):** The account has Pro in the web UI, but Antigravity CLI and OmniRoute still throw `Individual quota reached` because existing OAuth tokens minted prior to the upgrade remain bound to Free/Starter quota.
2. **IAP QR Code Validation Wall (403 PERMISSION_DENIED):** Upstream Google API (`daily-cloudcode-pa.googleapis.com`) suddenly halts requests with:
   `403 PERMISSION_DENIED: "Verify your account to continue." (reason: "VALIDATION_REQUIRED")`
   redirecting to `challenge/iap/qrcode`. Attempting to scan this QR code with arbitrary phones often fails (`500 Error`) because the device token is bound to browser session and IP.

---

## Proven Solution & End-to-End Workflow

### Step 1: Web Activation & First-Run Warmup
1. Open the GPM profile on CDP (skip proxy check if necessary for local browser control).
2. Navigate to the activation link, click **"Kích hoạt gói"**, and verify the **Celebration Page** (`https://one.google.com/celebration...`) confirms:
   - "Bạn là thành viên gói Google AI Pro".
   - Storage shows 5 TB or 2 TB.
3. **Mandatory First-Run Warmup:** Navigate to `https://gemini.google.com/`. Verify model dropdown displays `3.1 Pro` (Advanced) and `4 Argon`. Click `3.1 Pro` and send at least 1 prompt to accept terms of service and register the account in Google's internal AI entitlement registry.

---

### Step 2: Bypassing the 403 Validation Wall via Direct OAuth Re-auth
**DO NOT battle the `challenge/iap/qrcode` screen manually.**
Instead, initiate a clean Antigravity OAuth Consent flow directly inside the logged-in GPM profile:
1. Call OmniRoute authorize endpoint:
   `http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http%3A%2F%2F127.0.0.1%3A20129%2Fcallback`
2. In Playwright connected over CDP:
   - Navigate to `authUrl`.
   - On Account Chooser: select the target email automatically.
   - On TOTP prompt: read TOTP secret from `master_gmail_manager.xlsx` and auto-fill using `pyotp`.
   - On Google Security Warning ("Đảm bảo rằng bạn đã tải ứng dụng này xuống từ Google"): click `button:has-text("Đăng nhập")`.
   - On Consent: click `Allow` / `Cho phép`.
   - Capture `code` parameter on redirect to `/callback`.
3. Post `code` to `/callback` or let OmniRoute complete the exchange:
   - OmniRoute receives fresh tokens and updates `provider_connections` with `HTTP 200`.
   - **Outcome:** The fresh OAuth consent completely supersedes and clears the `VALIDATION_REQUIRED` checkpoint.

---

### Step 3: Multi-Pool Admission Contract (All 3 Combos)
A Google AI Pro account provides entitlements for **both Gemini Pro and Claude Sonnet/Opus models**. It must be added to all 3 primary combos in `C:\Users\Kibe\.omniroute\storage.sqlite`:

1. **`ag-gemini-pool-3`:**
   ```json
   {
     "id": "ag-gemini-pool-3-model-<N>-antigravity-gemini-3-8-flash-tiered-<CONN_ID>",
     "kind": "model",
     "model": "antigravity/gemini-3.8-flash-tiered",
     "providerId": "antigravity",
     "connectionId": "<CONN_ID>",
     "weight": 0,
     "label": "<EMAIL>"
   }
   ```
2. **`ag-sonnet`:**
   ```json
   {
     "id": "ag-claude-model-<NAME>-<CONN_ID_PREFIX>",
     "kind": "model",
     "model": "antigravity/claude-sonnet-4-6",
     "providerId": "antigravity",
     "connectionId": "<CONN_ID>",
     "weight": 0,
     "label": "sonnet: <EMAIL>"
   }
   ```
3. **`ag-opus`:**
   ```json
   {
     "id": "ag-opus-model-<NAME>-<CONN_ID_PREFIX>",
     "kind": "model",
     "model": "antigravity/claude-opus-4-6-thinking",
     "providerId": "antigravity",
     "connectionId": "<CONN_ID>",
     "weight": 0,
     "label": "opus: <EMAIL>"
   }
   ```
*Note: `omni-worker` references `ag-gemini-pool-3` and `ag-sonnet`, so updating those two automatically benefits `omni-worker`.*

---

### Step 4: AGY CLI Sandbox Provisioning
For headless Antigravity CLI execution (`D:/Taadaa/agy_profiles/acc_XX`):
Ensure all **5 mandatory files** are written via `D:/Taadaa/tools/setup_agy_profile_creds.py`:
- `.gemini/google_accounts.json` (`{"active": "<EMAIL>", "old": []}`) - **CRITICAL:** Without this file, `agy.exe` ignores sandbox credentials and falls back to host `C:\Users\Kibe\.gemini`.
- `.gemini/oauth_creds.json` (Tokens from `provider_connections`).
- `.gemini/settings.json` (`{"security": {"auth": {"selectedType": "oauth-personal"}}}`).
- `.gemini/projects.json` (Local directory project mappings).
- `.gemini/state.json` (Startup warnings & tips state).
- Update `profiles_config.json` with matching proxy (`http://mobi<PORT>:TaadaaMobi%232026%21@test.taadaa.click:<PORT>`).

---

### Step 5: Verification
Run a forced test through OmniRoute:
```python
req = urllib.request.Request(
    'http://127.0.0.1:20129/v1/chat/completions',
    data=json.dumps({
        'model': 'antigravity/gemini-3.8-flash-tiered',
        'messages': [{'role': 'user', 'content': 'ping'}],
        'forcedConnectionId': '<CONN_ID>'
    }).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer env-key'}
)
```
Verify `HTTP 200 OK` and inspect `omniroute-stdout.log` to confirm no 403 or fallback occurs.
