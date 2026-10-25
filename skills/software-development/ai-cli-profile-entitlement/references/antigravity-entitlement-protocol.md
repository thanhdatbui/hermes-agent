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
3. Unset `HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy`, `https_proxy` in `agy.exe`'s environment so that requests to `127.0.0.1` go directly to the local proxy rather than failing via the upstream proxy.
4. When `agy.exe` sends requests to the local proxy:
   - If path matches `streamGenerateContent`:
     - Inspects JSON body: adds `"enabledCreditTypes": ["GOOGLE_ONE_AI"]`.
     - Ensures `"project": "aicode-consumers"`.
     - Re-encodes body, adjusts `Content-Length`.
5. The local proxy forwards the request upstream to `https://daily-cloudcode-pa.googleapis.com` via the profile's upstream proxy (`upstream_proxy`, e.g., `test.taadaa.click:<port>`).
6. The local proxy streams response status code, headers, and SSE chunks back to `agy.exe` verbatim.
7. Verified with unit test suite in `D:/Taadaa/tools/tests/test_ag_credit_proxy.py` (100% pass).
