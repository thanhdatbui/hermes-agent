# ViChanger Cleanup Plan (2026-09-03) — TikTok Farm Proxy Gate

User directive: **Remove ViChanger completely from all repos**, keep only Singbox/MikroTik transparent proxy for TikTok farm automation.

## Background
- Current TikTok farm VPN gate checks `tun0` + `dumpsys connectivity` VPN via ViChanger (`vn.vichanger.app`)
- ViChanger is a niche VpnService app that broadcasts `GET_IP` for live IP verification
- User wants **zero ViChanger** — only MikroTik RouterOS + Singbox transparent proxy

## Files to Clean (5 locations)

| Repo | File | ViChanger References |
|------|------|---------------------|
| `gan-proxy` | `scripts/vi_changer_runner.py` | Entire file — standalone ViChanger runner |
| `gan-proxy` | `scripts/gan_proxy_fleet.py` | Imports `vi_changer_runner`, calls `set_proxy()`, `vpn_connected()`, `PACKAGE`, `ACTION_*` |
| `tiktok-luot nuoi acc` | `python_runner/core/benign_popup.py` | `VICHANGER_PACKAGE`, `VICHANGER_LSPOSED_NOTICE`, `detect_vichanger_lsposed_notice()` |
| `tiktok-luot nuoi acc` | `python_runner/core/vpn_preflight.py` | `require_vichanger_connected()`, calls `recover_missing_android_vpn()` |
| `automation-core` | `src/automation_core/preflight.py` | Lines 521-522: `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` |

## New Architecture (Singbox Only)

```
Device (Samsung S7)
    → ADB global http_proxy=192.168.110.2:2000N (port 20001-20080 per machine)
    → captive_portal_mode=0, captive_portal_detection_enabled=0
    ↓
MikroTik RouterOS (192.168.110.2:9090)
    → Firewall kill-switch: DROP if no proxy set
    ↓
Singbox Container (80 inbound ports 20001..20080)
    → Mixed inbound: HTTP/SOCKS proxy with auth
    ↓
Upstream PPPoE/4G (ports 10001..10035, various providers: test.taadaa.click, mirotik1.taadaa.click, khoalee.duckdns.org)
```

## Verification Method (No ViChanger)

**From PC (egress IP test):**
```bash
curl -x http://192.168.110.2:<port> http://api.ipify.org
# Must return PUBLIC PROXY IP (NOT farm direct IP 42.114.218.81)
```

**From device (toybox nc):**
```bash
adb -s <serial> shell "toybox nc -w 5 -W 5 -q 1 192.168.110.2 <port> << 'EOF'
GET http://api.ipify.org/ HTTP/1.1
Host: api.ipify.org
Proxy-Connection: close

EOF"
# Parse response for public IP
```

## Current Status (Verified 2026-09-03)

- ✅ 80/80 machines: ADB global http_proxy set correctly (192.168.110.2:20001-20080)
- ✅ 80/80 machines: captive_portal_mode=0, captive_portal_detection_enabled=0
- ✅ 16/16 target machines: ViChanger STOP_VPN sent, app force-stopped, tun0 removed
- ✅ Singbox inbound ports 20001-20080: all OPEN from PC
- ✅ Egress IP test (16 machines): All return **different public IPs** via Singbox (not farm direct IP)

| Port | Egress IP | Provider (from Excel) |
|------|-----------|----------------------|
| 20006 | 116.107.123.149 | test.taadaa.click:5106:mobi6 |
| 20009 | 116.107.125.114 | test.taadaa.click:5111:mobi11 |
| 20013 | 171.224.79.190 | test.taadaa.click:5115:mobi15 |
| 20020 | 27.69.65.79 | mirotik1.taadaa.click:10003:admin@1 |
| 20024 | 116.103.50.153 | test.taadaa.click:5128:mobi28 |
| 20035 | 27.69.66.78 | mirotik1.taadaa.click:10003:admin@1 |
| 20039 | 171.224.49.103 | test.taadaa.click:5101:mobi1 |
| 20043 | 27.69.66.78 | test.taadaa.click:5105:mobi5 |
| 20046 | 116.104.219.195 | test.taadaa.click:5108:mobi8 |
| 20052 | 27.69.66.0 | test.taadaa.click:5116:mobi16 |
| 20056 | 117.5.56.134 | test.taadaa.click:5122:mobi22 |
| 20062 | 116.103.50.153 | test.taadaa.click:5128:mobi28 |
| 20065 | 116.111.248.78 | test.taadaa.click:5133:mobi33 |
| 20069 | 125.234.212.106 | test.taadaa.click:5137:mobi37 |
| 20072 | 171.224.49.103 | mirotik1.taadaa.click:10001:admin@1 |
| 20074 | 27.69.66.78 | mirotik1.taadaa.click:10003:admin@1 |

**Farm direct IP (no proxy):** `42.114.218.81` — **none of the 16 machines leaked this IP**

## Next Steps (Execution Order)

1. **Delete** `gan-proxy/scripts/vi_changer_runner.py`
2. **Rewrite** `gan-proxy/scripts/gan_proxy_fleet.py`:
   - Remove all ViChanger imports (`from vi_changer_runner import ...`)
   - Replace `set_proxy()` → ADB global proxy only (already done by AI-Tools script)
   - Replace `vpn_connected()` → Singbox port check + egress IP verification
   - Keep `plan` / `run` / `watch` commands for fleet management
3. **Remove** ViChanger code from `tiktok-luot nuoi acc/python_runner/core/benign_popup.py`
4. **Rewrite** `tiktok-luot nuoi acc/python_runner/core/vpn_preflight.py`:
   - Replace `require_vichanger_connected()` with router transparent proxy check
   - Check: wlan0 UP + Singbox port reachable + egress IP ≠ farm direct IP
5. **Remove** ViChanger GET_IP broadcast from `automation-core/src/automation_core/preflight.py` (lines 517-544)
6. **Run full fleet verification**: `python D:/Taadaa/gan-proxy/scripts/gan_proxy_fleet.py run --all --workers 20`

## Pitfalls to Avoid

- **Never fallback to ViChanger** — if Singbox port closed, block machine (fail-closed)
- **Direct IP Leak detection**: Always compare egress IP with farm direct IP (42.114.218.81)
- **Device Lock conflicts**: Other TikTok jobs (feed, follow, login) hold locks — use `gan_proxy_fleet.py watch` for auto-recovery
- **Proxy mapping**: Excel `PROXYgandienthoai.xlsx` has 80 rows with upstream proxy auth — keep for Singbox upstream config, but device only needs `192.168.110.2:2000N`