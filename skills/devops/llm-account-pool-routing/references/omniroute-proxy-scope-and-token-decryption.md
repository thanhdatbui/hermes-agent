# OmniRoute Proxy Assignment Scope & AGY CLI Token Decryption

## 1. OmniRoute Proxy Routing Architecture & The `scope="account"` Invariant

### The Failure Mode
When an Antigravity or LLM connection in OmniRoute is created or updated via custom scripts, developers often mistakenly insert into `proxy_assignments` with:
```sql
-- WRONG: OmniRoute upstream resolver IGNORES this!
INSERT INTO proxy_assignments (proxy_id, scope, scope_id, ...) VALUES (?, 'connection', ?, ...);
```
Or they assume that `provider_connections.proxy_enabled = 1` means the proxy is working.
In reality:
- `proxy_enabled = 1` is merely an allow-toggle on the connection record; it does NOT assign a proxy.
- OmniRoute's resolver (`resolveProxyForScopeFromRegistry("account", connectionId)` in `src/lib/db/settings.ts`) specifically queries:
  ```sql
  SELECT p.* FROM proxy_assignments a 
  JOIN proxy_registry p ON p.id = a.proxy_id 
  WHERE a.scope = 'account' AND a.scope_id IS ?
  ```
- If `scope` is `'connection'`, the query returns null, and OmniRoute silently falls back to **DIRECT egress** from the host IP! This immediately leaks the home/server IP to Google, triggering `403 VALIDATION_REQUIRED` and burning accounts.

### Proper Assignment & Cache Invalidation
1. **Always assign via the official API endpoint** (which handles in-memory `proxyResolutionCache` and `proxyRegistryGeneration` bumps):
   ```python
   import requests
   requests.put(
       "http://127.0.0.1:20129/api/settings/proxies/assignments",
       json={"scope": "account", "scopeId": connection_id, "proxyId": proxy_registry_id},
       timeout=10
   )
   ```
2. **If editing SQLite directly (`storage.sqlite`), you MUST use `scope = 'account'`**:
   ```sql
   INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
   VALUES (?, 'account', ?, 0, datetime('now'), datetime('now'));
   ```

### Verification & Read-Back Protocol
- **DO NOT** check `call_logs.summary.proxy` — the summary JSON does not carry proxy metadata.
- **Verification Method 1 (Resolver API):**
  `GET http://127.0.0.1:20129/api/settings/proxies/assignments?resolveConnectionId=<cid>`
  Must return `{"level": "account", "proxy": {"host": "...", "port": ...}}`.
- **Verification Method 2 (DB Proxy Logs):**
  Query `proxy_logs` table in `storage.sqlite`:
  ```sql
  SELECT timestamp, status, proxy_host, proxy_port, provider, connection_id 
  FROM proxy_logs WHERE connection_id = ? ORDER BY timestamp DESC LIMIT 3;
  ```
  Must show status `success` and the exact phone farm proxy host/port.

---

## 2. Antigravity CLI (`agy`) Profile Credentials & AES-GCM Decryption

### The Encrypted Token Pitfall (`enc:v1:`)
In `storage.sqlite`, OmniRoute encrypts all `access_token` and `refresh_token` fields with prefix `enc:v1:`.
Directly selecting these tokens and writing them into `.gemini/oauth_creds.json` for an AGY CLI profile corrupts the profile:
- Binary `agy.exe` cannot parse `enc:v1:` strings.
- Google OAuth rejects the refresh grant (`invalid_grant`).
- `agy.exe` drops back to default unauthenticated state, throwing `RESOURCE_EXHAUSTED (code 429)`.

### Exact Decryption Algorithm (AES-256-GCM)
The encryption key is stored in `C:/Users/Kibe/AppData/Roaming/omniroute/server.env` under `STORAGE_ENCRYPTION_KEY`.
Format in SQLite: `enc:v1:<iv_hex>:<ciphertext_hex>:<authTag_hex>`.

```python
import base64, urllib.parse, urllib.request, json, re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# 1. Derive key using Scrypt
with open(r"C:\Users\Kibe\AppData\Roaming\omniroute\server.env", "r", encoding="utf-8") as f:
    key_secret = re.search(r"STORAGE_ENCRYPTION_KEY=(.+)$", f.read(), re.MULTILINE).group(1).strip().encode("utf-8")

kdf = Scrypt(salt=b"omniroute-field-encryption-v1", length=32, n=16384, r=8, p=1)
derived_key = kdf.derive(key_secret)

# 2. Decrypt token
def decrypt_token(enc_str: str) -> str:
    if not enc_str.startswith("enc:v1:"):
        return enc_str
    parts = enc_str[7:].split(":")
    iv = bytes.fromhex(parts[0])
    ct = bytes.fromhex(parts[1])
    tag = bytes.fromhex(parts[2])
    aesgcm = AESGCM(derived_key)
    return aesgcm.decrypt(iv, ct + tag, None).decode("utf-8")

# 3. Refresh live access_token from Google
client_id = base64.b64decode("MTA3MTAwNjA2MDU5MS10bWhzc2luMmgyMWxjcmUyMzV2dG9sb2poNGc0MDNlcC5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbQ==").decode()
client_secret = base64.b64decode("R09DU1BYLUs1OEZXUjQ4NkxkTEoxbUxCOHNYQzR6NnFEQWY=").decode()

def get_live_access_token(clean_refresh_token: str):
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": clean_refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

---

## 3. Windows Session Isolation in VMware Automation

- `vmrun runProgramInGuest` runs strictly inside the session of the guest credentials specified (`-gu <user> -gp <pass>`).
- If VMware Workstation console displays a different logged-in desktop user (e.g., `thanh` vs `tada`), programs launched via `vmrun` execute in an isolated background session.
- PowerShell GUI automation (`SendKeys`, `AppActivate`) or mouse click commands cannot interact with the console desktop across session boundaries.
- For VM rescue operations where GUI input is needed, pass exact credentials and TOTP to the user or interact via an exposed CDP/network port, rather than trying to blind-click cross-session.
