---
name: openwrt-multiwan-node-provisioning
description: Use when deploying OpenWrt multi-WAN router with Tailscale.
version: 1.0.0
author: Hermes Agent
platforms: [linux, openwrt, windows]
tags: [openwrt, multi-wan, pppoe, tailscale, rescue-port, proxy-node]
---

# OpenWrt Multi-WAN Node Provisioning & Remote Deployment

Guidance for configuring, hardening, and deploying physical OpenWrt routers (e.g., Xiaomi R3G, x86 mini-PCs, NanoPi) to remote locations as multi-line PPPoE nodes for proxy rotation or farm connectivity, managed headlessly via Tailscale.

## 1. Physical Port Topology: 2-PPPoE + 1 Rescue Port

A standard 3-port gigabit router (e.g., Xiaomi Mi Router 3G v1) should be configured into a dedicated asymmetric topology:

| Physical Port | Role | Protocol | Metric | Purpose |
|---|---|---|---|---|
| **Port 1 (e.g., LAN 1 / middle white)** | **WAN 1** | `pppoe` | `10` | Dedicated to ISP Line 1 (primary public IP block) |
| **Port 2 (e.g., LAN 2 / outer white)** | **WAN 2** | `pppoe` | `20` | Dedicated to ISP Line 2 (secondary public IP block) |
| **Port 3 (e.g., WAN / blue)** | **Rescue** | `dhcp` (client) | `200` | Out-of-band lifeline to home router for Tailscale |

### Rules for the Rescue Port
1. **Disable Internal DHCP Server:** Set `uci set dhcp.lan.ignore='1'` so the router never broadcasts DHCP offers on the rescue port, preventing rogue DHCP conflicts on the local network.
2. **High Metric:** Set metric to `200` so default routing prefers PPPoE lines (`10`, `20`) whenever active.
3. **Zero-Touch Normal Operation:** In normal production, the rescue port remains **unplugged**. The router routes through PPPoE. The rescue port is only plugged in when PPPoE fails or during initial field triage.

---

## 2. Anti-Lockout 2-Step Handshake Protocol

When reconfiguring physical ports while connected to the router via SSH from a local host:

### The Pitfall
Directly converting the active management port (e.g., `lan1`) to a PPPoE interface instantly drops the SSH session, leaving the router unreachable and half-configured.

### The 2-Step Safe Handshake
1. **Step 1 (Expand Management Bridge):**
   - Add the target rescue port (`wan` / blue) to `br-lan`:
     ```sh
     uci add_list network.@device[0].ports='wan'
     uci commit network && /etc/init.d/network reload
     ```
   - Both ports now serve the management IP (e.g., `192.168.5.1`).
2. **Step 2 (Physical Cable Swap):**
   - Move the physical Ethernet cable to the blue port.
   - Verify connectivity to `192.168.5.1`.
3. **Step 3 (Reconfigure LAN Ports):**
   - Now that the session runs over the blue port, safely remove `lan1` and `lan2` from `br-lan`.
   - Assign `lan1` to `interface 'wan'` and `lan2` to `interface 'wan2'`.
   - Set protocol to `pppoe` with corresponding credentials.
   - Save and commit persistently (`uci commit`).

---

## 3. Tailscale Headless Deployment Discipline

For routers deployed headlessly to remote locations without technical staff on-site:

1. **Disable Key Expiry (Mandatory):**
   - Default Tailscale node keys expire after **180 days**. An expired headless node permanently disconnects and cannot be recovered remotely.
   - Immediately after node authentication, open Tailscale Admin Console (`console.tailscale.com/admin/machines`), locate the node, and click **Disable key expiry** (verify status shows `No expiry` / `Expiry disabled`).
2. **Boot Service Verification:**
   - Verify symlinks in `/etc/rc.d/`:
     - `/etc/rc.d/S19dropbear` (SSH listener)
     - `/etc/rc.d/S80tailscale` (Tailscale daemon startup)
3. **NTP Server Redundancy for TLS Clock Sync:**
   - Tailscale requires accurate system time for TLS/WireGuard handshake. Routers without battery-backed RTC boot with epoch time (1970).
   - Ensure NTP configuration in `/etc/config/system` includes global reliable NTP pools (`time.cloudflare.com`, `time.google.com`, `pool.ntp.org`), not solely domestic or ISP servers.
