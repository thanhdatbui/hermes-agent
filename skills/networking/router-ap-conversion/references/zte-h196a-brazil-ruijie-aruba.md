# ZTE H196A V9 Brazil ROM behind Ruijie/Reyee + Aruba Instant

Session-derived notes for converting a ZTE ZXHN H196A V9 Brazil-like firmware into an AP/bridge behind a Ruijie/Reyee main router with Aruba Instant already serving the target SSID.

## Observed identifiers

- H196A web UI title: `H196A V9`, version footer observed as `H196A V9 V9.0.0P5_MUL`.
- Label/user account observed: `multipro` / `multipro`.
- Printed/ARP MAC can be used to track the unit after mode/IP changes; in the observed case MAC was `94-28-6f-b2-6e-cf`.
- Ruijie/Reyee main router was `192.168.110.1`; Aruba Instant APs were detectable on `:4343`.

## H196A menu/page IDs seen

The UI can hide pages behind JavaScript menu functions. Useful page IDs:

- Work mode: `openLink('mpworkmode')`
- LAN IPv4 / DHCP: `openLink('lanMgrIpv4')`
- WLAN basic: `openLink('wlanBasic')`

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

- Do not trust typed LAN IP/DHCP values until the device is re-read and reachable. In one observed case, typing `192.168.110.240` and clicking Apply did not persist; the device remained at the old IP.
- The LAN/DHCP UI may show both DHCP radio buttons unchecked and IP fields blank in accessibility snapshots even after expanding the section. Treat this as insufficient evidence; verify via saved UI state, network behavior, or DHCP tests.
- Setting the Work Mode select with JavaScript (`#CurrentWorkMode = controller_bridge`) and clicking Apply may not persist. Always re-open Work Mode and verify it no longer shows the previous mode.
- After any Work Mode or LAN IP Apply, search for the device by MAC in ARP/router client list instead of assuming the intended IP.
- If the user's visible Chrome is already logged into Ruijie/Aruba, Hermes browser tools may still be using a separate browser session. Check for Chrome CDP/remote debugging before assuming you can reuse the user's session. If CDP is unavailable, history `stok` URLs alone may render a login shell without the session cookies.

## Aruba/Ruijie Wi-Fi matching

- Aruba Instant management commonly redirects to `https://<ap-ip>:4343/`; self-signed certificate errors are expected in browsers.
- Do not infer full Wi-Fi security mode or passphrase from only Ruijie overview text such as `SSID: Dat` and `Security: Yes`.
- If Aruba/Ruijie authenticated session or credentials are unavailable, stop before changing H196A Wi-Fi rather than guessing security mode/password.

## Cabling note

For this ROM, do not default to a LAN-LAN final instruction before confirming the actual persisted Work Mode and vendor guidance/UI state. `Controller(Bridge)` may still expect WAN uplink on some CPE firmwares; verify after mode change and management reachability before telling the user to move the cable.
