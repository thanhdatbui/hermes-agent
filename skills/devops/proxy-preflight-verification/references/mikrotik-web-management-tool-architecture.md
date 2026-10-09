# MikroTik Web Management Tool — Architecture & Diagnostic Workflow

## Architecture (2026-09-09)

```
Browser → https://mikrotik-tool.pages.dev/  (Cloudflare Pages — frontend)
            ↓ fetch()
         https://mikrotik-control.thanhdatbui1995.workers.dev  (Cloudflare Worker — backend)
            ↓ REST API
         http://<management_pppoe_ip>:9090/rest/...  (MikroTik RouterOS REST API)
```

- **Frontend**: Single-page HTML app (inline JS, no framework). Hosted on Cloudflare Pages.
- **Backend**: Cloudflare Worker (`mikrotik-control.thanhdatbui1995.workers.dev`). Proxies API calls from browser to MikroTik REST API.
- **Router API**: `http://192.168.110.2:9090/rest/` (internal) or via public PPPoE IP (external).
- **DNS**: `mirotik1.taadaa.click` → public IP of management PPPoE line (dynamic, changes on reconnect).
- **Auth**: HTTP Basic (`admin:N0spam@@`) — hardcoded in both frontend (base64) and Worker.
- **Login password** (frontend UI): `N0spam@@`

### Frontend Tabs
| Tab | Function | API Endpoint |
|-----|----------|-------------|
| 📡 Danh sách Proxy | List PPPoE interfaces + their public IPs | `/api/ip`, `/api/monitor` |
| ⏱ Tự động đổi IP | PPPoE schedule auto-rotation | `/api/settings/auto` |
| 🔑 Đổi Pass Proxy | Change proxy auth credentials | `/api/container/envs` |
| { } API Change IP | Trigger IP change on specific interface | `/api/change-ip` |
| 🛡️ Bảo mật | Security settings | — |

## Failure Mode: HTTP 522 "Lỗi kết nối Router"

### Root Cause Chain
1. User clicks "Change IP" on web UI → Worker calls `/api/change-ip`
2. Worker triggers PPPoE reconnect on management line (e.g., `pppoe-out1`)
3. PPPoE gets new public IP (or gets disabled if credentials fail)
4. DNS `mirotik1.taadaa.click` still points to OLD IP
5. Worker tries to connect to old IP → timeout → returns HTTP 522 to browser
6. Web app shows "Lỗi kết nối Router: RouterOS HTTP 522: error code: 522"

### Diagnostic Steps (O(1))

```bash
# 1. Check Worker is alive (root should return 404)
curl -s -w "\nHTTP %{http_code}" "https://mikrotik-control.thanhdatbui1995.workers.dev/"
# Expected: {"error":"Not found"} + HTTP 404

# 2. Check Worker → Router connectivity (will timeout if DNS stale)
curl -s -w "\nHTTP %{http_code}" --connect-timeout 10 "https://mikrotik-control.thanhdatbui1995.workers.dev/api/ip"
# If timeout → DNS staleness or firewall block

# 3. Check DNS vs actual PPPoE IPs
nslookup mirotik1.taadaa.click
# Compare resolved IP with actual PPPoE interface IPs

# 4. Check management PPPoE line status via mikrotik_manager.py
python D:/Taadaa/AI-Tools/scripts/mikrotik_manager.py --check

# 5. Check specific line status
python -c "
from scripts.mikrotik_manager import api_call, find_active_host
host = find_active_host()
pppoe = api_call(host, '/interface/pppoe-client?name=pppoe-out1')
print(pppoe[0] if pppoe else 'NOT FOUND')
"

# 6. Verify firewall allows port 9090 from WAN
# Rule should exist: chain=input dst-port=9090 action=accept comment="REST API external"
```

### Fix Options

**Option A: Re-enable management PPPoE + update DNS**
```python
from scripts.mikrotik_manager import api_call, find_active_host
host = find_active_host()

# Re-enable pppoe-out1
pppoe = api_call(host, '/interface/pppoe-client?name=pppoe-out1')
if pppoe and pppoe[0].get('disabled') == 'true':
    api_call(host, f"/interface/pppoe-client/{pppoe[0]['.id']}", method='PATCH', data={"disabled": False})
    # Wait for PPPoE to connect, then check new IP
    import time; time.sleep(10)
    addrs = api_call(host, '/ip/address?interface=pppoe-out1')
    print(f"New IP: {addrs[0]['address']}" if addrs else "No IP yet")

# Then update DNS record on Cloudflare to new IP
```