4. **Daemon & Routing Cleanup (Claude Audit Hardening):**
   - **mwan3 vs Kernel Metric Conflict:** If relying on kernel routing metrics (10 -> 20 -> 200), `mwan3` MUST be stopped and disabled (`/etc/init.d/mwan3 disable; /etc/init.d/mwan3 stop`). Leaving `mwan3` active conflicts with metric failover and drops connections.
   - **Prune Unused Daemons:** Disable `alist`, `openvpn`, and `watchcat` to prevent rogue WAN port exposure (5244, 1194) and uncoordinated watchcat reboot loops during internet loss.
   - **Pre-Shipout Backup:** Always run `sysupgrade -b /tmp/pre-ship-backup.tar.gz` and pull the archive back to coordinator machine before boxing hardware.
5. **Firewall Inbound Access:**
   - Ensure `/etc/firewall.user` or LuCI firewall includes an explicit rule allowing inbound traffic on `tailscale0`:
     ```sh
     iptables -I INPUT -i tailscale0 -j ACCEPT
     iptables -I FORWARD -i tailscale0 -j ACCEPT
     ```

---

## 4. Field Deployment Pitfalls & Triage

1. **ISP Circuit-ID Binding (Line Swapping):**
   - Vietnamese ISPs (VNPT, Viettel) lock PPPoE credentials to the physical fiber circuit ID / port at the OLT/BRAS.
   - If Line 1 is plugged into the Line 2 port, authentication fails (`PAP authentication failed`).
   - Instruction to on-site personnel must clearly identify Line 1 vs Line 2. If unmarked, swap the two white cables if Tailscale remains offline.
2. **ONT / Modem Bridge Mode Prerequisite:**
   - Newly installed ISP modems default to Router mode (NAT). A downstream router cannot establish PPPoE pass-through until the ISP technician or admin enables Bridge Mode on the ONT (commonly restricted to **LAN 1** port on ZTE/iGate modems).
3. **Rescue Protocol for "Tailscale Not Showing Up / 1-Minute Flap" (Field Triage Checklist):**
   - When on-site staff reports plugging in or screenshots show the node connected briefly (e.g. 1 minute) then dropped (`last seen ... ago`):
     1. **Never Dismiss Brief Online Reports:** If user or dashboard reports node was seen online (e.g., `Last seen: 2:11 PM`), do NOT argue it never connected. A brief online blip followed by disconnection is a classic signature of route flapping or cable disconnection, not a cold offline state.
     2. **Forensic Timeline Check (Avoid Cutting Working Lines):**
        - Correlate the exact time helper plugged cables with Tailscale `LastSeen`.
        - If helper plugged the 2 white cables at 14:08 and Tailscale connected at 14:10, **the PPPoE line was working!** Ordering them to unplug the white cables at 14:11 kills the working connection.
        - NEVER order an immediate unplug without verifying whether the primary or rescue interface produced the connection.
     3. **The "All-Cables-Plugged" Fallback (Anti-Cable-Juggling Heuristic):**
        - Asking non-technical helpers to constantly plug/unplug different colored cables causes confusion, loose barrel jacks, and false diagnostics.
        - Instruct helper to **plug ALL 3 CABLES** (Line 1 + Line 2 + Rescue into home modem). Since `rescue` has metric `200` while PPPoE lines have `10` and `20`, Linux will use PPPoE if up, or seamlessly fall back to Rescue if PPPoE fails, without manual intervention.
     4. **Audit Rescue Source:** Verify the cable in the BLUE port comes from a working LAN port (LAN 1/2, not IPTV/MyTV ports on LAN 3/4) of the **existing active home WiFi router**, **NOT** from the newly installed unbridged ISP lines.
     5. **Visual LED Milestone:** Front LED must boot Yellow/Orange and turn solid **BLUE** (~60–90s).
     6. **Premature Lifeline Unplug Warning:** Reiterate firmly: **DO NOT TOUCH OR SWAP CABLES WHEN THE LIGHT TURNS BLUE**. Let the coordinator verify via Tailscale first.
     7. **Post-Rescue Investigation:** Once Tailscale comes online, SSH in (`ssh root@<tailscale-ip>`) to inspect:
        ```sh
        logread | grep -E "pppd|wan"
        ip -br link
        ```
        Check whether `lan1`/`lan2` link state is `UP` (carrier detected) or `NO-CARRIER`, and whether PPPoE failed due to `Timeout waiting for PADO packets` (ONT not in bridge mode or wrong ONT LAN port) or `PAP/CHAP authentication failed` (swapped line credentials or wrong circuit ID).

