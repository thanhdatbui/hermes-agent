# MikroTik Web Manager & PPPoE Management Tools

## Local Web Manager (Preferred for PPPoE Management)

**Path:** `D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py`
**Launcher:** `D:\Taadaa\AI-Tools\tools\mikrotik_web\run_hidden.vbs` (chạy ngầm không hiện console qua `pythonw.exe`) hoặc `start_mikrotik_web.bat`
**URL:** `http://localhost:2310` (port configurable via `WEB_PORT` constant or CLI arg)

### Architecture
- Python `ThreadingHTTPServer` with embedded HTML/JS frontend (3 tabs: Dashboard, Schedules, API)
- Connects directly to MikroTik REST API at `192.168.110.2:9090`
- No cloud dependency, no DNS dependency, works on LAN only
- Accessible via Tailscale MagicDNS at `http://kibe:2310` from any device on tailnet (máy tính đã đổi tên sang `kibe`)
- IP Whitelist tích hợp trong `server.py`: `192.168.110.` (LAN), `100.` (toàn bộ dải Tailscale CGNAT 100.64.0.0/10), `127.0.0.1` (localhost)

### API Endpoints
- `GET /api/status` — MikroTik health check (RouterOS version, CPU, memory)
- `GET /api/proxies` — Lists all 60 PPPoE interfaces with port, status, IP, **live uptime**
- `POST /api/change-ip` — Reconnects interface (disable → 2s → enable → poll for IP up to 60s)
- `GET /api/schedules` — List all auto IP change schedules
- `POST /api/schedules` — Create new schedule (time, days[], interface)
- `PATCH /api/schedules/{id}` — Update schedule (enabled, time, days, interface)
- `DELETE /api/schedules/{id}` — Delete schedule

### Key Design Decisions
1. **ThreadingHTTPServer** — NOT `HTTPServer` (single-threaded blocks on MikroTik API calls causing browser timeouts)
2. **60s timeout** for change-ip (was 30s, too short for PPPoE reconnection)
3. **Retry logic** on enable failure (try enable twice before giving up)
4. **Error handling** — All API calls wrapped in try/except, returns JSON error instead of crashing
5. **Auto-refresh** every 30s via JavaScript
6. **Batch uptime fetch** — Single monitor API call with comma-separated `.id` values returns uptime for all running interfaces at once; maps results by matching `local-address` to known PPPoE IPs
7. **Port configurable** — Default 2310, override via `WEB_PORT` constant or `python server.py <port>`

### PPPoE Change IP Flow
```
1. Disable interface (PATCH /interface/pppoe-client/{id} {disabled: true})
2. Wait 2 seconds
3. Enable interface (PATCH /interface/pppoe-client/{id} {disabled: false})
4. Poll /ip/address?interface={name} every 2s for up to 60s
5. Return new IP when found, or timeout error
```

### Frontend Tabs
1. **Dashboard** — PPPoE table with live uptime (e.g., `1h56m52s`), filter by name/IP/port/status, manual Change IP button per row
2. **Schedules** — CRUD for automatic IP rotation: set time (HH:MM), days of week (Mon-Sun), target interface; enable/disable toggle; auto-executes via background thread checking every 30s
3. **API & cURL** — Documents all endpoints; per-proxy `curl -x http://host:port http://api.ipify.org` with one-click copy to clipboard

### Pitfalls
- **CẤM dùng `HTTPServer`** — MUST use `ThreadingHTTPServer(ThreadingMixIn, HTTPServer)` for concurrent requests
- **pppoe-out1 is management interface** — Changing IP on it temporarily breaks Worker→MikroTik connectivity
- **DNS update lag** — After PPPoE IP change, `cloudflare-ddns` script on MikroTik updates DNS every 1 minute
- **30s timeout too short** — PPPoE reconnection can take 30-60s, always use 60s minimum
- **Monitor API batch call** — Must use comma-separated `.id` values (`*5D,*5E,*5F`); passing array or multiple keys returns 400. Match results to interfaces by `local-address` ↔ `ip_map`.
- **Uptime field** — PPPoE interfaces don't expose uptime in list endpoint; must call `/interface/pppoe-client/monitor` for each running interface

