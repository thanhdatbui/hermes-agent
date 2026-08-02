# ZTE ZXHN H196A Specifics for AP Conversion

This document outlines specific behaviors and workarounds encountered when configuring the ZTE ZXHN H196A (Brazil ROM) for Access Point (AP) mode. Refer to the main `network-device-ap-conversion` skill for the general workflow.

## 1. Login and Interface Navigation

### Login Redirection / "404 Not Found"
When attempting to log in to the H196A (e.g., at `http://192.168.110.19/`), the device might redirect back to the login page or display a "404 Not Found" error within the main content area even after successful credential submission.

**Workaround:**
*   After submitting credentials, directly re-navigate to the base URL (e.g., `http://192.168.110.19/`) or simply refresh the page. The session should be authenticated, and the main dashboard will appear.
*   **Initial Login Popups:** Be aware of popups, such as "Last login IP address: 192.168.110.25", that may obscure the interface immediately after login. These need to be dismissed by clicking an "OK" button (e.g., `ref=e1`) or by injecting JavaScript: `document.querySelectorAll('.white_content_security, .black_overlay').forEach(e=>e.style.display='none');`.

### Internal Navigation via JavaScript `openLink`
The H196A's interface uses JavaScript functions for internal page navigation rather than standard HTTP GET requests for new URLs. Attempting to manually construct URLs (e.g., `http://192.168.110.19/lanConfig`) often results in a "404 Not Found".

**Workaround:**
*   Use the `openLink()` JavaScript function available in the browser's context. This function takes a menu ID as an argument.
*   The menu structure can be inspected via `window.menuTreeJSON` (e.g., in `browser_console`).
*   **Example Usage:**
    *   To navigate to LAN IPv4 settings: `openLink('lanMgrIpv4');`
    *   To navigate to WLAN Basic settings: `openLink('wlanBasic');`

## 2. Revealing Hidden Configuration Sections

Some configuration sections (e.g., "DHCP Server" details under LAN IPv4 settings) might be visually collapsed or hidden using CSS (`display: none`) by default. Clicking their header might not always trigger expansion, or the `browser_snapshot` might not capture the change immediately.

**Workaround:**
*   If a section is expected to be present but is not visible, use `browser_console` to force its display style.
*   **Example for DHCP Server configuration:**
    *   `document.getElementById('DHCPBasicCfg_container').style.display = 'block';`
    *   This will make the hidden input fields and radio buttons visible for interaction.

## 3. Recommended LAN IP for AP Mode

*   During this session, an IP conflict occurred when `192.168.110.200` was assigned (it was already in use by another device with a different MAC).
*   For AP mode, it's crucial to select an IP address that is **static**, **within the primary router's subnet**, and **outside its DHCP range**, and **not currently in use by any other device**.
*   In this instance, `192.168.110.240` was chosen as a likely unused static IP. Always verify with `ping` and `arp -a` (checking MAC addresses) before final assignment.

## 4. Work Mode / AP Mode vs. Manual Configuration

The H196A firmware (Brazil ROM) does not appear to have a prominent "AP Mode" or "Work Mode" option readily accessible in the main "Network" or "System Settings". Therefore, manual configuration (disabling DHCP, setting static IP/DNS) is the required approach.