4. **Non-Technical Communication Discipline for Remote On-Site Helpers:**
   - **Terminology:** Speak in plain physical terms. Say **"Đường 1" / "Đường 2"**, NEVER say "modem 1", "ONT", "BRAS", or "bridge".
   - **Port Identification:** Describe physical position and color: *"cổng trắng ở giữa (Đường 1)"*, *"cổng trắng ngoài cùng (Đường 2)"*, *"cổng xanh dương cạnh lỗ nguồn (mạng nhà cứu hộ)"*.
   - **Failsafe Reassurance:** Explicitly reassure helper: *"Nếu cắm nhầm ngược nhau thì không cháy hay mất mạng, chỉ cần đổi chéo 2 dây trắng cho nhau là xong"*.

---

## 5. Remote On-Site PC Triage via UltraViewer / AnyDesk

When headless network access fails and an on-site computer is borrowed via UltraViewer/AnyDesk:

### The "Zero-Disruption" Secondary IP Technique
- **Problem:** The remote Windows PC is on home subnet `192.168.1.x` (from ISP modem), while OpenWrt LAN is on `192.168.5.1`. Accessing `http://192.168.5.1` results in `ERR_CONNECTION_TIMED_OUT`. Changing the primary adapter IP to static `192.168.5.x` instantly kills the internet connection, dropping UltraViewer permanently!
- **Solution:** Add a secondary IP alias to the existing network adapter:
  1. Press `Win + R`, type `ncpa.cpl` -> Press Enter.
  2. Right-click active adapter (**Ethernet** or **Wi-Fi**) -> **Properties**.
  3. Double-click **Internet Protocol Version 4 (TCP/IPv4)** -> Click **Advanced...**
  4. Under **IP addresses**, click **Add...**:
     - IP address: `192.168.5.2`
     - Subnet mask: `255.255.255.0`
  5. Click **Add** -> **OK** -> **OK** -> **Close**.
- **Result:** The primary DHCP connection (`192.168.1.x`) remains active (UltraViewer stays connected), while Windows can now route traffic to `192.168.5.1` directly.

### User-Trust & Non-Invasive Discipline ("Sợ Nghĩ Mình Hack Máy")
- Borrowing a non-technical family member's PC requires strict privacy decorum:
  1. **NO Black Screens (CMD / PowerShell / Bash):** Never open command prompts or run visible CLI commands on their desktop. It triggers immediate suspicion of malware or hacking.
  2. **Browser-Only Interaction:** Open Chrome or Edge directly to `http://192.168.5.1` (LuCI GUI). It looks identical to normal household Wi-Fi router management.
  3. **No File Downloads or Script Drops:** Perform all configuration purely inside LuCI web forms. Close browser and disconnect remote session immediately once Tailscale is online.

### LuCI Real-World Field Diagnostics
1. **PPPoE Status & CGNAT Realities:**
   - If an interface displays an IP in `172.16.0.0/12` (e.g. `172.17.49.92`) or `100.64.0.0/10`, **PPPoE is UP and functional**. This is ISP CGNAT, not an error.
   - **Debunking "Chưa Mở NAT":** Tailscale operates seamlessly over CGNAT/double-NAT via DERP relays. A public IP / open NAT is NEVER required for Tailscale to establish connectivity.
2. **`Error: Unknown error (USER_REQUEST)` in LuCI:**
   - Means the interface was explicitly brought down or is pending restart via netifd. Clicking **Restart** triggers a fresh PPPoE discovery (`PADI -> PADO -> PADR -> PADS`) taking ~15–30 seconds.
3. **Tailscale Kickstart via LuCI:**
   - If Tailscale daemon booted before WAN was established, it may stay idle in backoff.
   - Go to **System -> Startup**, locate `tailscale`, and click **Restart**.
   - If node still fails to handshake, check **Status -> System Log** for clock desync (NTP failing to sync TLS time) or DNS failure resolving `controlplane.tailscale.com`.
