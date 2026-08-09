---
name: network-device-ap-conversion
description: |
  Provides a structured workflow for configuring a network device (typically a router)
  into an Access Point (AP) mode, either by using a dedicated AP mode setting or
  by manually disabling router functionalities (DHCP, NAT) and setting a static IP.

  This skill also covers troubleshooting common issues encountered during this process,
  such as login difficulties, hidden UI elements, and IP address conflicts.
version: 1.0.0
---

# Network Device to Access Point Conversion Workflow

This skill outlines the process of converting a consumer-grade router into an Access Point (AP) to extend Wi-Fi coverage within an existing network.

## Goal

To configure a secondary network device (the target device) to act as an Access Point (AP) within a primary network, sharing the primary network's subnet, DHCP services (from the primary router), and Wi-Fi SSID (optional).

## Prerequisites

1.  **Primary Router:** An existing main router (e.g., Ruijie) handling NAT, DHCP, and Internet access.
2.  **Target Device:** The device to be converted to an AP (e.g., ZTE H196A).
3.  **Login Credentials:** Administrative username and password for the target device.
4.  **Network Information:**
    *   Primary router's LAN IP address (and thus the network's gateway, e.g., `192.168.110.1`).
    *   Primary network's subnet mask (e.g., `255.255.255.0`).
    *   Desired Wi-Fi SSID and password for the AP (to match existing Wi-Fi, if applicable).
5.  **Physical Connection:** Target device is connected to the network, initially via its WAN port to a LAN port of the primary router for initial configuration (this will be changed later).

## Workflow Steps

### Phase 1: Initial Access and Information Gathering

1.  **Access the Target Device's Web Interface:**
    *   Navigate your browser to the target device's current IP address (often found via `arp -a` if it's already connected, or default IP from documentation).
    *   **Pitfall:** Sometimes login attempts result in redirection or apparent failure. Try re-navigating to the base URL `http://<device_ip>/` after an initial login attempt.
    *   **Pitfall:** Be aware of popups or overlay messages (e.g., "Last login IP address") that might obscure the interface; dismiss them as needed.

2.  **Log in to the Device:**
    *   Enter the administrative username and password.

3.  **Identify Current Network Configuration:**
    *   Locate sections related to "Network", "LAN", "WAN", "DHCP", "Operation Mode", or "System Settings".

### Phase 2: Configure AP Mode (or Manual AP Setup)

1.  **Check for Dedicated "AP Mode" / "Work Mode" Setting:**
    *   Look for a dedicated "Operation Mode", "Work Mode", or "AP Mode" setting, usually under "System Settings", "Network", or "Advanced".
    *   If found, select "AP Mode" and apply the changes. This is the simplest method.
    *   **Verification:** After enabling AP Mode, the device might restart. You'll likely need to access it at a new IP (possibly assigned by the primary DHCP) or its original LAN IP, but with DHCP disabled.

2.  **Manual AP Configuration (if no dedicated AP Mode):**
    *   **Disable DHCP Server:** Navigate to the "LAN" or "DHCP" settings. Locate the DHCP server option and **disable it**.
        *   **Pitfall:** Configuration sections might be hidden by default (e.g., `display: none` in CSS). Use browser developer tools or `browser_console` (`document.getElementById('<id>').style.display = 'block';`) to reveal them if necessary.
    *   **Set Static LAN IP Address:**
        *   Navigate to "LAN" settings (e.g., "LAN" -> "IPv4").
        *   Change the IP assignment from DHCP (if applicable) to **Static IP**.
        *   Assign a static IP address that is:
            *   Within the primary router's subnet (e.g., `192.168.110.X` if primary is `192.168.110.1`).
            *   **Crucially, outside the primary router's DHCP range.**
            *   **NOT currently in use by any other device.**
        *   **Pitfall:** Do NOT reuse an IP that appears in `arp -a` unless you confirm the MAC address matches the target device, or you verify the old device is off the network. An IP conflict will render the device inaccessible.
        *   **Recommendation for finding unused IP:** Scan the network (e.g., `ping` sweep, then `arp -a` to exclude active IPs, or use a network scanner tool) to find a truly available IP.
    *   **Set Subnet Mask:** Match the primary router's subnet mask (e.g., `255.255.255.0`).
    *   **Set Gateway and DNS:** Point these to the primary router's LAN IP address (e.g., `192.168.110.1`).
    *   **Apply Changes:** Save the network settings. The device may restart.

### Phase 3: Configure Wireless (WLAN) Settings

1.  **Access WLAN/Wi-Fi Settings:**
    *   Navigate to the "WLAN", "Wi-Fi", or "Wireless" section of the target device's interface.
