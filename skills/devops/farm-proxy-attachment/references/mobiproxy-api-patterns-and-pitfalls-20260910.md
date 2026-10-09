# MobiProxy Web API Patterns & Pitfalls (2026-09-10)

## API Endpoints Discovered

### Authentication Flow
1. `GET /login.php` → Extract `_csrf` from `<input name="_csrf" value="...">`
2. `POST /login.php` → Form data: `_csrf=<token>&password=<admin_pass>`
3. `GET /index.php` → Extract CSRF from `<meta name="csrf-token" content="...">`
4. All subsequent API calls need headers: `X-CSRF-Token`, `X-Requested-With: XMLHttpRequest`, `Content-Type: application/json`

### Key Endpoints
| Endpoint | Method | Purpose | Restart Proxy? |
|:---|:---|:---|:---|
| `proxy.access_bulk` | POST | Set auth for ALL proxies at once | **YES - restarts all 40** |
| `proxy.access` | POST | Set auth for ONE proxy by index | May restart single proxy |
| `proxy.nat` | POST | Toggle NAT on/off | No |
| `settings.get` | GET | Read current settings | No |
| `dashboard` | GET | Full proxy list + status | No |
| `proxy_getlist?token=<api_token>` | GET | Simple proxy list (no auth needed) | No |

### Payload Examples
```json
// Set auth mode for single proxy
POST /api.php?action=proxy.access
{"index": 1, "mode": "strong", "password": "TaadaaMobi#2026!", "allowed_ips": ""}

// Set auth mode for all proxies (DANGEROUS)
POST /api.php?action=proxy.access_bulk
{"mode": "strong", "password": "TaadaaMobi#2026!", "allowed_ips": ""}

// Toggle NAT
POST /api.php?action=proxy.nat
{"enabled": true}
```

### Auth Modes
- `none` = No authentication (anyone can use proxy)
- `strong` = Username + password required
- `iponly` = IP whitelist only (no password needed from whitelisted IPs)

## PHP-FPM Memory Leak (Confirmed 2026-09-10)

### Symptoms
- Calling `proxy.access` ~13 times consecutively (even with 30s delay) → PHP-FPM OOM → 502 Bad Gateway
- `access_bulk` (restarts 40 proxies) → Immediate PHP-FPM crash → 502
- After reboot, box loads saved config → same crash pattern repeats

### Root Cause
- PHP-FPM 7.4.28 on OpenWrt MT7621 has memory leak
- RAM (128MB) not released after each API request
- After ~13 requests, RAM full → kernel OOM killer → PHP-FPM killed → Nginx returns 502

### Evidence
- `access_bulk` returns `{"ok":true,"configs":40}` but box crashes immediately after
- Single `proxy.access` calls succeed for first ~13, then timeout/502
- NAT TẮT + `access_bulk` → Box survives (no bot scan load)
- NAT BẬT + bot scan → Box crashes faster

## Bot Scan vs Auth Mode

### Critical Misunderstanding
IP whitelist (`iponly`) does NOT prevent bot scanning:
- Bots connect to TCP ports directly via IP:port
- Box must accept TCP handshake regardless of auth mode
- Auth mode only determines whether the bot can USE the proxy after connecting
- Bot TCP connections still consume CPU/resources on the box

### Correct Approaches to Block Scans
1. **NAT OFF** (`nat_port: 0`) → Firewall drops all TCP from WAN → 0% CPU load
2. **MikroTik firewall whitelist** → iptables DROP before packets reach box → 0% CPU load
3. **Hardware replacement** → Mini PC x86 with proper firewall → handles any load

## Recommended Workflow for Setting Auth

### DO (Manual Web UI)
1. User opens `http://test.taadaa.click/#proxies`
2. Click each proxy → "Cấu hình truy cập" → set mode + password
3. Natural delay between clicks → PHP-FPM handles fine

### DO NOT (API Automation)
1. ❌ `access_bulk` → Restarts all proxies → OOM crash
2. ❌ `proxy.access` x32 via script → Memory leak → OOM after ~13 calls
3. ❌ Watchdog loop checking box → Additional load on struggling box
4. ❌ Background scripts with 2s/5s/30s interval → Still causes load

## Hardware Specs (Box MobiProxy)
- CPU: MediaTek MT7621 (MIPS, 2 cores)
- RAM: 128MB
- OS: OpenWrt 21.02.0
- PHP: 7.4.28
- Web: Nginx + PHP-FPM
- Proxy: 3proxy (32-40 instances)

## Replacement Recommendation
- Mini PC x86: Intel N100/J4125, 8GB RAM, 4x 2.5GbE LAN
- Price: 1.5M-2.5M VND (Shopee: "mini pc 4 lan 2.5g n100 firewall")
- Runs Ubuntu + iptables (proper firewall at network level)
- Can handle 100+ proxy instances without OOM