4. **Clock Desync TLS Trap (`x509: certificate is not valid`):**
   - No-RTC routers boot with stale clock time. TLS handshakes to Tailscale DERP relays fail with `x509: certificate is not valid for any names`.
   - **Fix:** In LuCI go to **System -> System -> General Settings**, click **`SYNC WITH BROWSER`**, click **Save & Apply**, then restart `tailscale` in **System -> Startup**.
5. **DNS Forwarding Trap:**
   - If log shows `no such host` resolving Tailscale domains on `127.0.0.1:53`, add public resolvers (`8.8.8.8`, `1.1.1.1`) under **Network -> DHCP and DNS -> DNS forwardings** and save.
6. **ISP Walled Garden & Traceroute ICMP Code `!C` (`Administratively Prohibited`):**
   - If PPPoE obtains an IP (e.g., `172.17.x.x` on Viettel) but `Network -> Diagnostics -> Ping 8.8.8.8` has 100% loss, run `IPv4 Traceroute` to `8.8.8.8`.
   - **The `!C` Signature:** If traceroute hops enter ISP internal routers (e.g. `27.68.x.x -> 172.28.x.x -> 10.29.x.x`) and end with `!C` (e.g. `8 10.29.74.202 !C`):
     - `!C` is ICMP Type 3 **"Communication Administratively Prohibited"**.
     - **Definitive Proof:** The packet has successfully exited the router and reached deep inside the ISP network (often 2ms away), where the ISP policy/firewall deliberately rejects it because the newly pulled fiber line has **not been provisioned / activated / completed (chưa hoàn công / active luồng)** by the technician on the ISP billing/service platform.
     - This proves **100% ISP-side configuration hold**, NOT router misconfiguration.
   - **Actionable Escalation:** Take a screenshot of the `!C` traceroute and instruct the user to report directly to the ISP tech or hotline (e.g., Viettel 1800 8119): cite the contract accounts, the gateway IP, and the exact hop rejecting traffic with `!C`.

7. **Direct PPPoE Dial-Up Testing on Windows via UltraViewer (Zero-Disconnect Safeguard):**
   - To eliminate all doubt and prove an ISP line fault directly from a Windows PC connected to the ONT:
   - **Critical UltraViewer Trap:** When Windows connects a PPPoE dial-up interface, it defaults to setting that connection as the system's Default Gateway. If that PPPoE line is in a walled garden / has no internet, all PC traffic immediately diverts to the dead line, **killing internet and dropping the UltraViewer session permanently**!
   - **The Unchecked Gateway Protocol:**
     1. In Windows Settings -> **Dial-up** -> **Set up a new connection** -> **Connect to the Internet** -> **Broadband (PPPoE)**.
     2. Enter PPPoE Username and Password. Click **Connect**, then **IMMEDIATELY click Cancel/Skip** on the connecting dialog so the profile is saved without engaging traffic.
     3. Press `Win + R` -> `ncpa.cpl`.
     4. Right-click the newly created PPPoE connection -> **Properties** -> **Networking** tab.
     5. Select **Internet Protocol Version 4 (TCP/IPv4)** -> **Properties** -> **Advanced...**.
     6. **UNCHECK: `Use default gateway on remote network`**. Click OK -> OK -> OK.
     7. Now safely connect the PPPoE profile: Windows dials and obtains the IP on the PPP adapter, while all existing PC internet and UltraViewer traffic remains 100% on the primary physical adapter.

8. **PPPoE `Timeout waiting for PADO packets`:**
   - Indicates no discovery offer from BRAS. Verify: cable is in **LAN 1** of ONT (many ONTs only bridge LAN 1), ONT is set to Bridge Mode, and VLAN ID (e.g. 35) is configured if required by provincial ISP.