2.  **Configure SSID:**
    *   Set the Wi-Fi network name (SSID). To extend an existing network, make this identical to the primary network's SSID.
3.  **Configure Password and Security:**
    *   Set the Wi-Fi password (WPA2-PSK, AES encryption is generally recommended and matches most modern networks like Aruba).
4.  **Apply Changes:** Save the wireless settings.

### Phase 4: Final Physical Connection and Verification

1.  **Change Cable Connection:**
    *   **Disconnect the Ethernet cable from the target device's WAN port.**
    *   **Connect the Ethernet cable from a LAN port of the primary router to one of the LAN ports of the target device.** The WAN port of the target device should remain unused.
2.  **Verify Connectivity:**
    *   Connect a device (e.g., phone, laptop) to the newly configured AP's Wi-Fi.
    *   Check if it gets an IP address from the primary router's DHCP server.
    *   Verify Internet access.
    *   Confirm you can access the AP's management interface at its newly assigned static IP.

## Troubleshooting

*   **Device inaccessible after IP change:**
    *   Ping the new IP to verify reachability.
    *   Check your local ARP table (`arp -a`) for the device's MAC address to determine its actual current IP.
    *   If still inaccessible, try connecting a device directly to the AP via Ethernet and checking its IP configuration, or attempt to factory reset the AP and start over.
*   **H196A Specifics:** For detailed notes on the ZTE ZXHN H196A interface and workarounds, refer to `references/h196a-specifics.md`.
*   **Wi-Fi not working / no Internet:**
    *   Double-check DHCP is disabled on the AP.
    *   Verify the static IP, subnet, gateway, and DNS settings on the AP are correct and match the primary network.
    *   Ensure the physical cable connection is LAN-to-LAN.

## Safety Principles

1. Preserve management access above all.
2. Do not reset devices unless explicitly requested.
3. Do not change the main router or existing AP/controller settings unless the task explicitly requires it.
4. Verify after each state-changing step with real network/tool output.
5. Stop and report if login fails, target IP is uncertain, or a change may strand the device.
6. Prefer a built-in `AP`, `Bridge`, or equivalent work mode over manual DHCP-off configuration when the firmware provides it.
7. If changing LAN IP or work mode may move the device, record current IP, MAC, intended new IP, gateway, and recovery path before applying.

## Choosing the Mode Safely

Preferred order:

1. Built-in AP/Bridge mode for standalone AP use.
2. If multiple bridge-like options exist, distinguish them before applying:
   - `Controller(Bridge)` may mean the unit is a bridge-mode controller/AP — evaluate FIRST for a standalone AP behind a non-ZTE main router, but selecting it in the UI may not persist; always re-open Work Mode and track the unit by MAC after Apply.
   - `Mesh Auto(Bridge)` may mean vendor mesh enrollment/auto-discovery, not generic AP.
   - `Agent` may indicate mesh agent mode and can already bridge client traffic, depending on firmware.
3. Manual AP mode only if no built-in mode is available:
   - Disable DHCP server; disable NAT/router/WAN functions if exposed.
   - Set a static management IP in the main LAN subnet that is known free (check ARP/ping/router client list first; avoid IPs that appear in ARP even if intermittent; prefer reserving in the main router if the UI supports it).
   - Gateway and DNS point to the main router. After applying, test both old and new IPs; ARP MAC should match the target label/MAC.

## ZTE H196A Notes

ZTE H196A V9 Brazil-like firmware may expose:
- `Management & Diagnosis → Work Mode`
- `Local Network → LAN → IPv4` with `DHCP Server`, `LAN IP Address`, `Subnet Mask`, DNS fields

H196A Pitfalls:
- Do not trust `Apply` buttons in this specific ROM blindly. Always re-navigate to the setting page to verify persistence.
- Avoid forcing changes by JS if the UI is unresponsive.
- If in doubt regarding credentials or SSID parameters for synchronization, stop and request credentials rather than guessing encryption types or passphrases.
- SSID names in this firmware may require specific handling of special characters.
- Do not assume the old IP change saved just because fields were typed. Confirm with ping/web access and by re-reading the page.
- Do not default to LAN-LAN cabling until the persisted bridge mode and uplink expectation are verified.

Additional H196A Brazil/Ruijie/Aruba field notes: `references/zte-h196a-brazil-ruijie-aruba.md` (merged from the former `router-ap-conversion` skill).

## User Expectation Pattern

For users asking for senior network-engineer/autonomous execution, do not ask confirmation after every step. Narrate briefly, act, verify, and only stop for missing credentials, uncertain IP, or access-loss risk.
