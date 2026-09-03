# Two-Step Proxy Attachment & Device Lock Handling (Session 2026-09-03)

## Context
User asked to restart ADB on machines and re-attach routing proxy for 16 TikTok video machines (6,9,13,20,24,35,39,43,46,52,56,62,65,69,72,74).

## Two-Step Standard Workflow

### Step 1: ADB Global Proxy (Plain host:port — BYPASSABLE)
```bash
python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py --machines 6,9,13,20,24,35,39,43,46,52,56,62,65,69,72,74
```
- Sets `192.168.110.2:2000N` (MikroTik Sing-box inbound port = 20000 + machine_id)
- Also disables captive portal detection (`captive_portal_mode=0`, `captive_portal_detection_enabled=0`)
- **Result**: 16/16 SUCCESS
- **Limitation**: TikTok can bypass system `http_proxy` and connect directly — NOT for production TikTok flows

### Step 2: Authenticated Proxy via ViChanger VPN (tun0 tunnel — NON-BYPASSABLE)
```bash
python D:/Taadaa/gan-proxy/scripts/gan_proxy_fleet.py run --machines 6 9 13 20 24 35 39 43 46 52 56 62 65 69 72 74 --workers 8
```
- Uses authenticated proxy from `PROXYgandienthoai.xlsx` (format: `host:port:user:pass`, ≥3 colons = `authenticated_http`)
- Launches `vn.vichanger.app` + broadcasts `START_VPN` → creates `tun0` VpnService tunnel
- Verifies via `GET_IP` broadcast (must return proxy IP, not farm Direct IP)
- **Result**: 7 SUCCESS, 9 SKIPPED_DEVICE_LOCKED

## Device Lock Conflict Analysis

### Locked Machines & Lock Owners
| Machine | Serial | Lock Owner (Project) | PID | Status |
|---------|--------|---------------------|-----|--------|
| 6 | 9885e64c484c544d32 | tiktok-luot nuoi acc | 63428 | running |
| 9 | 988627414444594c51 | tiktok-luot nuoi acc | 63428 | running |
| 20 | ce0318237dec1ce60c | tiktok-luot nuoi acc | 63428 | running |
| 35 | ce061606c3322c1603 | tiktok-luot nuoi acc | 176848 | blocked |
| 46 | ce0916092531413504 | tiktok-luot nuoi acc | 63428 | running |
| 62 | ce12160c4a505d2604 | tiktok-luot nuoi acc | 63428 | running |
| 65 | ce12160c4a45432204 | tiktok-luot nuoi acc | 176848 | blocked |
| 72 | ce12160cd19f847f0c | tiktok-luot nuoi acc | 63428 | running |
| 74 | ce061606c21e153d03 | tiktok-follow-recovery | 44540 | running |

### Resolution Options
1. **Wait for lock release** — jobs finish naturally, lock released
2. **Use watch mode** — `gan_proxy_fleet.py watch --machines 6 9 20 35 46 62 65 72 74` auto-recovers on reconnect/lock release
3. **Stop conflicting job** — kill the TikTok job holding the lock, then re-run

### Key Learning
- The device lock system (`automation_core.device_lock`) prevents concurrent access
- `gan_proxy_fleet.py run` respects locks — it skips rather than forcing takeover (correct behavior)
- `gan_proxy_fleet.py watch` is designed for this: it waits for events (reconnect, boot_id change) and takes over when lock is available
- **Never bypass VPN gate** — the lock conflict is a scheduling issue, not a reason to skip authenticated proxy

## Verification Commands

### Quick Plan (read-only)
```bash
python D:/Taadaa/gan-proxy/scripts/gan_proxy_fleet.py plan --machines 6 9 13 20 24 35 39 43 46 52 56 62 65 69 72 74
```

### Probe All Clusters (external proxy health)
```bash
python C:/Users/Kibe/AppData/Local/hermes/skills/devops/farm-proxy-attachment/scripts/probe_proxy_clusters.py
```

### Probe Fleet Wi-Fi/DHCP
```bash
python C:/Users/Kibe/AppData/Local/hermes/skills/devops/farm-proxy-attachment/scripts/probe_fleet_wifi.py
```

## Files Touched
- `D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py` — ADB global proxy setter
- `D:/Taadaa/gan-proxy/scripts/gan_proxy_fleet.py` — Fleet proxy runner (ViChanger VPN)
- `D:/Taadaa/gan-proxy/scripts/vi_changer_runner.py` — Single-device ViChanger protocol
- `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx` — Source of truth mapping (80 machines)