9. **The Bridge Dual-Zone & DHCP Collapsing Trap (Why Rescue Port Flaps After 1 Minute):**
   - **The Architectural Bug:** If both the static management interface (`lan` on `192.168.5.1`) and the rescue interface (`rescue` on DHCP client) are bound to the same bridge device (`br-lan`), but assigned to different firewall zones (`lan` in zone `lan` with `ACCEPT`, and `rescue` in zone `wan` with `REJECT/masq`):
     - Netifd attempts to manage two conflicting subnet scopes on one L2 bridge.
     - When connected to a home router, `rescue` obtains an upstream DHCP lease and brings Tailscale up (~30s). Shortly after (~60–90s), OpenWrt initializes the static IP and firewall zone conflict, while router-side dnsmasq rogue DHCP leases clash with home network $\rightarrow$ default gateway flaps and Tailscale drops out permanently!
   - **The Permanent Fix in LuCI / UCI:**
     1. **Move RESCUE Zone to `lan`:** Under **Network -> Interfaces -> RESCUE -> Firewall Settings**, assign it to zone **`lan`** (green), NOT `wan`. Both interfaces on `br-lan` must share the same security domain.
     2. **Disable Rogue DHCP on LAN:** Under **Network -> Interfaces -> LAN -> DHCP Server -> General Setup**, check **`Ignore interface`**. This completely silences OpenWrt DHCP broadcasts, ensuring peaceful coexistence when plugged into any home router.
     3. **Preserve Metric Priority:** Keep `rescue` metric at `200` while PPPoE lines remain at `10` and `20`.

10. **Tone & Decorum When Composing ISP Escalation Messages:**
    - When user requests a message to send to ISP technicians:
    - **Never make it overly aggressive or hostile.** Avoid threats, insults, or demanding compensation.
    - Keep tone polite, professional, and technical: cite exact accounts (`hyn_gftth_...`), gateway IPs (`27.68.227.150`), and ICMP diagnostic codes (`10.29.74.202 !C`). Technical precision commands immediate respect from field engineers without escalating interpersonal friction.

11. **LuCI Web Terminal Hangs & Go/Tailscale Stalled Handshake:**
    - **Symptom:** Running commands like `tailscale up` in LuCI web terminal (`/cgi-bin/luci/admin/system/ttyd`) appears to hang, prints nothing, and cursor drops to a blank newline upon Enter.
    - **Mechanism:** `tailscale up` performs a blocking synchronous HTTP/TLS request to `controlplane.tailscale.com`. When the WAN interface is captive / walled-garden (traffic dropped or blackholed after BRAS), the Go TLS dialer blocks indefinitely waiting for TCP handshake / TLS deadline. The web terminal does not render incremental output until process returns or flushes stdout.
    - **Triage:** Do NOT force the user to repeatedly retype commands or hit Enter in LuCI terminal when WAN has 100% packet loss. As long as WAN cannot reach external IPs (ping 8.8.8.8 loss 100%), any CLI command attempting internet connection will hang. Triage ISP connectivity first before invoking network daemons.

12. **ISP Modem / Mesh Router Dialing Conflict & MAC Binding (The H196A / "20 Lines" Trap):**
    - **Symptom:** ISP technician tests their own router/mesh device (e.g. ZTE H196A) on the newly pulled line and claims *"PPPoE connects fine and lướt web bình thường"*, but the customer router (R3G OpenWrt) gets `PADO timeout` or `!C` walled-garden errors.
    - **Triage & Common Root Causes:**
      1. **Device Account Hijacking (`Type: Routing` vs `Bridge`):** Check the ISP device configuration page. If the ISP router profile shows `Type: Routing` (with PPPoE username/password embedded in it), **the ISP device itself is dialing PPPoE and occupying the subscriber session!** A downstream router plugged into its LAN port cannot dial PPPoE again (results in PADO timeout or Session Limit Exceeded). The ISP device MUST have PPPoE deleted or switched to pure `Bridge Mode`.
      2. **The "IPTV Bundling / Dual-Service" Trap on ISP Profile (Crucial):**
         - On ISP routers/mesh (ZTE H196A), the WAN connection profile has a **Service List** with checkboxes for `INTERNET` and `IPTV`.
         - If `IPTV` is checked alongside `INTERNET` (`☑ INTERNET`, `☑ IPTV`), the ISP device or ONT bridges multicast/VoD traffic into the session or tags packets for the telco's internal TV network. The router receives a carrier-internal IP (`172.17.x.x`), but external internet traffic is blocked with ICMP code `!C` (`Administratively Prohibited`).
         - **Fix:** On the ISP device (or when instructing the technician), explicitly **UNCHECK `IPTV`** so the profile serves **`INTERNET` ONLY** (`☑ INTERNET`, `☐ IPTV`). Once IPTV is unbundled, the PPPoE session routes directly to the public internet.
      3. **Distinguish Dedicated ONT vs Handheld Test Router:**
         - Do not confuse the customer's permanent optical modem (ONT at `192.168.1.1` or under the desk) with the technician's portable testing AP (e.g. H196A at `192.168.2.253`). Technicians frequently carry a spare mesh router into the field purely to prove line sync. If the technician's test device successfully dials PPPoE upon unchecking IPTV, it conclusively proves the underlying fiber and ONT bridge are functioning—the customer router simply needs to establish its PPPoE session cleanly without IPTV service tags.
      4. **OLT/BRAS MAC Address Binding (Caveat):**
         - While some BRAS implementations bind to specific vendor MACs, avoid jumping to MAC cloning as a first assumption when a technician is merely using a test router. Check line activation status and service bundling (IPTV) first. If cloning is genuinely required, set **Network -> Interfaces -> Edit WAN -> Advanced Settings -> Override MAC address** to the ISP test device's WAN MAC.
      5. **Account vs Line Disconnect (The "20 Lines" Benchmark):** If other lines at the same site work on different routers, never assume the new line has the same active profile. Perform an A/B test: temporarily enter a verified active username from one of the working lines into the router to immediately distinguish between a local hardware/config issue and an ISP subscriber provisioning freeze.

