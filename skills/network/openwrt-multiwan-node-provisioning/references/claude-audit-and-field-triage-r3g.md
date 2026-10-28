# Claude Audit & Field Triage Case Study: Xiaomi R3G Multi-WAN Deploy

Case study and operational notes from deploying the Xiaomi Mi Router 3G v1 (`r3g-thaibinh`) with 2 PPPoE lines + 1 rescue port over Tailscale.

## 1. Claude CLI Independent Audit Findings

During pre-shipout review, Claude CLI identified critical production hazards on headless OpenWrt nodes:

1. **mwan3 vs Kernel Metric Route Conflict:**
   - *Finding:* When interfaces have distinct metrics (Line 1 = 10, Line 2 = 20, Rescue = 200), `mwan3` rules still intercept routing unless explicitly configured for failover policies.
   - *Remediation:* If relying purely on Linux kernel metric-based default routing, disable `mwan3` completely:
     ```sh
     /etc/init.d/mwan3 disable
     /etc/init.d/mwan3 stop
     rm -f /etc/rc.d/*mwan3*
     ```

2. **Dormant Daemon Port Exposure & Resource Leaks:**
   - *Finding:* Default ROM images often package `alist` (listening on TCP 5244) and `openvpn` (UDP 1194) with inbound firewall accept rules. On public IP lines, these expose files and services to the public internet.
   - *Finding:* `watchcat` configured to reboot on ping failure will cause infinite reboot loops when upstream ISP fiber is disconnected during transit or installation.
   - *Remediation:*
     ```sh
     /etc/init.d/alist disable && /etc/init.d/alist stop
     /etc/init.d/watchcat disable && /etc/init.d/watchcat stop
     uci -q delete firewall.alist
     uci -q delete firewall.openvpn
     uci commit firewall
     ```

3. **NTP Server Redundancy (No-RTC Clock Desync):**
   - *Finding:* MT7621 routers have no battery-backed RTC. Default NTP lists often contain regional Chinese servers (Aliyun, Tencent) that may fail or time out, leaving system time at 1970. Tailscale cannot validate TLS certificates with desynchronized clocks.
   - *Remediation:*
     ```sh
     uci add_list system.ntp.server='time.cloudflare.com'
     uci add_list system.ntp.server='time.google.com'
     uci add_list system.ntp.server='pool.ntp.org'
     uci add_list system.ntp.server='vn.pool.ntp.org'
     uci commit system
     /etc/init.d/sysntpd restart
     ```

4. **Pre-Shipout Sysupgrade Archive:**
   - *Command:* `sysupgrade -b /tmp/pre-ship-backup.tar.gz`
   - *Verification:* Pull archive back to coordinator PC (`C:/Users/Kibe/pre-ship-backup.tar.gz`) and verify `etc/config/network`, `etc/config/firewall`, `etc/firewall.user` inside before packing hardware.

---

## 2. Field Triage & Flapping Lifeline (Real-World Incident)

### Incident Symptom
- Node appears `Connected` (green dot) in Tailscale Admin Console at `14:10:00`.
- At `14:11:00` (after ~1 minute), node state drops to `Offline (last seen 2:11 PM GMT+7)` with `RxBytes: 0`.

### Root Cause Analysis & Forensic Breakdown
1. **The Bridge Dual-Zone & Rogue DHCP Conflict (The Architectural Bug):**
   - *Discovery:* Both the static management interface (`lan` on `192.168.5.1`) and the rescue interface (`rescue` on DHCP client) were bound to the same bridge device (`br-lan`).
   - *Firewall Zone Clash:* `lan` was assigned to zone `lan` (ACCEPT), while `rescue` was assigned to zone `wan` (REJECT/masq).
   - *Sequence of Failure:*
     1. On boot, `udhcpc` on `rescue` successfully pulled an IP lease (`192.168.1.x`) from the home router and brought Tailscale online (`Connected` at 14:10).
     2. Within 60 seconds, netifd committed the static IP `192.168.5.1` on `br-lan`, while firewall zone matching rules clashed on the same L2 bridge.
     3. Rogue dnsmasq on `lan` began broadcasting DHCP offers to the home network, destabilizing local routing and dropping the default gateway.
   - *Remediation:*
     1. Move `rescue` to firewall zone `lan` (under **Network -> Interfaces -> RESCUE -> Firewall Settings**).
     2. Enable `Ignore interface` on `lan` DHCP server (under **Network -> Interfaces -> LAN -> DHCP Server -> General Setup**).

2. **Premature Line Severing & Denial Bias:**
   - Because of impatience, coordinator assumed the primary lines failed and prematurely ordered helpers to unplug cables.
   - When user presented screenshots showing the node was connected at 2:10 and disconnected at 2:11, coordinator initially dismissed the evidence, assuming the node had never connected.
   - *Discipline:* Never argue against timestamp evidence. Always cross-check intervention timeline before ordering unplugs. Default to leaving all 3 lines connected.

---

## 3. Remote PC On-Site Triage & LuCI Diagnosis (UltraViewer Case Study)

When headless remote access fails and an on-site Windows machine is borrowed via UltraViewer:

### 1. Subnet Traversal without Disconnecting Remote Desktop
- Host PC was connected to home ONT (`192.168.1.x`), while OpenWrt LAN was `192.168.5.1`. Direct browser requests to `192.168.5.1` timed out (`ERR_CONNECTION_TIMED_OUT`).
- **Remedy:** Added secondary IP alias `192.168.5.2 / 255.255.255.0` via `ncpa.cpl -> IPv4 -> Advanced -> Add IP`.
- Maintained active internet connection for UltraViewer while establishing instant L2 access to LuCI at `http://192.168.5.1`.

