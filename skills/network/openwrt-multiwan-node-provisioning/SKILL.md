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
4. **Firewall Inbound Access:**
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
3. **Rescue Protocol for "Tailscale Not Showing Up":**
   - When on-site staff reports plugging in but Tailscale shows offline:
     1. Instruct staff to plug an Ethernet cable from their existing working home WiFi router into the **BLUE port** (rescue).
     2. Wait 60–90 seconds for OpenWrt boot + DHCP lease.
     3. Once Tailscale comes online, SSH into the node and inspect live logs:
        ```sh
        logread | grep -E "pppd|wan"
        ip -br link
        ```
     4. Check whether `lan1` / `lan2` link state is `UP` (cable detected) or `NO-CARRIER` (loose cable or ONT powered off), and verify authentication rejection reasons.
