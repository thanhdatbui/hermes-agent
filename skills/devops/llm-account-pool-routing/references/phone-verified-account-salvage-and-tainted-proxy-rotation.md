# Phone-Verified Account Salvage and Tainted Proxy Quarantine Runbook

## 1. Capital Protection Invariant for Phone-Verified Accounts

### Background & Value Invariant
In phone farm and LLM account operations, accounts with phone verification (SMS verified via 5SIM or physical SIM) represent tangible real-money capital ($0.08 to $0.50+ per number, plus manual labor, proxy bandwidth, and aging time).
- **User Correction Invariant**: *"Mày đéo hiểu à acc cũ t ver sim tốn tiền r dm"*.
- **Strict Anti-Discard Rule**: NEVER write off an account or advise the user to discard it merely because an automated test or API endpoint returns `401 Unauthorized` or token expired.
- **Root-Cause Classification**:
  1. **Transient Token Expiry (Recoverable)**: The short-lived `access_token` expired, but the long-lived `refresh_token` remains completely valid on OpenAI's OAuth server.
  2. **Permanent Deactivation (Dead)**: The underlying account was terminated by Trust & Safety (`account_deactivated` or `invalid_grant` with `"Your session has ended. Please log in again."`).

---

## 2. Automated Salvage Workflow via Refresh Token Grant

Before concluding any phone-verified account is dead, execute a dedicated OAuth Refresh Token probe.

### Decryption & Probe Steps
1. **Derive Storage Decryption Key**:
   In OmniRoute (`storage.sqlite`), secrets are encrypted with AES-GCM using a key derived from `STORAGE_ENCRYPTION_KEY` in the OmniRoute process environment via Scrypt (`salt = b'omniroute-field-encryption-v1'`, `n=16384`, `r=8`, `p=1`).
2. **Mandatory Proxy Route**:
   ALWAYS route the token refresh HTTP request through the account's designated proxy (`test.taadaa.click:<port>` or `192.168.110.2:<port>`). Direct IP calls will poison the session or trigger immediate security bans.
3. **Execute Refresh Grant**:
   Send HTTP POST to OpenAI OAuth endpoint:
   ```http
   POST https://auth.openai.com/oauth/token
   Content-Type: application/x-www-form-urlencoded
   User-Agent: codex_cli_rs/0.136.0

   client_id=app_EMoamEEZ73f0CkXaXp7hrann&grant_type=refresh_token&refresh_token=<DECRYPTED_REFRESH_TOKEN>
   ```
4. **Evaluate Verdict**:
   - **HTTP 200 OK**: Account is 100% LIVE! Extract new `access_token`, `refresh_token`, and `expires_at`.
   - **Live Verification**: Immediately ping `https://chatgpt.com/backend-api/codex/responses` (model `gpt-5.6-luna`) with the new token. A response of `200 OK` or `429 Rate Limited` confirms the account is active.
   - **HTTP 401 Unauthorized (`invalid_grant` / `Your session has ended`)**: Token revoked, account permanently dead.
   - **`account_deactivated`**: Account terminated by Trust & Safety.

*Case Study (October 2026)*: Running this automated sweep across 69 "expired/error" Codex accounts immediately resurrected 4 healthy, verified accounts (`jessicaobakervi8yx@gmail.com`, `machanh041236@gmail.com`, `kellynbishopgq63j@gmail.com`, `vanharlingenmach959@hotmail.com`), increasing the pool capacity by ~17%.

---

## 3. Tainted Proxy Quarantine & Redial Protocol

When an account ban wave occurs (e.g. OpenAI IP-based ban), the egress IPs that were active during the incident are tainted. Continuing to run healthy or newly registered accounts through these tainted IPs risks immediate cross-contamination.

### Tainted Port Mapping
Cross-reference banned accounts against:
- GPMLogin `profile_data.db` (`Profiles.JsonData -> Proxy`).
- OmniRoute `proxy_assignments` join `proxy_registry`.
- 9Router `providerConnections.data -> providerSpecificData.proxyPoolId`.
Extract all tainted port numbers.

### Rotation Procedures

#### A. MobiProxy 4G Cluster (`test.taadaa.click:5101..5138`)
1. **API Trigger**:
   ```python
   url = f"http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:{port}&token={TOKEN}"
   req = urllib.request.Request(url, headers={"User-Agent": "MobiRecreate/1.0"})
   urllib.request.urlopen(req, timeout=10)
   ```
2. **Pacing Invariant**:
   Sleep **at least 2.5 seconds** between successive port recreate calls to prevent locking up the multi-dongle OpenWrt USB bus.
3. **Anchor Port `5101` Rule**:
   Port `5101` anchors the dynamic DNS resolution for domain `test.taadaa.click`. If `5101` is tainted, trigger recreate normally, but pause 15–30 seconds to allow the modem redial and DDNS daemon to resolve `test.taadaa.click` to the new IP before resuming dependent tests.

#### B. MikroTik Multi-WAN PPPoE (`pppoe-out1..pppoe-out7` / Ports `10001..10007`)
1. **RouterOS REST API Endpoint**: `http://192.168.110.2:9090/rest/interface/pppoe-client/<id>`.
2. **Disconnect (Disable)**:
   ```json
   PATCH /rest/interface/pppoe-client/*5D {"disabled": "true"}
   ```
3. **CRITICAL TIMING RULE (40-Second Cooldown)**:
   You MUST sleep **at least 40 seconds** while the PPPoE interface is disabled. If re-enabled within <15 seconds, the ISP BRAS server will re-assign the exact same stale IP lease.
4. **Reconnect (Enable)**:
   ```json
   PATCH /rest/interface/pppoe-client/*5D {"disabled": "false"}
   ```
5. **Verify Lease Change**:
   Query `/rest/ip/address` to ensure the interface acquired an IP strictly different from the pre-rotation IP.
6. **Container Restart**:
   Start/restart MikroTik proxy containers (`/rest/container/start` for 3proxy and sing-box) to drop lingering half-open sockets.

---

## 4. 9Router Pool Integration Invariant
When salvaged accounts are re-added:
- Insert/update `providerConnections` in `C:/Users/Kibe/AppData/Roaming/9router/db/data.sqlite`.
- Ensure `providerSpecificData` contains the exact `proxyPoolId` matching the account's dedicated port.
- Maintain `fallbackStrategy: "round-robin"` and `stickyRoundRobinLimit: 2` in `settings` table.
- Verify rotation with 4+ consecutive chat completion probes to confirm multi-IP egress distribution.
