# M7 Hardware Exception: SSID Dat & Anti-Premature-Rescue Incident Runbook

## Context & Physical Root Cause
Machine 7 (Samsung Galaxy S7, serial `9885f63030454d3055`) suffers from a persistent hardware/RF driver fault on 5GHz WPA2 association with Aruba AP-315 (`.253` BSSID `b0:b8:67:5b:f8:b0`, `kibe 1` 5180 MHz). The AP rejects association with `ASSOCIATION_REJECTION (status 1)`.

## Authorized Operator Policy
- Machine 7 is permanently authorized and assigned to connect to SSID **`Dat`** (WPA2 passphrase `19051995`) broadcast by the Aruba swarm.
- Dynamic DHCP leases in the farm subnet (`192.168.110.x`) are acquired normally.
- Proxy is mapped to `192.168.110.2:20007`.
- All farm tools, profiles (`farm_wifi_profiles.json`), and test suites (`test_farm_network_gate.py`) must treat Machine 7's connection to `Dat` as expected and valid. Blanket policies forbidding `Dat` for the general fleet do not apply to Machine 7.

## Watchdog Alert Triage Protocol
1. **Timestamp vs Real-time Disambiguation**: When an operator asks about a watchdog alert (e.g., "Why did shift report fail M7?"), check the report's start/end timestamps. The alert reflects the state when that batch started (e.g. 06:03 AM), not the current state.
2. **Read-Only Inspection First**: Never run intrusive reset tools (`_forget_all_networks`, `recover_stuck_s7.py --reboot`, `--force-preempt`) without checking live state (`dumpsys wifi`, `ip addr show wlan0`).
3. **No Operator Task Delegation**: Never tell the operator to power cycle hardware or replug POE cables ("cấm sai bảo user").

## Dual-Band 5GHz Trapping & Association Rejection Blacklist (Incident 2026-10-20)
- **Root Failure Chain**:
  1. SSID `Dat` broadcasts on both 2.4GHz and 5GHz across the Aruba AP swarm.
  2. Samsung Android 8's `SavedNetworkEvaluator` grants a +40 bonus score to 5GHz (`5GHz bonus: 40`), causing M7 to prioritize 5GHz BSSIDs over 2.4GHz BSSIDs even when 2.4GHz has a viable signal.
  3. AP Aruba rejects M7's 5GHz association requests with `ASSOCIATION_REJECTION_EVENT: timedOut=false status=1:UNSPECIFIED_FAILURE`.
  4. M7 can associate and lease DHCP normally on 2.4GHz (e.g. BSSID `b0:b8:67:5b:f8:a1` at 2462 MHz), but roaming/periodic scans pull it back to 5GHz.
  5. After 8 consecutive association rejections, Android marks the entire network disabled:
     `NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION counter:8`.
  6. Once disabled, Android refuses to attempt connection to ANY BSSID of that SSID (including 2.4GHz), falling to `DisconnectedState / InactiveState`.
- **Diagnostics in `dumpsys wifi`**:
  - Search for `NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION` under `WifiConfigManager - Configured networks`.
  - Search for `ASSOCIATION_REJECTION_EVENT` and `5GHz bonus: 40` in `WifiConnectivityManager`.
  - Check `wpa_supplicant` log lines: `CTRL-EVENT-SSID-TEMP-DISABLED ... auth_failures=1 duration=10 reason=CONN_FAILED`. Note that `auth_failures=1` here is an association failure marker, NOT a bad password.
- **Remediation**:
  - Dedicated 2.4GHz-only SSID (e.g. `Dat_2.4G` or `farm_2.4g`) with 5GHz radio disabled for degraded hardware.
  - Hardcode BSSID to 2.4GHz in `WifiConfiguration` / `wpa_supplicant`.
  - Temporary unstick: `service call wifi 13 i32 <netId> i32 1` (enableNetwork) or reboot recovery via `recover_stuck_s7.py`.