**Option B: Use Cloudflare Tunnel (more stable, IP-independent)**
- Install `cloudflared` on MikroTik (or a sidecar container)
- Tunnel port 9090 to Cloudflare edge
- Worker connects via tunnel hostname instead of dynamic IP
- No DNS staleness possible

## MikroTik Manager CLI Quick Reference

Location: `D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py`

| Flag | Function | When to Use |
|------|----------|-------------|
| `--check` | Status overview (RouterOS, PPPoE, containers) | First diagnostic step |
| `--fix` | Auto-repair IP conflicts on dockers_proxy, verify hairpin NAT, restart 3proxy | After IP changes or container crashes |
| `--watchdog` | Audit all PPPoE lines, auto-reconnect dead ones | Mass line failures |
| `--reconnect N` | Redial specific PPPoE line N | Single line down |

**Router hosts** (tried in order): `192.168.110.2`, `mirotik1.taadaa.click`, `192.168.88.1`
**REST API port**: 9090
**Auth**: `admin:N0spam@@`

## Worker Source Code Locations

- **Cloudflare Worker**: `C:\Users\Kibe\iCloudDrive\Backup_OneDrive\mirotik\mikrotik-worker\`
  - `wrangler.toml` — Worker name `mikrotik-control`, KV binding `LOCK`, cron `* * * * *`
  - `src/index.js` — Full Worker source (207 lines)
- **Frontend HTML**: `C:\Users\Kibe\iCloudDrive\Backup_OneDrive\mirotik\mirotik1-tool\index.html`
- **GitHub repo**: `thanhdatbui/AI-Tools` (contains `scripts/mikrotik_manager.py`)

## Worker Environment Variables

The Worker reads env vars at runtime (set in Cloudflare dashboard or `wrangler.toml`):

| Env Var | Default | Purpose |
|---------|---------|---------|
| `ROUTEROS_HOST` | `mirotik1.taadaa.click` | Router hostname/IP for REST API |
| `ROUTEROS_PORT` | `80` | REST API port (must be `9090` for MikroTik www service) |
| `ROUTEROS_PROTO` | `http` | Protocol |
| `ROUTEROS_USER` | `admin` | REST API username |
| `ROUTEROS_PASS` | `N0spam@@` | REST API password |

**Critical**: Default port is `80` but MikroTik `www` service runs on `9090`. The Worker env MUST have `ROUTEROS_PORT=9090` set, otherwise it will fail to connect even when DNS is correct.

## Worker `changeIp()` Pitfall

The Worker's `changeIp()` function (line 48-82 of `src/index.js`) performs:
1. PATCH disable `pppoe-outN` → wait 2s → PATCH enable
2. Polls `/interface/pppoe-client/monitor` every 2s for up to 30s
3. Returns new public IP from `state['local-address']`

**Failure mode**: If PPPoE reconnect fails (bad credentials, ISP timeout, interface error), the function throws after 30s but the interface may remain **disabled**. The user sees "đổi IP" error on the web UI, but the interface is now dead. This is exactly what happened in the 2026-09-09 incident — `pppoe-out1` was left `disabled=true` after a "Change IP" operation.

**Fix**: Always check `pppoe-out1` status first when web app reports errors. If disabled, re-enable via API: `PATCH /interface/pppoe-client/{id} {"disabled": false}`.

## DNS Update Requirements

After IP change, DNS `mirotik1.taadaa.click` must be updated on Cloudflare:
- Domain `taadaa.click` uses Cloudflare nameservers (`arch.ns.cloudflare.com`, `malavika.ns.cloudflare.com`)
- **No Cloudflare API token found on machine** — `wrangler whoami` reports "not authenticated"
- Manual DNS update via Cloudflare Dashboard, or obtain API token with `zone:edit` scope
- Alternative: Set up Cloudflare Tunnel (`cloudflared`) to avoid dynamic DNS dependency entirely

## Key Infrastructure Facts

- **Management PPPoE line**: `pppoe-out1` (user: `d511_gftth_khoind5`, interface: `macvlan1`)
- **Default route**: Multiple PPPoE lines with equal-distance routes (ECMP load balancing)
- **Firewall**: Input accept on port 9090 (REST API external)
- **DNS**: `mirotik1.taadaa.click` resolves to management line's public IP (dynamic!)
- **Total PPPoE**: 60 interfaces, typically 34-35 running, 10-11 disabled
- **Public IPs**: Each PPPoE gets a dynamic public IP from ISP (Viettel/FPT ranges: 116.x, 171.x, 27.x)
- **RouterOS**: 7.18.2 (stable), REST API on port 9090 (www service)
