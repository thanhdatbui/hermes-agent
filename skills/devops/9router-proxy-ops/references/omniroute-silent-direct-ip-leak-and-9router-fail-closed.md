# OmniRoute Silent Direct IP Leakage vs. 9Router Fail-Closed Proxy Binding

## 1. Context & Incident Root Cause (Mass Codex Ban October 2026)
In October 2026, 51 out of 65 historical Codex connections in OmniRoute (`storage.sqlite`) were permanently banned by OpenAI Trust & Safety (`account_deactivated`).
Upon forensic analysis of `storage.sqlite`:
- Even though `proxy_enabled = 1` was set on `provider_connections`, 65 connections had **NO matching record in `proxy_assignments`** (`scope = 'account'` / `scope_id = connection_id`).
- **OmniRoute silent fallback**: OmniRoute does NOT fail-closed when `proxy_enabled = 1` but `proxy_assignments` is missing. It silently routes API calls over the machine's direct residential IP (`1.53.55.190`).
- Over time, dozens of automated sessions hitting `https://chatgpt.com/backend-api/codex/responses` and `api.openai.com` from a single static IP caused OpenAI fraud detection to flag and deactivate the entire account cluster.
- In contrast, accounts that had explicit proxy records in `proxy_assignments` survived at an ~71% rate.

## 2. 9Router Fail-Closed Architecture
Unlike OmniRoute's decoupled join tables, 9Router stores the proxy association directly inside the connection's data payload:
```json
{
  "providerSpecificData": {
    "proxyPoolId": "<uuid-of-proxyPool>"
  }
}
```
- Each `proxyPoolId` maps 1-to-1 to a distinct 4G Mobi egress port (`5101` - `5138`) or Mikrotik gateway (`10001`+).
- If the proxy fails or is misconfigured, 9Router fails the request rather than leaking the machine's direct public IP.

## 3. Optimal Rotation Strategy in 9Router
To prevent quota exhaustion (429) and avoid clustering requests onto a single egress IP:
- Configure 9Router `settings` (ID 1 in `data.sqlite`):
```json
{
  "fallbackStrategy": "round-robin",
  "stickyRoundRobinLimit": 2,
  "providerStrategies": {
    "codex": {
      "fallbackStrategy": "round-robin",
      "stickyRoundRobinLimit": 2,
      "rotateStrategy": "round-robin"
    }
  }
}
```
- Behavior: Each account serves exactly 2 consecutive requests (`consecutiveUseCount: 2`) before the router advances to the next active connection in the pool, smoothly cycling through all 4G Mobi egress IPs.
- On 429 (Rate Limit): 9Router immediately rotates to the next available account without failing the consumer turn.

## 4. GPMLogin API Lockout Diagnosis ("Yêu cầu cập trình duyệt")
When automating profile launches via GPMLogin local API (`http://127.0.0.1:19995/api/v3/profiles/start/{id}`):
- If the API returns: `{"success": false, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`
- **Root Cause**: An active unacknowledged modal dialog in the GPMLogin desktop application (e.g., "Big Update" popup, Fingerprint 411 announcement, or newly installed browser core needing initial GUI initialization).
- **Remediation**:
  1. Inspect the GPMLogin window via `computer_use(action='capture', app='GPMLogin')`.
  2. Dismiss modal dialogs ("Đóng thông báo" button).
  3. Manually launch (click "Mở") any single profile once in the GUI to allow GPMLogin to unpack/validate core resources.
  4. Subsequent API calls to `start` will return `{"success": true, ...}` immediately.
