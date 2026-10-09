# Antigravity Pro Pool Migration and 1:1 Proxy Attachment Runbook

## Overview
When an account in the Taadaa farm is upgraded to Google AI Pro (or when onboarding a new Pro account), follow this contract to safely attach proxies, update metadata in OmniRoute, migrate combo memberships, and verify live routing.

---

## 1. Upstream Google Entitlement Verification (loadCodeAssist)
Before altering pool memberships, verify the account's live entitlement directly with Google:
- **Endpoint**: `POST https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist`
- **Headers**:
  - `Authorization: Bearer <decrypted_access_token>`
  - `User-Agent: antigravity/ide/1.0.0 darwin/arm64`
  - `Content-Type: application/json`
- **Body**: `{"metadata":{"ideType":"ANTIGRAVITY"}}`

### Target Response Signature for Pro:
```json
{
  "currentTier": { "id": "free-tier" },
  "paidTier": {
    "id": "g1-pro-tier",
    "name": "Google AI Pro"
  },
  "allowedTiers": [
    { "id": "free-tier", "isDefault": true },
    { "id": "standard-tier", "userDefinedCloudaicompanionProject": true }
  ],
  "ineligibleTiers": []
}
```
*Criteria*:
1. `paidTier.id == "g1-pro-tier"` (confirms Google recognized the Pro subscription).
2. `ineligibleTiers` MUST NOT contain `reasonCode: "VALIDATION_REQUIRED"`.

---

## 2. 1:1 Farm Proxy Attachment & Leak-Prevention
Each account on the farm corresponds to a physical device (S7) and a dedicated mobile proxy port:
1. **Source of Truth Mapping**:
   - Check `gmail_clean_v2.xlsx` (sheet `Gmail Accounts`) for `số máy` (e.g. Máy 55, Máy 44).
   - Match with `PROXYgandienthoai.xlsx` for the exact proxy URL (e.g. `test.taadaa.click:5121:mobi21:TaadaaMobi#2026!`).
2. **OmniRoute DB Configuration** (`C:/Users/Kibe/.omniroute/storage.sqlite`):
   - Table `proxy_registry`: ensure the proxy is registered and marked `status = 'active'`.
   - Table `proxy_assignments`: must contain an assignment with:
     - `scope = 'account'`
     - `scope_id = <connection_id>`
     - `proxy_id = <proxy_registry.id>`
   - Table `provider_connections`: ensure `proxy_enabled = 1`.
3. **Pre-flight Proxy Connectivity Test**:
   - Probe `https://api.ipify.org?format=json` through the proxy before enabling traffic.
   - Confirm external IP matches the designated mobile carrier subnet (never localhost or public machine IP).

---

## 3. Database Metadata Update (`provider_connections`)
Update connection fields in `storage.sqlite` to reflect Pro status:
- `provider_specific_data`:
  - `tier`: `"g1-pro-tier"`
  - `subscriptionTier`: `"Google AI Pro"`
  - `plan`: `"Pro"`
- `max_concurrent`: `2` (standard concurrency cap for Pro accounts to avoid triggering Google upstream 429 semaphore congestion).
- `priority`: assign appropriate Pro priority (typically 18–20, higher priority than Free tier).

---

## 4. Combo Pool Migration Contract
Accounts must be explicitly moved from Free combos into Pro combos:

1. **Add to Pro Combos**:
   - **`ag-gemini-pool-3`** (Gemini 3.8 Flash Tiered Pro Pool):
     - Model: `antigravity/gemini-3.8-flash-tiered`
     - Label: `pro-<email_prefix>`
   - **`ag-gemini-pool-3-37`** (Gemini 3.7 Flash Tiered Pro Pool):
     - Model: `antigravity/gemini-3.7-flash-tiered`
     - Label: `pro-<email_prefix>`
   - **`ag-opus-pool` & `ag-opus-78`** (Claude Opus 4.6 Thinking Pro Pool):
     - Model: `antigravity/claude-opus-4-6-thinking`
     - Label: `opus-pool-<N>`
   - **`ag-sonnet`** (Claude Sonnet 4.6): verify account is included.

2. **Purge from Free Combos**:
   - Remove the connection ID from **`ag-gemini-free-pool`** and **`ag-gemini-free-pool-37`**.
   - *Reason*: Leaving Pro accounts in Free pools leads to inefficient quota utilization and concurrency lockouts on lower-priority traffic.

3. **Umbrella Combo Propagation**:
   - `omni-worker` references `ag-gemini-pool-3` (Tier 1) and `ag-gemini-pool-3-37` (Tier 1b). Changes to the child combos immediately take effect in `omni-worker` within the 5-second `TTLCache` cycle.

---

## 5. Verification Probe
After updating SQLite combos and connections:
1. Dispatch a canary prompt to the Pro combo endpoint:
   - `POST http://127.0.0.1:20129/v1/chat/completions`
   - Model: `ag-gemini-pool-3`
   - Body: `{"messages": [{"role": "user", "content": "ping"}]}`
2. Check `call_logs` table in `storage.sqlite`:
   - Verify `status == 200`
   - Confirm `model == "gemini-3.8-flash-tiered"`
   - Confirm `error_summary IS NULL`
