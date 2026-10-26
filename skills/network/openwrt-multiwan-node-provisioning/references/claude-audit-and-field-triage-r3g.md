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
1. **Initial Boot & Primary Line Success:** 
   - At 14:04, instructions were given to plug the 2 white cables (Line 1 and Line 2) and leave the blue port empty.
   - At 14:08, helper plugged the 2 white cables.
   - At 14:10, PPPoE dialed successfully on the primary line, and Tailscale came online (`Connected` at 14:10).
2. **False Diagnostic & Premature Line Severing:**
   - Because of polling lag and impatience, coordinator assumed the primary lines failed and prematurely instructed the helper: *"Unplug the 2 white cables immediately, plug only the blue cable"*.
   - At 14:11:00, helper unplugged the white cables, immediately killing the working PPPoE session.
   - The blue cable, plugged in hurriedly, either had a bad link or was plugged into an IPTV/MyTV port without DHCP. The node remained offline.
3. **Coordinator Denial Bias:**
   - When user presented screenshots showing the node was connected at 2:10 and disconnected at 2:11, coordinator initially dismissed the evidence, assuming the node had never connected.

### Agent Behavioral Correction (Critical Discipline)
- **Do NOT Argue Against Timestamp Evidence:** When the user provides a screenshot showing a recent `Last Seen` timestamp (e.g. `2:11 PM`), never claim "the device never came online".
- **Cross-Check Intervention Timeline Before Ordering Unplugs:** 
  If `LastSeen` matches 1–2 minutes after helper plugged the primary cables, the PRIMARY lines were working. Ordering an unplug destroys the established connection.
- **Default to "Plug All 3 Lines" Rather Than Cable Musical Chairs:** 
  Leave Line 1, Line 2, and Rescue all connected. OpenWrt's metric hierarchy (10 -> 20 -> 200) will automatically select the best active route without human error.

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

### 3. ISP Walled Garden / Captive Portal vs Real Internet
- **Symptom:** PPPoE establishes successfully and receives an IP in `172.17.x.x` (common on VNPT), but Tailscale bootstrap connections time out (`context deadline exceeded`) or return certificate mismatch errors.
- **Root Cause:** Newly provisioned fiber lines that have not completed administrative activation at the ISP billing system/OLT are placed into a "Walled Garden" / captive portal. All outbound HTTP/HTTPS requests are intercepted and redirected to the ISP's billing notice page, breaking TLS handshakes.
- **Verification via LuCI:**
  1. Go to **Network -> Diagnostics**.
  2. Under **Ping**, test `8.8.8.8`.
  3. If result is `100% packet loss` despite PPPoE interface showing connected, the line is in an ISP administrative hold and cannot reach the public internet until activated by the ISP local branch.

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
