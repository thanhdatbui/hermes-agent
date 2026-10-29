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
- **Step 3 (Reconfigure LAN Ports):**
   - Now that the session runs over the blue port, safely remove `lan1` and `lan2` from `br-lan`.
   - Assign `lan1` to `interface 'wan'` and `lan2` to `interface 'wan2'`.
   - Set protocol to `pppoe` with corresponding credentials.
   - Save and commit persistently (`uci commit`).

---

## 3. Remote Triage & Diagnostic Invariants

- **DSA Bridge PADO Swallowing Trap:** When converting switch ports (`lan1`, `lan2`) to PPPoE, `rx_handler` of `br-lan` intercepts PADO frames if ports remain in `network.@device[0].ports`, causing persistent `Timeout waiting for PADO packets`. Always execute `uci del_list network.@device[0].ports='lan1'` and verify via `ls /sys/class/net/br-lan/brif`.
- **Remote Web Terminal (ttyd) Paste Stripping:** Pasting chained commands via UltraViewer/AnyDesk strips `&&`, `&`, and `2>&1`, breaking shell scripts or locking daemons in foreground. Send strictly **one discrete command per turn**. Use `start-stop-daemon -S -b` instead of trailing `&`.
- **Remote Factory Reset Guard:** NEVER execute `firstboot` or LuCI reset remotely through host PC. IP reverts to `192.168.1.1` (conflicting with host ISP modem), blue port reverts to WAN with firewall REJECT, dropping UltraViewer and permanently locking out the node.
- **Viettel PPPoE Dual-Stack & Walled Garden:** Viettel allocates IPv6 via DHCPv6-PD (`2402:800:...`) independently of IPv4. Receiving a public IPv6 does NOT mean IPv4 is open. If IPv4 receives `172.17.x.x` and drops `8.8.8.8`, the ISP subscriber profile is in a walled-garden/inactive state. ONT bridge mode is untagged by default; do NOT add 802.1Q VLAN 35 sub-interfaces unless explicitly verified.

See `references/pppoe-pado-bridge-trap-and-remote-triage-pitfalls.md` for full operational details.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
