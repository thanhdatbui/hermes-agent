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

## 2. Multi-MACVLAN Isolated Proxy Rotation (8 Ports)
To deploy 8 rotating proxy ports (e.g. 5101..5108) on a single physical PPPoE line without risking Tailscale out-of-band disconnection:
- See detailed architecture and scripts at: `references/multi-macvlan-pppoe-proxy-rotation-architecture.md`.
- **Golden Rule:** Every virtual PPPoE sub-interface (`wan_sub1..8`) MUST be pinned with `defaultroute='0'`, `peerdns='0'`, and routed via isolated tables (`table 101..108`). The default gateway `0.0.0.0/0` in the main routing table belongs strictly to the primary WAN maintaining Tailscale.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
