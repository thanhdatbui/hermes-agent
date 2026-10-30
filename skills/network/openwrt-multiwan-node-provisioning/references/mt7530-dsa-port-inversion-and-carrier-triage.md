# MT7530 DSA Physical Port Inversion & Carrier Triage Field Notes (Xiaomi R3G v1)

## 1. Physical vs Kernel DSA Device Mapping
On Xiaomi Mi Router 3G v1 running ImmortalWrt / OpenWrt 21.02 DSA:
- **Blue Port (labeled Internet/WAN):** Internal device `wan` (`master br-lan` in rescue mode).
- **Middle White Port (labeled LAN 1 physically):** Kernel switch device **`lan2`** (`switch port 2`).
- **Outer White Port (labeled LAN 2 physically):** Kernel switch device **`lan1`** (`switch port 3`).

### Diagnostic Trap & Anti-Hallucination
When the user states: "I just unplugged the middle port" or "I just unplugged the outer port":
- If the agent naively assumes `middle port == lan1`, it will misdiagnose carrier states and argue falsely with the user.
- **Verification Rule:** Always run:
  ```sh
  dmesg | grep -iE "mt7530.*Link is" | tail -n 10
  ```
  Look at the exact timestamp of `Link is Down` vs `Link is Up` across `lan1` and `lan2` to correlate the human physical plug/unplug event with the kernel interface name.
- **Communication Invariant:** NEVER argue with the user when they report physical port unplug events. If the user says "cắm lỗ giữa mới đúng" / "rút cổng ngoài", correlate against kernel `dmesg` link down/up timestamps immediately before declaring which port is active.

## 2. MobiProxy Box REST API & PPPoE Provisioning Protocol
When interfacing with or configuring an external hardware MobiProxy box (`test.taadaa.click`):
- **Web UI & REST API Architecture:**
  - Login session via `POST /login.php` with `_csrf` and password (`N0spam@23102025`).
  - API endpoint: `http://<host>/api.php?action=<action>`.
  - Required headers for all API requests:
    - `Accept: application/json`
    - `X-CSRF-Token: <csrf-token-from-meta-or-html>`
    - `X-Requested-With: XMLHttpRequest`
- **Inspect WAN / PPPoE Credentials by Port:**
  - `GET /api.php?action=network.credentials&lan=<1|2|3|4>`
  - Returns current configured PPPoE username and password per physical port. Note: `lan` parameter is numeric (`1..4`), NOT string (`Lan1` will return HTTP 422).
- **Dashboard Inspection:**
  - `GET /api.php?action=dashboard` returns full list of proxies, egress interfaces (`pppoe-proxyXX`), and public IPv4/IPv6.
- **Rotation API:**
  - `GET /proxy_recreat?token=<token>&proxy=<host>:<port>` triggers immediate PPPoE redial and IP rotation.

## 2. Multi-MACVLAN Zero-Collision Invariant
- Never bind virtual sub-interfaces to the default routing table `main`.
- When binding proxy daemons (e.g. Tinyproxy), use `Bind <local_sub_ip>` and route tables `table 101..108` with `ip rule add from <local_sub_ip> table <table_id>` and `ip route replace default dev pppoe-wan_subX table <table_id>`.
- This ensures that if one line is physically unplugged or rotated, the primary WAN maintaining Tailscale never loses connectivity.
