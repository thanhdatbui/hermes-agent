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
1. `ag_cli.py` starts a local ephemeral proxy server on an available localhost port.
2. `HTTP_PROXY` and `HTTPS_PROXY` are set in the subprocess environment of `agy.exe` pointing to this local port.
3. The local proxy decodes incoming HTTPS requests to Google Cloud Code.
4. If path matches `streamGenerateContent`:
   - Inspects JSON body: adds `"enabledCreditTypes": ["GOOGLE_ONE_AI"]`.
   - Re-encodes body, adjusts `Content-Length`.
5. Forwards to the profile's upstream proxy (`test.taadaa.click:<port>`).
6. Streams responses back to `agy.exe` verbatim.
