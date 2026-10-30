# Single-NIC Managed Switch VLAN Trunking (Router-on-a-Stick) & Proxy Hardware Triage

## 1. Single-NIC Multi-WAN Architecture (Router-on-a-Stick)
When a user or partner wants to connect multiple physical ISP lines (e.g., 2 to 8 FTTH PPPoE lines) into a Mini PC running RouterOS, OpenWrt, or Linux:
- **Misconception**: Believing the Mini PC must have 4 to 6 physical NIC ports (1 port per WAN line). Sellers often use this misconception to upsell multi-port hardware.
- **Production Truth (VLAN 802.1Q Trunking)**:
  - A single Gigabit Ethernet port on a standard Mini PC can aggregate multiple independent WAN lines using an inexpensive 5-port or 8-port **Managed Switch** (supporting 802.1Q VLAN, ~250k - 350k VND / $10 - $15).
  - **Switch Configuration**:
    - Port 1 to 4: Configured as untagged **Access Ports**, each assigned to a separate VLAN ID (e.g., WAN 1 -> VLAN 101, WAN 2 -> VLAN 102, WAN 3 -> VLAN 103, WAN 4 -> VLAN 104).
    - Port 5: Configured as a tagged **Trunk Port** carrying VLANs 101-104, connected directly to the single LAN port of the Mini PC.
  - **Mini PC Configuration (OpenWrt/RouterOS/Linux)**:
    - Create virtual sub-interfaces on the physical NIC (e.g., `eth0.101`, `eth0.102`...).
    - Each sub-interface operates as an independent WAN interface to dial PPPoE, bind isolated policy routing tables, and terminate rotating proxy ports (via Sing-box, 3proxy, or tinyproxy).
  - **Bandwidth Calculation**: 1 Gbps NIC easily handles 4-8 residential fiber lines (100-150 Mbps each) for phone farm traffic without saturation.

## 2. Hardware Selection & Pitfalls for 24/7 Proxy Nodes
- **High-TDP Fanless Trap (e.g., Core i7 Gen 2 / Sandy Bridge, 65W-95W)**:
  - Sellers frequently market "Core i7" industrial PC chassis (e.g., LUSTER VC-5000) with 6 NICs for ~2 million VND (~$80).
  - **Severe Pitfall**: These 2011-era 32nm chips consume high power and generate excessive heat. In sealed aluminum fanless cases running 24/7, temperatures stay at 70°C–80°C+, causing thermal throttling, capacitor degradation, PSU burnout, or sudden kernel freezes.
- **Recommended Alternatives**:
  1. **Zero Hardware Cost**: Reuse existing single-NIC Mini PCs by adding an external Managed Switch (~250k VND).
  2. **Modern Low-TDP Soft Routers**: Intel N5105 / J4125 / J4105 / N100 (10W-15W TDP, 14nm/10nm/Intel 7), 4x 2.5Gbps Intel i225/i226 NICs, running cool and stable for years.

## 3. Communication Discipline (Direct & Concise)
- When advising non-technical partners or users:
  1. Address the specific hardware buying decision **FIRST** with clear verdict (Don't buy / Overpriced / Thermal hazard).
  2. Present the low-cost alternative immediately (Managed Switch + existing PC).
  3. Keep the initial response short and jargon-free; save deep routing/VLAN explanations for when explicitly requested.
