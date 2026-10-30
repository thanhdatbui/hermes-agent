# DNS Domain Mapping and Port Planning for Remote Multi-WAN Proxy Nodes

When integrating remote multi-WAN proxy nodes (e.g. OpenWrt Xiaomi R3G running 16 rotating proxies over Tailscale) into local farm infrastructure (Android S7 Farm, GPM, OmniRoute):

## 1. Port Namespace Isolation (Avoid Collision with Co-located Clusters)
- **Problem**: When a local or remote site already has an existing multi-port proxy farm (e.g., MobiProxy using ports `5101..5138`), deploying secondary nodes with overlapping port ranges causes immediate configuration chaos and port conflict in downstream routing scripts.
- **Rule**: Allocate dedicated, contiguous port blocks starting beyond the existing range:
  - MobiProxy baseline: `5101..5138` (LAN 1..4, 8 ports per line)
  - Dedicated R3G / Secondary Node: Start strictly at `5141` onwards:
    - Line 1 (primary lifeline / WAN2): `5141..5148` (8 proxies)
    - Line 0 (secondary line / WAN1): `5151..5158` (8 proxies)
  - This leaves clean gaps between blocks and zero risk of overlapping with ports 5101-5138.

## 2. Cloudflare DNS Mapping for Headless Tailscale Nodes
- **Why Domain over Raw IP?**
  - Android farm devices on Aruba Wi-Fi cannot run Tailscale clients directly (risk of VPN driver overhead and packet dropping).
  - Central gateways and scripts reference hostnames (e.g., `tb.taadaa.click`) rather than hardcoding Tailscale CGNAT IPs (`100.115.94.49`), enabling seamless re-routing or gateway NAT forwarding without modifying farm device assignments.
- **Cloudflare DNS Configuration**:
  - Add an `A` record pointing to the Tailscale IP of the node:
    - Name: `tb` (for `tb.taadaa.click`)
    - IPv4 Address: `100.115.94.49`
    - Proxy Status: **DNS only** (`DNS only - reserved IP`). Cloudflare proxy MUST be disabled because Tailscale CGNAT addresses (`100.64.0.0/10`) cannot be proxied through Cloudflare edge reverse proxies.
    - TTL: `Auto` or `2 min` / `5 min`.
- **Account Verification Pitfall**:
  - Confirm the exact Cloudflare account managing the primary zone. When multiple Google profiles exist (e.g. `thanhdatbui19951@gmail.com` vs `thanhdatbui1995@gmail.com`), zones and domains are bound to specific account IDs. Check the zone list before attempting to create records.
