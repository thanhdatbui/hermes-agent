# Gemini Web Pro 4 Argon Pool & Automated GPM CDP Extraction

## Executive Summary & Hard Invariant
- **User Mandate (October 2026)**: Never ask the user to manually launch GPM profiles or copy-paste session cookies. All credential extraction from GPM account pools MUST be executed autonomously via Chrome DevTools Protocol (CDP) WebSocket, followed by mandatory process cleanup.
- **Model Advantage**: While the native Antigravity IDE API (`daily-cloudcode-pa.googleapis.com`) is capped at `gemini-3.7-flash` and `gemini-3.1-pro`, Google Web (`gemini.google.com/app`) unlocks **`4 Argon`** ("Nhiệm vụ phức tạp - Mới") and advanced Thinking Level exclusively for Google AI Pro (`g1-pro-tier`) accounts.
- **Rotation Invariant**: Never route production tasks through a single web session account. To prevent rate-limiting, session expiration, and burst overload, maintain a minimum 5-account rotation pool (`gemini-web-argon-pool`) configured with `strategy: least-used` and strict 1-1 mobile proxy binding.

---

## 1. Automated CDP Cookie Extraction Protocol
To extract session cookies without user intervention:

1. **Start GPM Profile via Local API**:
   ```python
   # GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}
   # Returns: {"data": {"remote_debugging_address": "127.0.0.1:<port>"}}
   ```
2. **Attach via WebSocket CDP**:
   ```python
   # GET http://{remote_debugging_address}/json -> read webSocketDebuggerUrl
   import websocket, json
   ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
   ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
   res = json.loads(ws.recv())
   ws.close()
   ```
3. **Parse Google Pro Session Cookies**:
   Filter `google.com` domain cookies:
   - `__Secure-1PSID` (Mandatory auth ticket, ~150 chars)
   - `__Secure-1PSIDTS` (Session timestamp ticket, ~80 chars)
   - `__Secure-1PSIDCC` (Client context ticket, ~75 chars)
   Assemble into cookie header:
   `cookie_str = "__Secure-1PSID=...; __Secure-1PSIDTS=...; __Secure-1PSIDCC=..."`
4. **Stop & Clean Orphan Processes**:
   ```python
   # GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}
   import psutil
   for p in psutil.process_iter(['name', 'exe']):
       if 'gpm_browser' in (p.info.get('name') or '').lower():
           p.kill()
   ```

---

## 2. OmniRoute Provider Connection Registration
Register each extracted account into OmniRoute (`:20129`) as a `gemini-web` connection:

```python
payload = {
    "name": f"{email} (Pro Web)",
    "provider": "gemini-web",
    "email": email,
    "apiKey": cookie_str,
    "isActive": True,
    "providerSpecificData": {
        "cookie": cookie_str,
        "proxy": proxy_url,      # e.g. http://mobi11:TaadaaMobi#2026!@test.taadaa.click:5111
        "tier": "g1-pro-tier",
        "plan": "Pro"
    }
}
# POST http://127.0.0.1:20129/api/providers -> returns {"connection": {"id": "<conn_id>"}}
```

---

## 3. Strict 1-1 Proxy Assignment (`proxy_assignments`)
OmniRoute requires explicit assignment in SQLite to prevent direct IP leaks:

```sql
-- SQLite: C:/Users/Kibe/.omniroute/storage.sqlite
INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
VALUES (?, 'connection', ?, 0, datetime('now'), datetime('now'));
```
- `proxy_id`: Matches `proxy_registry.id` for the corresponding port (e.g. 5111 for mobi11, 5121 for mobi21).
- `scope`: Must be `'connection'`.
- `scope_id`: The newly generated OmniRoute connection ID.

---

## 4. Multi-Account Rotation Pool (`gemini-web-argon-pool`)
To prevent session choking, bundle all active Pro accounts into a least-used combo:

```python
combo_payload = {
    "name": "gemini-web-argon-pool",
    "description": "Gemini Web 4 Argon Pool (5 Google AI Pro Accounts)",
    "strategy": "least-used",
    "models": [
        {
            "model": "gemini-web/gemini-3.1-pro",
            "providerId": "gemini-web",
            "connectionId": conn_id_1,
            "label": "dokieu-argon-pro"
        },
        {
            "model": "gemini-web/gemini-3.1-pro",
            "providerId": "gemini-web",
            "connectionId": conn_id_2,
            "label": "namdung-argon-pro"
        },
        # ... up to 5 Pro connections
    ]
}
# POST http://127.0.0.1:20129/api/combos
```

---

## 5. Web vs Native Comparison Pitfalls
| Factor | Antigravity Native (`agy.exe`) | Gemini Web (`gemini-web`) |
| :--- | :--- | :--- |
| **Model Selection** | Capped at 3.7 Flash & 3.1 Pro | **4 Argon** & Thinking Level |
| **Tool Calling** | GPU-level native function calling | Prompt-emulated DSL (`ACTION: PATCH`, etc.) |
| **Session Lifetime** | Infinite (OAuth refresh token) | Temporary (rotated `__Secure-1PSIDTS`) |
| **Execution Path** | Direct gRPC / CloudCode API | HTTP `StreamGenerate` or Playwright |
