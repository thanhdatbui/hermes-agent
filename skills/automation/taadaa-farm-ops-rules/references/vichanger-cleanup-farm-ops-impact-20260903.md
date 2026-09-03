# ViChanger Cleanup — Farm Ops Impact (2026-09-03)

User directive: **Remove ViChanger completely from all repos**, keep only Singbox/MikroTik transparent proxy.

## Farm Operations Impact

The VPN preflight gate (`require_vichanger_connected` → `require_android_vpn`) is the **first check** before any TikTok consumer script runs on a machine. Removing ViChanger changes this gate:

### Old Flow (ViChanger)
```
Machine mapped in PROXYgandienthoai.xlsx
    ↓
require_vichanger_connected(adb, serial)
    ↓
check_android_vpn(required=True, interface="tun0", verify_live_ip=True)
    ↓
ViChanger GET_IP broadcast → result=200 + proxy_ip ≠ farm direct IP → PASS
    ↓
Run TikTok script (feed/follow/login/reg)
```

### New Flow (Singbox Only)
```
Machine mapped in PROXYgandienthoai.xlsx
    ↓
require_singbox_proxy(adb, serial)  # NEW function
    ↓
check_android_vpn(required=True, interface="wlan0", verify_live_ip=True)
    ↓
1. ADB global http_proxy = 192.168.110.2:2000N ✓
2. captive_portal_mode=0, captive_portal_detection_enabled=0 ✓
3. Singbox inbound port 2000N OPEN from PC ✓
4. Egress IP via Singbox = public proxy IP (≠ 42.114.218.81) ✓
5. wlan0 UP + Wi-Fi VALIDATED ✓
    ↓
Run TikTok script (feed/follow/login/reg)
```

## Alert [MÁY N] Procedure Update

When receiving `[MÁY N]` alert:
1. **B1 (Inspect):** `python D:/Taadaa/tools/inspect_machine.py <N>` — check current screen, log, VPN/proxy state
2. **B2 (Root Cause):** Check if Singbox port is reachable, egress IP is public, wlan0 is UP
3. **B3 (Patch Script):** Fix automation-core preflight / consumer vpn_preflight to use Singbox verification
4. **B4 (Test):** `python D:/Taadaa/gan-proxy/scripts/gan_proxy_fleet.py run --machines <N> --workers 1`
5. **B5 (Verify):** Egress IP check via curl from PC + device

## Key Verification Commands

```bash
# Check ADB proxy setting
adb -s <serial> shell settings get global http_proxy

# Check captive portal
adb -s <serial> shell settings get global captive_portal_mode
adb -s <serial> shell settings get global captive_portal_detection_enabled

# Check Singbox port from PC
curl -x http://192.168.110.2:2000N http://api.ipify.org

# Check wlan0 on device
adb -s <serial> shell ip addr show wlan0

# Check Wi-Fi connectivity
adb -s <serial> shell dumpsys connectivity | grep -A5 "NetworkAgentInfo.*WIFI"
```

## Files Requiring Updates (Per Repo)

| Repo | File | Change |
|------|------|--------|
| `automation-core` | `src/automation_core/preflight.py` | Remove ViChanger GET_IP broadcast (lines 517-544), keep router-mode |
| `tiktok-luot nuoi acc` | `python_runner/core/vpn_preflight.py` | Replace `require_vichanger_connected()` with Singbox check |
| `tiktok-luot nuoi acc` | `python_runner/core/benign_popup.py` | Remove ViChanger constants/detection |
| `gan-proxy` | `scripts/vi_changer_runner.py` | **DELETE** |
| `gan-proxy` | `scripts/gan_proxy_fleet.py` | Rewrite: remove ViChanger, Singbox-only fleet management |
| `tiktok-log-in` | `login_runner/cli.py`, `account_reconcile.py` | Update VPN preflight calls |
| `Tiktok_Reg` | `tiktok_login_v1.py` | Update VPN check to router-mode |

## Direct IP Leak Detection (Critical)

**Always verify egress IP ≠ farm direct IP (42.114.218.81)**

If Singbox upstream dies, MikroTik kill-switch should DROP traffic. But if kill-switch fails or misconfigured:
- Device falls back to direct Wi-Fi
- TikTok sees farm IP → rate limits entire farm
- **Must check egress IP on every machine after proxy assignment**

## References

- `farm-proxy-attachment` skill: `references/vichanger-cleanup-plan-20260903.md`
- `tiktok-farm-hermes-cron-migration` skill: `references/vichanger-cleanup-plan-20260903.md`
- `tiktok-login-reconcile` skill: `references/vichanger-cleanup-impact-login-reconcile-20260903.md`