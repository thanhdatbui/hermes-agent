# ViChanger Cleanup Impact on TikTok Login Reconcile (2026-09-03)

User directive: **Remove ViChanger completely from all repos**, keep only Singbox/MikroTik transparent proxy.

## Impact on Login Reconcile Flow

The TikTok login reconcile flow (`tiktok-log-in`, `Tiktok_Reg`) uses VPN preflight that currently calls ViChanger. This must be updated:

| File | Current ViChanger Usage | New Approach |
|------|------------------------|--------------|
| `tiktok-log-in/login_runner/cli.py` | `require_vichanger_connected()` from `vpn_preflight.py` | Check Singbox port + egress IP |
| `tiktok-log-in/login_runner/account_reconcile.py` | VPN check before login | Singbox verification |
| `Tiktok_Reg/tiktok_login_v1.py` | `require_android_vpn(verify_live_ip=True)` → ViChanger GET_IP | Router-mode validation only |
| `automation-core/src/automation_core/preflight.py` | Lines 517-544: ViChanger GET_IP broadcast | Remove, keep router-mode (wlan0 + ping + atx-agent curl) |

## VPN Preflight Migration

**Old (ViChanger):**
```python
# automation-core/preflight.py lines 517-544
if effective_interface == "tun0":
    for attempt in range(1, 4):
        get_ip = adb.shell(["am", "broadcast", "-a", "vn.vichanger.app.GET_IP", "-n", "vn.vichanger.app/.AdbCaller"], ...)
        if "result=200" in out and match:
            proxy_ip = match.group(1)
            ip_verified = True
```

**New (Singbox only):**
```python
# Router transparent proxy mode (wlan0)
if effective_interface == "wlan0":
    # 1. Ping gateway + 8.8.8.8
    # 2. atx-agent curl via global proxy to get egress IP
    # 3. Verify egress IP is PUBLIC (not farm direct IP)
    # 4. Wi-Fi VALIDATED capability check
```

## Login Reconcile Verification After Cleanup

When login reconcile runs on a machine:
1. ADB global http_proxy must be set (192.168.110.2:2000N)
2. captive_portal_mode=0, captive_portal_detection_enabled=0
3. Singbox inbound port must be OPEN
4. Egress IP via Singbox must be public proxy IP (NOT 42.114.218.81)
5. Wi-Fi interface (wlan0) must be UP + VALIDATED

## Device Lock Interaction

- `gan_proxy_fleet.py watch` will auto-reassign proxy on device reconnect
- Login reconcile must wait for proxy readiness (watcher sets `proxy_ready` marker)
- If `SKIPPED_DEVICE_LOCKED` by feed/follow job → wait or use watch mode

## References

- `farm-proxy-attachment` skill: `references/vichanger-cleanup-plan-20260903.md`
- `tiktok-farm-hermes-cron-migration` skill: `references/vichanger-cleanup-plan-20260903.md`