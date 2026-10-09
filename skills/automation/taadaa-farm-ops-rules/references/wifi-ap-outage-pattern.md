# Wi-Fi Access Point Outage Pattern (BOX 1.1 / BOX 2)

**Date:** 2026-09-11
**Event:** Batch alert on 80 machines, 10 machines (M38, M61-64, M67, M68, M70, M72, M74) failed with `proxy-vpn:required router proxy is unreachable... dumpsys connectivity: Wi-Fi not connected`

## Root Cause
- 2 physical Access Points (`BOX 1.1` and `BOX 2`) serving the M6x–M74 zone lost power / LAN / DHCP at ~08:57 (≈7.2h before detection)
- All 10 affected machines had `lastConnected` timestamps clustering at 25132–26048s ago (same moment)
- Machines configured with `kibe 1` / `kibe 2` as fallback but:
  - Some had `hasEverConnected: false` for kibe 2 (never joined)
  - Others had stale `lastConnected since <incorrect>` (incorrectly recorded)
  - Scan Cache showed zero `kibe` BSSIDs visible (`34:fc:b9:75:ab:d0` and `b0:b8:67:5b:f8:b0`)
- Neighboring machines (M60, M65, M66, M69, M71, M73, M75) stayed online on `kibe 1` / `kibe 2` — confirms only the BOX APs dropped

## Diagnostic Commands (ADB dumpsys wifi)
```bash
# Check Wi-Fi state
adb -s <serial> shell dumpsys wifi | grep -E "mWifiInfo SSID:|Supplicant state:"

# Check last connected time per SSID
adb -s <serial> shell dumpsys wifi | grep -E "SSID:.*lastConnected:"

# Scan cache (visible BSSIDs)
adb -s <serial> shell dumpsys wifi | grep -A 20 "Scan Cache:"

# Network disconnection reason
adb -s <serial> shell dumpsys wifi | grep "NETWORK_DISCONNECTION_EVENT"

# IP route / interface state
adb -s <serial> shell ip addr show wlan0
adb -s <serial> shell ip route
```

## Key Indicators in dumpsys wifi
| Indicator | Meaning |
|-----------|---------|
| `mWifiInfo SSID: <unknown ssid>, Supplicant state: DISCONNECTED/UNINITIALIZED, RSSI: -127` | Wi-Fi radio has no active association |
| `lastConnected: 25xxx sec` | Seconds since last successful connection to that SSID |
| `hasEverConnected: false` | Device never successfully joined this network |
| `lastConnected since <incorrect>` | Stale/invalid timestamp, ignore |
| `NETWORK_DISCONNECTION_EVENT reason=3` | Reason code 3 = DEAUTH_LEAVING (AP kicked client or AP went down) |
| `trackBssid: disable <bssid> reason code 1` | Driver disabled BSSID due to repeated failures |

## Recovery Procedure
1. Physically check `BOX 1.1` and `BOX 2` power + LAN cables
2. Reboot both APs
3. Wait for DHCP lease renewal (machines have `autoReconnect: 1`)
4. Verify: `adb -s <serial> shell ip addr show wlan0` → should show `state UP` + `inet 192.168.110.x`

## Prevention
- Add AP health check to preflight: ping AP management IP, verify DHCP server responding
- Monitor `lastConnected` delta across fleet — cluster of similar timestamps = AP outage
- Ensure fallback SSIDs (`kibe 1`/`kibe 2`) have `hasEverConnected: true` on all machines in zone