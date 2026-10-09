# MikroTik Web Manager - Full Feature Set (2026-09-10)

## Overview
Local Python web server (`D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py`) running on port 2310 (canonical URL: `http://kibe:2310` or `http://localhost:2310`), serving an embedded single-page application with three tabs: Dashboard, Schedules, API & cURL.

## Architecture
- **Port**: 2310 (canonical, migrated from legacy 8090)
- **Server**: `ThreadingHTTPServer` (critical for concurrent requests — `HTTPServer` single-threaded blocks on MikroTik API calls causing browser timeouts)
- **Frontend**: Embedded HTML/CSS/JS (dark theme, responsive, Vietnamese UI)
- **Auth**: Basic Auth to MikroTik REST API (`admin:N0spam@@` at `192.168.110.2:9090`)
- **Whitelist**: `ALLOWED_IPS = ["192.168.110.", "100.", "127.0.0.1", "::1"]` — LAN + Tailscale CGNAT + localhost

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves embedded HTML |
| `/api/status` | GET | MikroTik health check (RouterOS version, CPU, memory) |
| `/api/proxies` | GET | Lists all 60 PPPoE interfaces with port, status, IP, uptime |
| `/api/change-ip` | POST | Reconnects interface (Body: `{"interface": "pppoe-out1"}`) |
| `/api/schedules` | GET | List all schedules |
| `/api/schedules` | POST | Add new schedule (Body: `{"time": "08:00", "days": [0,1,2,3,4,5,6], "interface": "pppoe-out1", "enabled": true}`) |
| `/api/schedules/toggle` | POST | Bật/tắt lịch (Body: `{"id": "...", "enabled": true/false}`) |
| `/api/schedules/delete` | POST | Xóa lịch (Body: `{"id": "..."}`) |

## Three Tabs

### 1. Dashboard (Dashboard)
- Stats cards: Running / Down / Disabled / Total / RouterOS version
- Search/filter input (filters by name, IP, port, status)
- Table columns: `#`, `Interface`, `Proxy Port`, `Status`, `Public IP`, `Uptime`, `Action`
- Change IP button per row (disabled for DISABLED interfaces)
- Auto-refresh every 30s

### 2. Schedules (⏰ Schedules)
- **Add Schedule Modal**: Time picker, day checkboxes (Mon-Sun, all checked by default), interface dropdown (only RUNNING interfaces)
- **Schedule Table**: Time, Days, Interface, Status (enabled/disabled badge), Created, Actions (toggle, delete)
- **Persistence**: JSON file `schedules.json` in script directory
- **Background Runner**: Checks every 30s, executes `reconnect_pppoe()` when time matches and day matches
- **Schedule Format**:
```json
{
  "id": "1725987654321",
  "time": "06:00",
  "days": [0,1,2,3,4,5,6],
  "interface": "pppoe-out1",
  "enabled": true,
  "created_at": "2026-09-10 21:00:54"
}
```

### 3. API & cURL (📡 API & cURL)
- Common endpoints: `/api/status`, `/api/proxies` with one-click copy
- Per-proxy cURL commands for running interfaces only
- Format: `curl -x http://admin@1:admin@1@192.168.110.2:10001 http://api.ipify.org` (for ports < 20000 with auth)
- Filter input to search by interface name, IP, port

## Uptime via Batch Monitor (Key Optimization)

### Problem
Calling `/interface/pppoe-client/monitor` individually for 35 interfaces = 35 HTTP requests, slow, potential timeout.

### Solution
Single POST with comma-separated `.id` values:
```python
ids = ",".join(p.get(".id") for p in running_interfaces if p.get(".id"))
result = mt_api("/interface/pppoe-client/monitor", method="POST", data={".id": ids, "duration": "1"})
```

### Response Format
```json
[
  {"local-address": "171.231.181.33", "uptime": "1h56m52s", ...},
  {"local-address": "171.231.191.184", "uptime": "1h56m50s", ...},
  ...
]
```

### Matching Logic
Map monitor results back to interfaces by matching `local-address` against `ip_map[interface_name]` (e.g., `171.231.181.33/32` contains `171.231.181.33`).

### Fallback
If batch call fails, fallback to individual monitor calls per interface.

## Running the Server
```bash
cd D:\Taadaa\AI-Tools\tools\mikrotik_web
python server.py
```
Auto-opens browser at `http://localhost:8090`

## Access via Tailscale
1. Server must be running on `0.0.0.0:8090`
2. Tailscale whitelist `100.` covers entire CGNAT range
3. Access from phone: `http://kibe:8090` (after setting Machine Name in Tailscale Admin Console)
4. iOS: Add to Home Screen → PWA icon for one-tap access

## File Structure
```
D:\Taadaa\AI-Tools\tools\mikrotik_web\
├── server.py              # Main server (embedded HTML, API, schedules runner)
├── schedules.json         # Persisted schedules (auto-created)
├── start_mikrotik_web.bat # Windows launcher
└── __pycache__/
```

## Restart on Config Changes
Sau khi sửa `server.py`, TUYỆT ĐỐI KHÔNG dùng `taskkill -F -IM python.exe` vì sẽ làm chết toàn bộ các tiến trình Python khác (watchers, automation-core, Hermes, v.v.).
Dùng lệnh PowerShell chuẩn để chỉ kill đúng process đang listen port 2310 và restart ngầm an toàn:
```powershell
powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 2310 -State Listen).OwningProcess -Force -ErrorAction SilentlyContinue; Start-Process (Get-Command python).Source -ArgumentList 'D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py' -WindowStyle Hidden"
```
> **Lưu ý quan trọng:** Bắt buộc có cờ `-State Listen` trong `Get-NetTCPConnection`. Nếu bỏ `-State Listen`, PowerShell sẽ quét cả các kết nối `TimeWait` (có `OwningProcess = 0`), khiến lệnh `Stop-Process` báo lỗi hoặc xử lý nhầm. Sau khi restart, chờ 2s rồi verify bằng `curl -s http://127.0.0.1:2310/api/status`.

## Related Files
- Config repo: `D:\Taadaa\AI-Tools\docs\infrastructure\mikrotik\mikrotik-master-network-handbook.md` (Section 5)
- Exported firewall rules: `D:\Taadaa\AI-Tools\docs\infrastructure\mikrotik\firewall-fptlan-proxy-rules-2026-09-10.rsc`
- Skill: `farm-proxy-attachment` (Pitfalls section updated with full feature set)