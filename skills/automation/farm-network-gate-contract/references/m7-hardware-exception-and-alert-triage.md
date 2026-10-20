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
