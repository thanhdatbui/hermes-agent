# ZTE H196A V9 Brazil ROM behind Ruijie/Reyee + Aruba Instant

Session-derived notes for converting a ZTE ZXHN H196A V9 Brazil-like firmware into an AP/bridge behind a Ruijie/Reyee main router with Aruba Instant already serving the target SSID.

## Observed identifiers

- H196A web UI title: `H196A V9`, version footer observed as `H196A V9 V9.0.0P5_MUL`.
- Label/user account observed: `multipro` / `multipro`.
- Printed/ARP MAC can be used to track the unit after mode/IP changes; in the observed case MAC was `94-28-6f-b2-6e-cf`.
- Locating device IP from MAC: If device IP is unknown, run a fast subnet ping sweep (e.g. 192.168.110.1-254) to refresh ARP cache, then filter `arp -a | grep -i <mac>`.
- Ruijie/Reyee main router was `192.168.110.1`; Aruba Instant APs were detectable on `:4343`.

## H196A menu/page IDs seen

The UI can hide pages behind JavaScript menu functions. Useful page IDs:

- Work mode: `openLink('mpworkmode')`
- LAN IPv4 / DHCP: `openLink('lanMgrIpv4')`
- WLAN basic: `openLink('wlanBasic')`
- WLAN SSID Accordion: Under WLAN Basic, the SSID configuration form is inside collapsible container `#WLANSSIDConfBar`. In automated browser sessions, click `#WLANSSIDConfBar` to expand the accordion and expose `SSID1 (2.4GHz)` and `SSID5 (5GHz)` configuration inputs in accessibility tree.

Work Mode options observed:

- `Mesh Auto(DHCP)` -> select value `auto_dhcp`
- `Mesh Auto(Bridge)` -> `auto_bridge`
- `Controller(Router)` -> `controller_router`
- `Controller(Bridge)` -> `controller_bridge`
- `Agent` -> `agent`
- `Repeater` -> `repeater`
- `Router` -> `router`

For a standalone AP behind a non-ZTE main router, prefer evaluating `Controller(Bridge)` over `Mesh Auto(Bridge)`, `Agent`, `Router`, or `Repeater`; do not assume it will persist until re-read after Apply.

## Pitfalls and verification

- **Indexed Element ID Trap on Multi-Instance Forms:** Under `WLAN SSID Configuration`, ZTE H196A templates use suffixed element IDs for each SSID slot (e.g. `ESSID:0` for SSID1, `ESSID:4` for SSID5, `Btn_apply_WLANSSIDConf:0`, `Btn_apply_WLANSSIDConf:4`). Generic selectors like `$('#ESSID')` or clicking generic button `#Btn_apply_WLANSSIDConf` target hidden prototype template elements (`#template_WLANSSIDConf`) where `_InstID` is blank, causing the router backend to either ignore the POST or return an SNTP error. Automated interaction must target the exact suffixed elements (`[id="ESSID:0"]`, `[id="KeyPassphrase:0"]`, and submit handler for slot instance).
- **Viettel EasyMesh Carrier Lock vs Brazil Mod ROM:** In Brazil Mod firmware (e.g. `V9.0.0P5_MUL`), the firmware baseline burns default Wi-Fi credentials (`VIETTEL_<hash>`), Português/English language selection, and login credentials (`multipro / multipro`) directly into the read-only flash configuration partition. Performing a physical hard reset does NOT reset to clean unconfigured stock; it resets to this Brazil mod baseline where **Work Mode defaults back to `Agent`**. In `Agent` mode, any attempt to modify SSID name/passphrase directly is silently dropped by the internal Lua handler.
- **Cross-LAN Uplink Session Guard Trap & Direct Physical Wi-Fi / Dedicated Direct-LAN Bypass:** Even when the PC and ZTE H196A share the exact same subnet (e.g., `192.168.110.x` via an upstream Ruijie router/switch), the H196A's micro-httpd server treats incoming HTTP requests on its uplink interface differently from internal wireless/LAN clients. Specifically, while reading pages (`menuView`) may work, state-changing POST requests for critical sections (`multiap_work_mode_lua.lua`, `wlan_basic_lua.lua`) fail validation (`400 Bad Request` / `SessionTimeout` / silent discard). When the user asks "why can't the PC do it if they're on the same 192.168.110 subnet?", explain clearly: the H196A firewall/daemon enforces physical interface origin checks on management write-actions.
  - **Workaround 1 (Direct Wi-Fi):** Connect a phone directly to the local Wi-Fi radio (`VIETTEL_<hash>`) or local subnet (`192.168.2.254`).
  - **Workaround 2 (Dedicated Direct-LAN Bypass via Host Multi-NIC):** If the host machine has a secondary/spare Ethernet adapter (e.g., `Ethernet 5` / `Ethernet 6`), have the user connect a physical Ethernet cable directly from the H196A **LAN port** to the PC's spare Ethernet port (leaving the primary NIC on `192.168.110.x` intact). The spare NIC will acquire DHCP from H196A (e.g., `192.168.1.2`, gateway `192.168.1.1`). Because the PC is now a genuine downstream LAN client on the physical LAN port, all `_sessionTOKEN` origin guards and POST checks pass completely. The agent can authenticate and configure Work Mode (`controller_bridge`), SSIDs, and disable DHCP directly without requiring manual phone configuration.
  - **Post-Config Re-cabling:** Once configured via Direct-LAN, unplug the cable from the PC and connect the H196A LAN port back into the main network (Ruijie/Reyee switch).
