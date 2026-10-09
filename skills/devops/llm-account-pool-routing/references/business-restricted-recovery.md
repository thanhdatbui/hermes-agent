# Antigravity Business/Restricted Recovery — Evidence-First Runbook

## Classification

Do not treat the Dashboard `plan: Business` label as proof of a paid Business account. Inspect `providerSpecificData`:

- Restricted: `subscriptionTier` contains `Restricted`, or `tier == standard-tier`, or `plan == Business`.
- Starter: `tier == free-tier`, `subscriptionTier == Antigravity Starter Quota`.
- Pro: `tier == g1-pro-tier`, `subscriptionTier == Google AI Pro`.

The Restricted/standard-tier state is an upstream entitlement/project-provisioning state. Rewriting local metadata to Starter only changes presentation and can make the diagnosis worse.

## Upstream Google API Signature (loadCodeAssist)

To verify whether an account is clean Starter or stuck in `VALIDATION_REQUIRED`, inspect the upstream response directly:
- **Endpoint**: `POST https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist`
- **Headers**:
  - `Authorization: Bearer <access_token>`
  - `User-Agent: antigravity/ide/1.0.0 darwin/arm64`
  - `Content-Type: application/json`
- **Body**: `{"metadata":{"ideType":"ANTIGRAVITY"}}`

### Clean Free (Starter) Signature:
```json
{
  "currentTier": { "id": "free-tier", "name": "Antigravity" },
  "allowedTiers": [
    { "id": "free-tier", "isDefault": true },
    { "id": "standard-tier", "userDefinedCloudaicompanionProject": true }
  ],
  "cloudaicompanionProject": "aicode-consumers",
  "ineligibleTiers": []
}
```

### Validation Required (Restricted) Signature:
```json
{
  "allowedTiers": [
    { "id": "standard-tier", "userDefinedCloudaicompanionProject": true }
  ],
  "ineligibleTiers": [
    {
      "tierId": "free-tier",
      "reasonCode": "VALIDATION_REQUIRED",
      "reasonMessage": "Your current account is not eligible for Antigravity. Verify your account to continue...",
      "validationErrorMessage": "Verify your account to continue."
    }
  ]
}
```
*Note*: When `VALIDATION_REQUIRED` is triggered, Google drops `cloudaicompanionProject: aicode-consumers`. Any request to `aicode-consumers` from this account hangs 10–25s and fails with 403 / 429 semaphore congestion.

## Farm Account Cross-Reference Triad

When inspecting or selecting candidate accounts from the pool, cross-reference 3 sources:
1. **OmniRoute DB** (`C:/Users/Kibe/.omniroute/storage.sqlite`):
   - Table `provider_connections`: inspect `email`, decrypted `access_token`, `provider_specific_data` (`tier`, `subscriptionTier`), `is_active`.
2. **Excel Credential Vault** (`D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` sheet `Gmail Accounts`):
   - Fields: `số máy`, `tài khoản gmail`, `pass mail`, `2fa` (Base32 secret key), `mail khôi phục`, `trạng thái`.
3. **GPMLogin Profile Store** (`C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/profile_data.db`):
   - Table `Profiles`: query `Id`, `Name`, `ProfilePath` matching email prefix (e.g. `44 - kellynbishop...`).

## Model & Upstream Calling Rules
- Direct upstream calls to `streamGenerateContent?alt=sse` with `project: aicode-consumers` reject untiered model IDs (`gemini-2.5-flash`, `gemini-2.0-flash`) with immediate 429 `RESOURCE_EXHAUSTED`.
- Always use the resolved tiered IDs (`gemini-3.8-flash-tiered`, `gemini-3.7-flash-tiered`) or route requests through OmniRoute combos (`ag-gemini-free-pool`, `omni-worker` on port `20129`).

## Required evidence sequence

1. Read the current connection row and recent `call_logs` without exposing tokens.
2. Probe the actual model surface through `x-omniroute-connection-id`; do not rely on `testStatus: active` or a userinfo-only probe.
3. Classify separately:
   - `401 invalidated oauth token`: OAuth re-auth required; metadata edits cannot repair it.
   - `403 Antigravity upstream`: entitlement, project, geo, or account-policy failure; isolate before retrying.
   - `422 missing projectId` / `gcp_project_required`: use the canonical bounded project bootstrap/BYOP path; never fabricate a project claim.
   - `400 probe_inconclusive`: not proof of health; run a real model request.
   - semaphore timeout: local capacity symptom; use fail-fast spillover, but do not label the account dead without upstream evidence.
4. Only re-add an account to a combo after a real model request returns HTTP 200 and the account passes the relevant entitlement check.

## Recovery policy

- Preserve the account and its GPM profile; do not delete or overwrite credentials.
- Do not silently set `is_active = 1` when the operator intentionally disabled an account.
- A healer may select a Restricted account for controlled OAuth recovery, but it must not mark the account healthy until OAuth exchange succeeds and a real model probe passes.
- If OAuth is revoked/invalidated, run the existing credential-injected GPM OAuth pipeline with evidence capture. If Google presents a phone checkpoint or an unresolved security challenge, stop and keep the account isolated.
- If Google requires a user-owned project (BYOP), obtain a real project through the supported Google flow or leave the account isolated. Do not set `projectId = aicode-consumers` as a substitute for a missing entitlement.
- Test one canary account first, then process the remainder in bounded batches; after the first failed canary, capture the failure evidence and reassess instead of blindly retrying.

## Routing safety

`isActive` and combo membership are separate controls. Removing an account from every production combo is the immediate containment action. The account can remain stored for later recovery. A successful short prompt or one 200 response does not establish that the account tolerates Farm concurrency or long-context traffic; verify with a representative, bounded probe before restoring it.
