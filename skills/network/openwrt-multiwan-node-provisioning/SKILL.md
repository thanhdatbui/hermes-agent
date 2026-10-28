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

## References

- `references/claude-audit-and-field-triage-r3g.md` — Detailed case study of Xiaomi R3G deploy, Claude CLI production audit remediation, and the premature lifeline unplug incident.