- **Mandatory Two-Step Transition Sequence:**
  1. Under `Management & Diagnosis → Work Mode`, change `Mode` from `Agent` to `Controller(Bridge)` (or `Repeater`/`Router`) and click Apply. Wait 30s for the network daemon restart.
  2. Only AFTER Work Mode is no longer `Agent`, navigate to `Local Network → WLAN → WLAN SSID Configuration` to set SSID1 and SSID5 to the target roaming SSID (`Dat`) and WPA key (`19051995`). Attempting step 2 before step 1 will ALWAYS fail silently.
- **Work Mode `Agent` Silent Discard on SSID/Password:** When H196A is in `Agent` mode, modifying SSID Name or Passphrase under `wlanBasic` may appear to succeed in the DOM, but on reload the firmware silently reverts to the old values (e.g. `Dat-T1`). This happens because `Agent` mode delegates Wi-Fi credentials exclusively to a ZTE Mesh Master. To configure standalone Wi-Fi behind a 3rd-party router (Ruijie/Aruba), H196A **must be switched to `Controller(Bridge)` first**.
- **Work Mode Switch via Web UI Silent Fail / Carrier Mesh Lock:** In carrier-customized firmware (such as Viettel ROM running Brazil GUI `V9.0.0P5_MUL`), submitting `Controller(Bridge)` via the Web GUI (`Btn_apply_WorkMode` POST) often silently fails or aborts mid-flight without persisting the mode change (even if web port 80 drops temporarily or restarts). When the unit finishes reloading, it may remain in `Agent` mode with old SSIDs (`Dat-T1`, `Dat-T1-5G`). **Recommended Fast Recovery:** Rather than fighting carrier locks in the upstream web GUI, perform a physical hard reset (hold Reset pinhole 10–15s until power LED blinks red), connect directly to default Wi-Fi/LAN (`192.168.2.254` or `192.168.1.1`), set SSID/passphrase, disable DHCP server, and plug back into the main network via LAN port.
- **Bridge Mode Web Interface Port Behavior:** Applying `Controller(Bridge)` on H196A V9 Brazil firmware triggers a network/service restart and may close or firewall HTTP port 80 to management requests incoming via the upstream LAN bridge, while ICMP ping and DNS (port 53) remain responsive. Verify actual L2 broadcast state and client Wi-Fi associations on client devices rather than assuming the device locked up when port 80 drops.
- **Button Ordering (`Cancel` before `Apply`):** On ZTE H196A forms (both `WLAN SSID Configuration` and `WLAN On/Off`), the `Cancel` button DOM element appears immediately before the `Apply` button (`Btn_cancel_WLANSSIDConf` then `Btn_apply_WLANSSIDConf`). In accessibility snapshots, verify that you click the element labeled `Apply` (typically the second button), not `Cancel`.
- **Short Web Session Idle Timeout:** The H196A V9 web interface times out rapidly (~1–2 minutes). Inactivity or multi-tab transitions cause accessibility snapshots to return `(empty page)`. When this occurs, re-navigate to `http://<ap-ip>/` and re-authenticate with credentials (`multipro` / `multipro`).
- **Sticky Client Mitigation for Multi-AP Roaming:** When configuring H196A as a satellite AP alongside Aruba Instant APs on the same L2 subnet (`192.168.110.x`):
  1. Synchronize both `SSID1 (2.4GHz)` and `SSID5 (5GHz)` with the exact same SSID Name and WPA2-PSK passphrase as the Aruba network.
  2. Under `WLAN Global Configuration`, lower `Transmitting Power` from 100% to 60%–80% (or Medium) so mobile clients moving upstairs naturally drop below roaming thresholds (-75dBm) and switch to the stronger Aruba AP.
