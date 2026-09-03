# ViChanger Cleanup Plan (2026-09-03)

User directive: **Remove ViChanger completely from all repos**, keep only Singbox/MikroTik transparent proxy.

## Files to Clean

| Repo | File | Action |
|------|------|--------|
| `gan-proxy` | `scripts/vi_changer_runner.py` | **DELETE** — standalone ViChanger runner |
| `gan-proxy` | `scripts/gan_proxy_fleet.py` | **REWRITE** — remove ViChanger imports/calls, keep only ADB global proxy + Singbox verification |
| `tiktok-luot nuoi acc` | `python_runner/core/benign_popup.py` | **REMOVE** ViChanger constants (`VICHANGER_PACKAGE`, `VICHANGER_LSPOSED_NOTICE`, `detect_vichanger_lsposed_notice`) |
| `tiktok-luot nuoi acc` | `python_runner/core/vpn_preflight.py` | **REWRITE** — replace `require_vichanger_connected()` with router transparent proxy check (wlan0 + MikroTik Singbox) |
| `automation-core` | `src/automation_core/preflight.py` | **REMOVE** ViChanger GET_IP broadcast (lines 521-522), keep only router-mode validation |

## New Architecture (Singbox Only)

```
Device (ADB global http_proxy=192.168.110.2:2000N)
    ↓
MikroTik RouterOS (192.168.110.2:9090) — Firewall kill-switch: DROP if no proxy
    ↓
Singbox Container (inbound ports 20001..20080)
    ↓
Upstream PPPoE/4G (ports 10001..10035, various providers)
```

## Verification Method (No ViChanger)

From PC: `curl -x http://192.168.110.2:<port> http://api.ipify.org` → must return **public proxy IP** (not farm direct IP 42.114.218.81)

From device: ADB shell toybox nc to 192.168.110.2:<port> → HTTP GET → parse response for public IP

## Current Status (Verified 2026-09-03)

- ✅ 80/80 machines: ADB global http_proxy set correctly (192.168.110.2:20001-20080)
- ✅ 80/80 machines: captive_portal_mode=0, captive_portal_detection_enabled=0
- ✅ 16/16 target machines: ViChanger STOP_VPN sent, app force-stopped, tun0 removed
- ✅ Singbox inbound ports 20001-20080: all OPEN from PC
- ✅ Egress IP test (16 machines): All return **different public IPs** via Singbox (not farm direct IP)

## Next Steps

1. Delete `gan-proxy/scripts/vi_changer_runner.py`
2. Rewrite `gan-proxy/scripts/gan_proxy_fleet.py` → plan/run/watch without ViChanger
3. Remove ViChanger code from `tiktok-luot nuoi acc/python_runner/core/`
4. Remove ViChanger GET_IP broadcast from `automation-core/src/automation_core/preflight.py`
5. Run full fleet verification: `gan_proxy_fleet.py run --all --workers 20`