13. **OpenWrt Multi-WAN Switch/DSA Port-Binding Pitfall & The "auto" String Trap:**
    - **The DSA Bridge Slave Trap (`master br-lan` swallows PADO):**
      - **Root Cause:** In OpenWrt DSA architecture (kernel 5.4+ / MT7621), if `lan1` or `lan2` is still listed in `network.@device[0].ports` (belonging to `br-lan`), the Linux kernel bridge `rx_handler` intercepts incoming Ethernet frames with ethertype `0x8863` (PPPoE Discovery) and forwards them up the bridge instead of delivering them to the raw socket opened by `pppd` on `lan1`/`lan2`.
      - **Consequence:** `pppd` sends `PADI` packets out successfully (upstream ISP receives and responds with `PADO`), but `pppd` never sees the returning `PADO` frame because the bridge swallowed it. The log shows repeated `Timeout waiting for PADO packets` even on a 100% healthy line that works on other routers!
      - **Verification:** Run `bridge link` in terminal. If `lan1` or `lan2` has `master br-lan`, this bug is active.
      - **The Fix:** Remove slave ports from `br-lan` explicitly via UCI:
        ```sh
        uci -q del_list network.@device[0].ports='lan1'
        uci -q del_list network.@device[0].ports='lan2'
        uci commit network && /etc/init.d/network restart
        ```
        Keep only the management port (e.g. `wan` / blue port) in `br-lan` so remote UltraViewer/PC access is not severed.
    - **The Switch / DSA VLAN Misconfiguration Trap:**
      - On SoC routers like Xiaomi R3G (MediaTek MT7621 with DSA / switch architecture), `lan1` and `lan2` are physical switch ports designed for bridging into `br-lan`.
      - If an agent reassigns `lan1` or `lan2` to PPPoE WAN interfaces without cleanly isolating them from internal switch/VLAN bridge logic, outgoing PPPoE discovery frames (`PADI`) can be misrouted or tagged internally, causing perpetual `Timeout waiting for PADO packets` even when the ISP line and ONT are 100% healthy.
      - **Diagnostic Evidence:** If a known-working line dials fine on other hardware but gets `PADO timeout` on `lan1`/`lan2` of the OpenWrt router, do NOT blame the ISP cable or MAC binding. Verify link carrier (`ip link show lan1`) and inspect frame egress via `tcpdump -i any -n -e 'ether proto 0x8863'`.
    - **The "auto" String in LuCI PPPoE Fields:**
      - In LuCI -> **Network -> Interfaces -> Edit WAN -> Advanced Settings**, the fields **Access Concentrator** and **Service Name** show grey helper text: *"Leave empty to autodetect"*.
      - **The Bug:** Users or agents often mistakenly type the literal string `"auto"` into these fields.
      - In OpenWrt `pppd`, entering `"auto"` forces pppd to demand an Access Concentrator / Service Name literally named `"auto"`. The ISP BRAS (e.g. Viettel) rejects or ignores the request, causing immediate PPPoE discovery timeout (`PADO timeout`)!
      - **Fix:** Both fields **MUST BE LEFT COMPLETELY BLANK/EMPTY**.
    - **The Case-Sensitivity Interface Trap (`wan2` vs `WAN2`):**
      - OpenWrt UCI interface names are case-sensitive. If an interface was created in LuCI as `WAN2` (uppercase), running `ifup wan2` returns `Interface wan2 not found`. Always check exact case via `uci show network | grep proto=\'pppoe\'` or `ip -br addr` (which creates `pppoe-WAN2`).
    - **Missing Default Gateway Routing After PPPoE Connects:**
      - Even after obtaining an IP on `pppoe-WAN2` (e.g. `172.17.49.234`), `ping 8.8.8.8` may fail with 100% packet loss if `defaultroute` is disabled or overruled by lingering `mwan3` rules. Check `ip route` for a `default via <peer_ip> dev pppoe-WAN2` entry.
    - **Physical Port Safety & Zero-Disruption Management (Never Reset Factory Remotely):**
      - When managing the router via UltraViewer on an on-site PC plugged into the router:
      - **NEVER alter or reassign the physical port currently serving the PC (e.g. blue port / `br-lan`).** Doing so drops the management connection instantly, terminating the remote support session.
      - **NEVER perform a Factory Reset remotely:** Factory reset sets IP back to `192.168.1.1`, colliding with the ISP modem (`192.168.1.1`) and disabling management on the blue port, causing an instant, irrecoverable remote lockout.
      - Always confine interface debugging and testing strictly to the remaining ports (`lan1`, `lan2`) while keeping the management port untouched.
    - **LuCI Web Terminal (ttyd) Paste Corruption via Remote Desktop:**
      - **The Bug:** When pasting multi-line or compound shell commands via UltraViewer/AnyDesk into LuCI Web Terminal (`ttyd`), browser clipboard drivers frequently drop ampersand (`&`) characters or eat newlines.
      - **Consequences:**
        - `cmd1 && cmd2` becomes `cmd1 cmd2` (arguments mashed together, executing invalid commands).
        - Background syntax `cmd >/dev/null 2>&1 &` becomes `cmd >/dev/null 2> 1` (creating a file named `1` and blocking foreground execution instead of backgrounding).
        - Pressing `Ctrl + C` to abort a blocked foreground daemon kills the daemon socket instantly (`read unix @->/var/run/tailscale/tailscaled.sock: use of closed network connection`).
      - **Fixes:**
        1. Always send commands as single, independent lines one by one. Never paste compound `&&` chains through web terminals.
        2. To safely daemonize processes without relying on the `&` character, use OpenWrt's native daemon launcher:
           ```sh
           start-stop-daemon -S -b -x /usr/sbin/tailscaled -- --state=/tmp/tailscaled.state
           ```
    - **Port-Swapping & Circuit-ID / Credential Realignment Heuristic:**
      - When physical cables are swapped between ports (e.g. cable from Line 0 moved to `lan2`, and cable from Line 1 moved to `lan1`):
      - ISPs enforce strict Circuit-ID / OLT port binding. If physical cables are swapped, the PPPoE accounts MUST be swapped accordingly in UCI configuration:
        - `uci set network.wan.username='<account_of_cable_now_in_lan1>'`
        - `uci set network.WAN2.username='<account_of_cable_now_in_lan2>'`
      - Otherwise, cross-dialing occurs (sending Line 1 credentials down Line 0 fiber), triggering immediate authentication rejection from the BRAS.

    - **ISP 802.1Q VLAN Tagging vs Management Pool Trap (The "172.x.x.x" & VLAN 35 Solution):**
      - **Symptom:** PPPoE connects successfully and receives an IP in the private carrier range (e.g. `172.17.x.x` on Viettel) and an IPv6 GUA (`2402:800:...`), ping to BRAS peer (`27.68.227.150`) succeeds with 0% loss (2ms), but `ping 8.8.8.8` drops 100% and HTTP traffic hangs. ISP technician explicitly states: *"172 là cấu hình sai rồi, phải chạy VLAN 35"*.
      - **Root Cause:** When dialing PPPoE untagged directly on a physical interface (`lan1`), the ISP BRAS/OLT classifies the session as untagged management traffic and routes it to an isolated internal management pool (`172.17.x.x`), dropping all outbound internet traffic. To reach the actual Internet subscriber pool and obtain a routable Public IP / working CGNAT, the PPPoE session MUST be encapsulated in an 802.1Q VLAN tag (e.g. VLAN ID `35` for Viettel).
      - **How to Configure 802.1Q VLAN on OpenWrt (LuCI / UCI):**
        1. **Create the 802.1Q Device in LuCI:**
           - Go to **Network -> Interfaces -> Devices** tab.
           - Click **Add device configuration...**.
           - **Device type:** Select **`VLAN (802.1q)`**.
           - **Base device:** Select the physical port (e.g. `lan1` or `lan2`).
           - **VLAN ID:** Enter the ISP VLAN ID (e.g. `35`).
           - **Device name:** Enter `lan1.35` (or `lan2.35`). Click **Save** and **Save & Apply**.
        2. **Bind Interface to the VLAN Sub-Device:**
           - Go to **Network -> Interfaces -> Edit WAN** (or `WAN2`).
           - In **General Settings -> Device**, change selection from physical `lan1`/`lan2` to the new VLAN sub-device: **`lan1.35`** or **`lan2.35`**.
           - Ensure protocol is `PPPoE`, enter credentials, and save.
        3. **Clear "USER_REQUEST" Status:**
           - If interface shows `Error: Unknown error (USER_REQUEST)`, click **RESTART** on the interface row, followed by **Save & Apply**.
        4. **Verification:**
           - Once netifd brings up `pppoe-wan` over `lan1.35`, the router receives a genuine Public/Internet IP (e.g. `27.x`, `116.x`, `171.x` or routable CGNAT `100.64.x`), eliminating the `172.17.x.x` trap, and `ping 8.8.8.8` immediately succeeds.

    - **Untagged vs Tagged Reality & LuCI Modal Dropdown Selection Trap:**
      - **Untagged ONT Bridge Reality:** If tagging VLAN 35 on OpenWrt results in immediate `PADO timeout` while dialing untagged on raw `lan1`/`lan2` connects and negotiates LCP/IPCP (even if receiving carrier-internal IP `172.17.x.x`), the ONT bridge itself is **ALREADY stripping/handling VLAN 35 upstream** and presenting untagged frames to the router's LAN ports. In this topology, OpenWrt MUST dial directly on raw physical interfaces (`Switch port: "lan1"`, `Switch port: "lan2"`), NOT on VLAN sub-devices (`lan1.35`).
      - **The LuCI Device Dropdown Alias Trap:**
        - When configuring an interface in LuCI -> **Interfaces -> Edit WAN2 -> General Settings -> Device**, the expanded dropdown list contains confusing virtual items at the bottom:
          - `Alias Interface: "@WAN2"`
          - `Alias Interface: "@WAN2_6"`
          - `Alias Interface: "@lan"`
          - `Alias Interface: "@rescue"`
        - **The Pitfall:** Agents or users often mistakenly select alias entries (like `@WAN2` or `@WAN2_6`). This breaks L2 binding.
        - **Correct Selection:** ALWAYS scroll up and select the concrete physical Ethernet port: **`Switch port: "lan2"`** (or `Switch port: "lan1"`).
      - **The Misleading "USER_REQUEST" Status in Edit Modals:**
        - While an Edit modal dialog (`Interfaces » WAN2`) is actively open, LuCI frequently displays `Error: Unknown error (USER_REQUEST)` in the modal status header box.
        - This does NOT mean the interface is broken. It simply indicates uncommitted in-memory state or pending netifd reload. Check the RX/TX packet counters inside the status box: if packets and uptime are incrementing and an IPv4 address is present, the PPPoE session is already alive and running. Complete changes by clicking **Save**, then clicking **Save & Apply** at the bottom-right of the main Interfaces page.

## References

- `references/claude-audit-and-field-triage-r3g.md` — Detailed case study of Xiaomi R3G deploy, Claude CLI production audit remediation, and the premature lifeline unplug incident.