- Do not trust typed LAN IP/DHCP values until the device is re-read and reachable. In one observed case, typing `192.168.110.240` and clicking Apply did not persist; the device remained at the old IP.
- The LAN/DHCP UI may show both DHCP radio buttons unchecked and IP fields blank in accessibility snapshots even after expanding the section. Treat this as insufficient evidence; verify via saved UI state, network behavior, or DHCP tests.
- Setting the Work Mode select with JavaScript (`#CurrentWorkMode = controller_bridge`) and clicking Apply may not persist. Always re-open Work Mode and verify it no longer shows the previous mode.
- After any Work Mode or LAN IP Apply, search for the device by MAC in ARP/router client list instead of assuming the intended IP.
- If the user's visible Chrome is already logged into Ruijie/Aruba, Hermes browser tools may still be using a separate browser session. Check for Chrome CDP/remote debugging before assuming you can reuse the user's session. If CDP is unavailable, history `stok` URLs alone may render a login shell without the session cookies.

## Aruba/Ruijie Wi-Fi matching

- Aruba Instant management commonly redirects to `https://<ap-ip>:4343/`; self-signed certificate errors are expected in browsers.
- Do not infer full Wi-Fi security mode or passphrase from only Ruijie overview text such as `SSID: Dat` and `Security: Yes`.
- If Aruba/Ruijie authenticated session or credentials are unavailable, stop before changing H196A Wi-Fi rather than guessing security mode/password.

## Verification of Roaming & AP SSSID Persistence

When both APs broadcast the exact same SSID (e.g. `Dat`), users may wonder whether the satellite AP (H196A) is actually broadcasting or if the client is only receiving signal from the master (Aruba). Client OS Wi-Fi pickers (like iOS "My Networks") retain connection history and can deceive the user into thinking default SSIDs are still active.
- **iOS "My Networks" vs "Other Networks":** SSIDs listed under iOS "My Networks" represent previously joined networks stored in iCloud/local cache, NOT real-time RF broadcast presence. The real-time RF air monitor is reflected under active connection (`✓ SSID`) and "Other Networks".
- **Isolating Satellite AP RF:**
  1. *Aruba Power-Off Gate:* Temporarily cut power/PoE to the Aruba AP. Stand near the H196A and verify if `Dat` remains connected at full signal with active Internet routing.
  2. *BSSID / Hardware MAC Audit:* Use Apple AirPort Utility ("Wi-Fi Scanner") or Android WiFi Analyzer to inspect real-time BSSIDs broadcasting the SSID. Verify that a BSSID matching the H196A's OUI prefix (`94:28:6F:...`) appears alongside the Aruba AP's BSSID.

## Cabling note

For this ROM, do not default to a LAN-LAN final instruction before confirming the actual persisted Work Mode and vendor guidance/UI state. `Controller(Bridge)` may still expect WAN uplink on some CPE firmwares; verify after mode change and management reachability before telling the user to move the cable.