### 2. LuCI Real-World Telemetry Interpretation
- **WAN2 (Line 2):** Discovered actively connected via PPPoE with IP `172.17.49.92/32` (VNPT CGNAT) and IPv6 `2402:800:.../64`. This proved the physical line, fiber circuit ID, and ONT bridge were 100% operational.
- **WAN (Line 1):** Displayed `Error: Unknown error (USER_REQUEST)` due to an uninitiated daemon state; resolved by clicking `Restart`.
- **Tailscale Daemon Kickstart:** Because Tailscale initially booted prior to PPPoE establishment, the daemon paused in retry backoff. Triggering `Restart` under `System -> Startup -> tailscale` forced an immediate re-handshake over the active PPPoE interface.

---

## 4. Clock Desynchronization, DNS Bootstrap, and Captive Portal (x509 Certificate Block)

### 1. Clock Desync & TLS Failure (`x509: certificate is not valid for any names`)
- **Symptom in System Log (`Status -> System Log`):**
  ```text
  tailscaled: trying bootstrapDNS("derp9.tailscale.com", "...") for "controlplane.tailscale.com": x509: certificate is not valid for any names
  ```
- **Root Cause:** Routers without battery-backed RTC (like MT7621 Xiaomi R3G) retain the shutdown timestamp across reboots until NTP syncs. If deployed 15 days later without working NTP, system time is stuck in the past, causing Go `crypto/x509` certificate validation to fail on DERP relay connections.
- **Remedy via LuCI GUI:**
  1. Navigate to **System -> System -> General Settings**.
  2. Under **Local Time**, click **SYNC WITH BROWSER** to instantly set the router clock to the technician's browser time.
  3. Click **Save & Apply**.
  4. Go to **System -> Startup**, find `tailscale`, and click **Restart**.

### 2. DNS Forwarding Trap for Tailscale Bootstrap
- **Symptom in System Log:**
  ```text
  logtail: dial "log.tailscale.io:443" failed: dial tcp: lookup log.tailscale.io on 127.0.0.1:53: no such host
  ```
- **Root Cause:** Upstream ISP DNS servers either fail to resolve Tailscale domains or drop port 53 UDP queries during initial line provisioning.
- **Remedy via LuCI GUI:**
  1. Navigate to **Network -> DHCP and DNS -> General Settings**.
  2. Locate **DNS forwardings**, enter `8.8.8.8` and `1.1.1.1`.
  3. Click **Save & Apply**.
  4. Restart `tailscale` under **System -> Startup**.

### 3. ISP Traceroute Hop 8 `!C` (`Administratively Prohibited`) vs Walled Garden
- **Symptom:** PPPoE establishes successfully and receives an IP in `172.17.x.x`, but ping `8.8.8.8` returns `100% packet loss`. Traceroute to `8.8.8.8` returns:
  ```text
  1  27.68.227.150 (1.7 ms)
  2  172.28.144.150 (2.6 ms)
  3-7 10.29.74.201 (~2.2 ms)
  8  10.29.74.202 !C (2.1 ms)
  ```
- **Technical Breakdown:**
  - `!C` is ICMP Type 3 Code 13 (`Communication Administratively Prohibited`).
  - **Definitive Evidence:** The packet has successfully exited the router, traversed the BRAS gateway, and penetrated 7 hops into the ISP network before an internal aggregation/core firewall rejected the traffic.
  - This proves 100% that the router configuration and PPPoE authentication are correct, and the block is caused by an unprovisioned / un-activated account held in an ISP Walled Garden pool.
- **Communication Protocol:** Compose a polite, technically precise escalation message to the ISP technician citing the accounts, gateway IP, and the exact hop rejecting traffic with `!C`.

### 4. PPPoE `Timeout waiting for PADO packets` (Discovery Failure)
- **Symptom in System Log:**
  ```text
  pppd: Timeout waiting for PADO packets
  pppd: Unable to complete PPPoE Discovery
  ```
- **Diagnostics & Root Causes:**
  - Carrier is detected (`Link is Up - 1Gbps`), but no PPPoE Active Discovery Offer (PADO) is received from the BRAS.
  - **Check 1 (Wrong Port on ONT):** Many ISP ONTs (ZTE, Huawei, iGate) only bridge on **LAN 1**. Plugs in LAN 2–4 receive no PADO responses.
  - **Check 2 (Unbridged ONT):** ONT is still operating in Router mode (NAT) and rejecting PPPoE pass-through.
  - **Check 3 (VLAN Tagging Requirement):** ISP requires 802.1Q VLAN tagging on the WAN interface (e.g., VLAN 35 for VNPT in specific provinces). Untagged PADI packets are silently dropped by the OLT.

### 5. ISP Device Account Hijacking & MAC Clone Verification (The ZTE H196A Incident)
- **Symptom:** ISP technician connects an ISP router/mesh (ZTE H196A) directly to the fiber line and claims it connects fine, but customer router (R3G OpenWrt) fails with `PADO timeout` or `!C`.
- **Root Cause 1 (`Type: Routing` vs `Bridge`):** Inspecting the screenshot of the H196A interface revealed the profile was configured with `Type: Routing` (PPPoE connection handled by H196A itself with embedded credentials). By dialing PPPoE directly on H196A, the session was occupied, locking out any secondary router downstream.
- **Root Cause 2 (OLT MAC Binding):** If OLT binds authentication to the MAC address of the supplied ZTE router:
  - Extract the WAN MAC address from the H196A bottom label or status page.
  - Apply MAC clone in LuCI: **Network -> Interfaces -> Edit WAN -> Advanced Settings -> Override MAC address** -> Enter H196A MAC.