## MikroTik REST API Quick Reference

### Connection
```
Host: 192.168.110.2 (internal) or mirotik1.taadaa.click (external, port 9090)
Port: 9090 (www service)
Auth: Basic (admin:N0spam@@)
```

### Useful Endpoints
- `GET /rest/system/resource` — RouterOS version, CPU, memory
- `GET /rest/interface/pppoe-client` — All PPPoE interfaces
- `GET /rest/ip/address` — All IP addresses
- `PATCH /rest/interface/pppoe-client/{id}` — Enable/disable interface
- `POST /rest/interface/pppoe-client/monitor` — Monitor PPPoE status

### Cloudflare DDNS Script on MikroTik
Located in `/system/script` named `cloudflare-ddns`:
- Runs every 1 minute via scheduler
- Reads IP from `pppoe-out1` interface
- Updates Cloudflare DNS record `mirotik1.taadaa.click`
- Token: `[REDACTED_CLOUDFLARE_TOKEN]`
- Zone: `7ec2923fdd73bba508b64cb69e013d71`
- Record: `d17862a6a5cf6b7aee69f038f682b3ce`

### IP Whitelist & Firewall Rules (FPT_LAN)
Server has built-in IP whitelist (`ALLOWED_IPS` in `server.py`):
- `192.168.110.` — LAN subnet (phones + PCs)
- `100.88.164.` — Tailscale VPN
- `127.0.0.1` — Localhost

On MikroTik, proxy ports (10001-10060) are restricted to FPT_LAN only:
- Address list `FPT_LAN`: `192.168.110.0/24`, `192.168.10.0/24`
- Rule 1: `chain=forward src-address-list=FPT_LAN dst-port=10001-10060 action=accept`
- Rule 2: `chain=forward dst-port=10001-10060 action=drop` (catch-all block)

### Port Forwarding for Remote Access
NAT rule on MikroTik: `WAN:8090 → 192.168.110.123:8090` (Kibe PC)
- Firewall filter: `chain=input dst-port=8090 action=accept`
- LAN access: `http://192.168.110.123:8090`
- WAN access: `http://171.231.178.37:8090` (IP changes with PPPoE)

### Auto-start on Windows Boot
Launcher bat copied to `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\mikrotik_web.bat`

### Cloudflare DDNS Auto-Recovery
When pppoe-out1 is re-enabled after being disabled:
1. PPPoE reconnects and gets a new IP (e.g., `171.231.178.37`)
2. `cloudflare-ddns` scheduler (every 1 minute) reads new IP from pppoe-out1
3. Updates Cloudflare DNS record via API PUT
4. DNS propagates within ~2 minutes (TTL=120)
5. Cloudflare Worker can then reach MikroTik again
**No manual DNS update needed** — the DDNS script handles it automatically.

### Cloudflare Worker changeIp Bug Fix
Original Worker source at `C:\Users\Kibe\iCloudDrive\Backup_OneDrive\mirotik\mikrotik-worker\src\index.js` had:
- 30s timeout (too short for PPPoE reconnection)
- Silent error swallowing (`catch (_) {}`)
- No retry on enable failure

Fixed to:
- 60s timeout with 3s poll interval
- `console.error` logging in monitor loop
- Retry logic on enable failure (2 attempts)
- Vietnamese error messages with lastError detail

### MikroTik Manager CLI Script
**Path:** `D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py`
- `--check` — Status of router, PPPoE lines, containers
- `--fix` — Auto-repair IP conflicts, restart proxy container
- `--watchdog` — Audit all PPPoE lines, auto-reconnect dead/private IP
- `--reconnect N` — Re-dial specific PPPoE line

## User Preference: Local Tools Over Cloud

When building management tools for MikroTik:
- **PREFER local solutions** (Python HTTP server on localhost) over cloud-deployed (Cloudflare Workers/Pages)
- **Reason:** User frustration with cloud dependencies (DNS failures, Cloudflare 522 errors, token management)
- **Exception:** Only use cloud if user explicitly requests it or if remote access from outside LAN is required
- **Pattern:** Embed HTML frontend in Python server, serve on localhost:8090, auto-open browser on start
