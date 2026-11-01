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

Key references:
- Single-NIC Managed Switch VLAN Trunking (Router-on-a-Stick) & hardware triage: `references/single-nic-vlan-trunk-and-hardware-triage.md`
- Multi-MACVLAN PPPoE & Isolated Proxy Rotation with Tailscale: `references/multi-macvlan-pppoe-proxy-rotation-architecture.md`
- Xiaomi R3G Low-RAM Tinyproxy OOM & OpenWrt Firewall Isolation Hazards: `references/r3g-low-ram-tinyproxy-oom-and-firewall-hazards.md`
- Fail-Safe Firewall Hardening & Dead Man's Switch on Headless Tailscale Nodes: `references/dead-mans-switch-and-headless-firewall-safety.md`
- Asymmetric Routing Trap & Direct WAN Tinyproxy Bind Hazard: `references/asymmetric-routing-and-tinyproxy-bind-hazard.md`
- Direct WAN Subnet Whitelist vs Single IP Trap & ISP Dynamic Pool: `references/direct-wan-subnet-whitelist-vs-single-ip-trap.md`
- OpenWrt Tinyproxy Multi-WAN Egress Fallback & Default Route Pitfalls: `references/openwrt-tinyproxy-multiwan-egress-and-cgnat-pitfalls.md`
- R3G Direct WAN MobiProxy Parity & Anti-Compression Bias Architecture: `references/r3g-direct-wan-mobiproxy-parity-and-compression-bias.md`
- R3G OpenWrt LuCI Ubus Management, Direct WAN Cloudflare DDNS & Egress Binding: `references/r3g-luci-ubus-direct-wan-and-cf-ddns.md`
- Viettel FTTH CGNAT Profile Root Cause & Technical Support Dispatch Protocol: `references/viettel-cgnat-profile-and-support-dispatch.md`
- OpenWrt Multi-WAN PPPoE: CGNAT (100.x / 172.x) vs Missing MAC / Switch Port Conflict: `references/openwrt-pppoe-cgnat-vs-mac-duplication-pitfall.md`

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
