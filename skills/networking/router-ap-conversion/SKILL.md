---
name: router-ap-conversion
description: Convert ISP/router CPE devices into access points/bridges behind an existing main router; includes safe web-admin discovery, IP/DHCP/bridge-mode handling, Wi-Fi matching, and verification.
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [networking, router, access-point, bridge-mode, wifi, dhcp]
    category: networking
---

# Router/CPE to Access Point Conversion

Use when the user wants to repurpose a router/CPE as an AP behind a main router while keeping one LAN/subnet.

## Safety principles

1. Preserve management access above all.
2. Do not reset devices unless explicitly requested.
3. Do not change the main router or existing AP/controller settings unless the task explicitly requires it.
4. Verify after each state-changing step with real network/tool output.
5. Stop and report if login fails, target IP is uncertain, or a change may strand the device.
6. Prefer a built-in `AP`, `Bridge`, or equivalent work mode over manual DHCP-off configuration when the firmware provides it.
7. If changing LAN IP or work mode may move the device, record current IP, MAC, intended new IP, gateway, and recovery path before applying.

## Workflow

### 1. Map the current network

- Identify the main router/gateway, subnet, and the host IP.
- Use ARP/MAC matching to identify the target device. Label photos are useful; compare printed MAC to `arp -a` or router client list.
- Check candidate web ports (`80`, `443`, vendor ports such as Aruba Instant `4343`).
- Confirm which discovered IP belongs to the target before logging in.

### 2. Login and inspect firmware

- Login to the target CPE/router.
- Enumerate menus before applying changes. Look specifically for:
  - `Operation Mode`, `Work Mode`, `AP Mode`, `Bridge Mode`
  - `LAN IPv4`, `DHCP Server`, `WAN`, `NAT`, `Firewall`
  - `WLAN Basic`, `SSID`, `Security`, `Encryption`, `Passphrase`
- Some ZTE H196A-style UIs hide pages behind JS functions such as `openLink('<page-id>')`; menu trees in page JS can reveal IDs like `lanMgrIpv4`, `wlanBasic`, and `mpworkmode`.

### 3. Choose mode safely

Preferred order:

1. Built-in AP/Bridge mode for standalone AP use.
2. If multiple bridge-like options exist, distinguish them before applying:
   - `Controller(Bridge)` may mean the unit is a bridge-mode controller/AP.
   - `Mesh Auto(Bridge)` may mean vendor mesh enrollment/auto-discovery, not generic AP.
   - `Agent` may indicate mesh agent mode and can already bridge client traffic, depending on firmware.
3. Manual AP mode only if no built-in mode is available:
   - Disable DHCP server.
   - Disable NAT/router/WAN functions if exposed.
   - Set a static management IP in the main LAN subnet that is known free.
   - Gateway and DNS point to the main router.

### 4. Pick a safe management IP

- Do not guess an unused IP. Check ARP/ping/router client list first.
- Avoid using an IP that already appears in ARP, even if it only responds intermittently.
- Prefer reserving the IP in the main router if the UI supports reservations and the user permits it.
- After applying a new IP, test both old and new IPs; ARP MAC should match the target label/MAC.

### 5. Wi-Fi matching

Before changing Wi-Fi, read existing WLAN configuration from the current AP/controller/main router. Do not infer full security mode from only the SSID.

Collect:

- SSID(s)
- 2.4 GHz / 5 GHz split or unified SSID
- security mode (WPA2-PSK, WPA/WPA2 mixed, WPA3 transition, etc.)
- encryption/cipher (AES/CCMP, TKIP, mixed)
- passphrase
- band/channel/channel width if relevant

If credentials/session access to the current AP/router is missing, stop and request only the missing login or exact Wi-Fi details rather than guessing.

### 6. Apply and verify

After each Apply/Save:

- Wait for page reload/reboot only as needed.
- Ping the management IP.
- Open the web UI and login if required.
- Confirm saved values by re-reading the UI.
- Check DHCP is off (no leases served by the AP) and the main router remains the gateway/DHCP server.
- Confirm Wi-Fi SSID appears and clients can get a main-router subnet IP if possible.

### 7. Physical cabling reminder

For manual AP or bridge mode behind the main router, final cabling is usually:

- Remove cable from the target router WAN port.
- Connect a LAN port of the main router/switch to a LAN port of the converted AP.

Only tell the user to do this after configuration is verified or when the next step requires physical rewiring.

## ZTE H196A notes

ZTE H196A V9 Brazil-like firmware may expose:

- `Management & Diagnosis → Work Mode`
- `Management & Diagnosis → Work Mode`
- `Local Network → LAN → IPv4` with `DHCP Server`, `LAN IP Address`, `Subnet Mask`, DNS fields

### H196A Pitfalls:
- Do not trust `Apply` buttons in this specific ROM blindly. Always re-navigate to the setting page to verify persistence.
- Avoid forcing changes by JS if the UI is unresponsive.
- If in doubt regarding credentials or SSID parameters for synchronization, stop and request credentials rather than guessing encryption types or passphrases.
- Note: SSID names in this firmware may require specific handling of special characters.

Do not assume the old IP change saved just because fields were typed. Confirm with ping/web access and by re-reading the page.

Additional H196A Brazil/Ruijie/Aruba field notes are in `references/zte-h196a-brazil-ruijie-aruba.md`. Key pitfalls from that note: `Controller(Bridge)` is the mode to evaluate first for a standalone AP behind a non-ZTE main router, but selecting it in the UI may not persist; always re-open Work Mode and track the unit by MAC after Apply. Do not default to LAN-LAN cabling until the persisted bridge mode and uplink expectation are verified.

## User expectation pattern

For users asking for senior network-engineer/autonomous execution, do not ask confirmation after every step. Narrate briefly, act, verify, and only stop for missing credentials, uncertain IP, or access-loss risk.
