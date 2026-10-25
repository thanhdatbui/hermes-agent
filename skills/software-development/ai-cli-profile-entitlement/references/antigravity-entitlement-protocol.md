# Antigravity Headless Entitlement & Quota Protocol

## 1. Upstream Protocol Internals

### Endpoints
- Base URLs:
  - `https://daily-cloudcode-pa.googleapis.com`
  - `https://cloudcode-pa.googleapis.com`
- Load Code Assist: `POST /v1internal:loadCodeAssist`
- Onboard User: `POST /v1internal:onboardUser`
- Stream Generate: `POST /v1internal:streamGenerateContent`

### Protobuf Definition (Credits)
```protobuf
package google.internal.cloud.code.v1internal;

enum CreditType {
  CREDIT_TYPE_UNSPECIFIED = 0;
  GOOGLE_ONE_AI = 1;
}

message GenerateContentRequest {
  ...
  repeated CreditType enabled_credit_types = 8 [json_name = "enabledCreditTypes"];
}
```

## 2. Header Fingerprint
When dispatching headless requests that need to pass entitlement verification:
```http
User-Agent: antigravity/ide/1.10.4 darwin/arm64
X-Goog-Api-Client: gl-node/22.21.1
Content-Type: application/json
Authorization: Bearer <oauth_access_token>
```

## 3. Account Status Mapping
In `loadCodeAssist`:
- `subscriptionInfo.paidTier.id`: `"g1-pro-tier"` (User has paid subscription)
- `subscriptionInfo.currentTier.id`: `"free-tier"` (Currently active tier without credit injection)
- `cloudaicompanionProject`: `"aicode-consumers"`

When `enabled_credit_types: [1]` (`["GOOGLE_ONE_AI"]`) is omitted, the backend falls back to `currentTier` (Free Tier) and applies daily limits. When present, the backend consumes Google One AI credits (1,500 requests/day).

## 4. Local Interceptor Architecture
To enable native `agy.exe` without using a centralized chat completion proxy:
1. `ag_cli.py` starts a local ephemeral proxy server (`start_credit_proxy` in `D:/Taadaa/tools/ag_credit_proxy.py`) on an available localhost port (`127.0.0.1:0`).
2. Set `env["CLOUD_CODE_URL"] = f"http://127.0.0.1:{port}"` for the `agy.exe` subprocess.
3. Keep `HTTPS_PROXY` and `HTTP_PROXY` in `env` (to satisfy environment contracts/tests) but set `NO_PROXY=127.0.0.1,localhost` and `no_proxy=127.0.0.1,localhost`. Go's `net/http` standard library honors `NO_PROXY`, directly routing loopback requests to `CLOUD_CODE_URL` without external proxy traversal.
4. When `agy.exe` sends requests to the local proxy:
   - Handles `Transfer-Encoding: chunked` by reading hex chunk lengths to reconstruct full request body (avoiding empty body 400 INVALID_ARGUMENT).
   - If path matches `streamGenerateContent`:
     - Inspects JSON body: adds `"enabledCreditTypes": ["GOOGLE_ONE_AI"]`.
     - Ensures `"project": "aicode-consumers"`.
     - Re-encodes body, adjusts `Content-Length`.
5. The local proxy forwards the request upstream to `https://daily-cloudcode-pa.googleapis.com` via the profile's upstream proxy (`upstream_proxy`, e.g., `test.taadaa.click:<port>`).
6. The local proxy streams response status code, headers, and SSE chunks back to `agy.exe` verbatim, catching `ConnectionAbortedError` (WinError 10053) alongside `BrokenPipeError` and `ConnectionResetError`.
7. Verified with unit test suite in `D:/Taadaa/tools/tests/test_ag_credit_proxy.py` (100% pass).
8. **Upstream Quota Diagnosis:**
   - Pro Quota exhausted: Returns `429 RESOURCE_EXHAUSTED` with `reason: "INSUFFICIENT_G1_CREDITS_BALANCE"`. Confirms credit injection succeeded.
   - Free Tier fallback: Returns `429 RESOURCE_EXHAUSTED` with `message: "Individual quota reached. Please upgrade your subscription to increase your limits."`. Signals missing credit injection.

## 5. Multi-Profile Sandbox Isolation Architecture
When orchestrating a pool of distinct Pro accounts (e.g. 29 accounts `acc_01` to `acc_28`):
1. **Directory Structure per Profile:**
   - Base directory: `D:/Taadaa/agy_profiles/<profile_name>/`
   - `.gemini/google_accounts.json`: Binds single `active` email.
   - `.gemini/oauth_creds.json`: Account-specific refresh & access tokens.
   - `.gemini/projects.json`: Workspace mapping to GCP project `aicode-consumers`.
   - Sandbox AppData: `AppData/Roaming`, `AppData/Local`, `AppData/Local/Temp`.
2. **Environment Isolation Flags:**
   - `USERPROFILE`, `HOME`: Points to `profile_dir`.
   - `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP`: Dedicated sandbox paths via `ensure_sandbox_dirs()`.
   - `ANTIGRAVITY_GEMINI_DIR`: Points to `profile_dir/.gemini`.
   - `AGY_ACCOUNT`: Set to `active` email.
   - `ANTIGRAVITY_VSCODE_HOST=1`: Signals IDE integration host.
3. **Loopback Routing & Proxy Sanitization:**
   - Child process has `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` stripped.
   - Explicit `NO_PROXY=127.0.0.1,localhost` to prevent Go `net/http` from routing loopback traffic externally.
   - Upstream mobile/static proxy (e.g., ports 5101-5136) is handled exclusively by the `ag_credit_proxy` instance.
4. **O(1) Surgical Integration Pattern:**
   - To avoid re-indenting large execution blocks, invoke context manager via `credit_proxy_mgr.__enter__()` before `subprocess.Popen` and `credit_proxy_mgr.__exit__()` in the outer `finally:` block. Keeps diff numstat <= 15 lines.
5. **Process Lease Locking:**
   - `acquire_profile_lock(profile_dir)` writes a lease token file with PID and timestamp.
   - TTL = 1800s (30 mins); checks PID liveness before declaring a profile in use to prevent deadlocks from killed workers.
