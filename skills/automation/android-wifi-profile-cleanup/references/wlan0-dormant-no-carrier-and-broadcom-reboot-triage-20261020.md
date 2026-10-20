# wlan0 NO-CARRIER / DORMANT Post-Association-Rejection Triage (2026-10-20)

## Symptom: Handshake COMPLETED but Interface Stuck in NO-CARRIER / DORMANT
When an Android device (especially Samsung S7 SM-G930F/S) has suffered from repeated `ASSOCIATION_REJECTION` (e.g. `counter:8`) or continuous association flapping between a rogue SSID (`Dat`) and a target farm SSID (`kibe 1`), the following state can occur even after:
1. Purging all rogue/stale Net IDs via `service call wifi 14 i32 <NET_ID>`.
2. Bypassing blocklists and re-joining the target farm SSID via `adb-join-wifi`.
3. Seeing `wpa_supplicant` log `WPA: Key negotiation completed` and `CTRL-EVENT-CONNECTED`.

### Raw State Evidence
```text
14: wlan0: <NO-CARRIER,BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state DORMANT group default qlen 1000
    link/ether ac:5f:3e:60:59:1b brd ff:ff:ff:ff:ff:ff
mWifiInfo: [SSID: <unknown ssid>, BSSID: <none>, Supplicant state: DISCONNECTED, RSSI: -127, Link speed: -1Mbps...]
mNetworkInfo [type: WIFI[] - WIFI, state: DISCONNECTED/SCANNING, reason: (unspecified), extra: "kibe 1"...]
```

## Root Cause
- The Broadcom PCIe Wi-Fi chip driver (`bcmdhd` / `brcmfmac`) enters a low-power dormant link state where the upper network stack does not detect carrier signals despite layer 2 association in `wpa_supplicant`.
- Soft radio toggles (`svc wifi disable && svc wifi enable`) only cycle the Android Wi-Fi service and supplicant daemon; they do not power-cycle the PCIe bus or re-initialize the Broadcom firmware on kernel level.
- Consequently, DHCP client (`netd` / `IpClient`) is never triggered or drops DHCP discover packets due to `NO-CARRIER`.

## Resolution: Level 2 Hardware/Bypass Reboot
- Soft recovery (Level 1) will fail because the network stack cannot bind.
- Do NOT loop `adbjoinwifi` or soft radio toggles (this causes AP-side association rejection counters to increment further).
- Immediately invoke Level 2 recovery:
  ```bash
  python D:/Taadaa/tools/recover_stuck_s7.py --machine <N> --reboot
  ```
- Because device locks prevent reboot loops (`REBOOT_COOLDOWN_SECONDS = 300`), this reboot cleanly re-initializes the Broadcom PCIe bus, boots into a clean kernel state, loads the newly saved singular farm SSID profile, and completes carrier detection and DHCP lease acquisition.

## Rolling Rename Lock Interleaving
- Background farm tasks (such as `tiktok_rename_rolling_watchdog.py`) actively scan for candidate accounts during safe windows (e.g. 09:30–11:20) and acquire device locks (`machine_<N>.lock.json`).
- If inspecting or repairing devices during these windows, be aware that runner timeouts or lock contention can occur. Always check `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` and verify PID liveness before declaring a lock deadlock.
