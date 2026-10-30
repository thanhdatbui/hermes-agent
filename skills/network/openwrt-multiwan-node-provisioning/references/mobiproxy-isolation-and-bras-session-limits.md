# Production Triage & Farm Network Isolation: MobiProxy vs Node Deployment

## 1. Absolute Boundary: MobiProxy vs OpenWrt / Custom Nodes
- **Production Asset Immutability:** Dedicated farm proxy appliances (e.g. MobiProxy at `test.taadaa.click`, 32 proxies on 4 physical LAN ports) belong to dedicated line allocations.
- **NEVER Repurpose Production Farm Ports:** If a line fails on a new router/node under test, NEVER suggest or execute migrating the line permanently to an existing farm hardware box (e.g. plugging line into Lan3 on MobiProxy).
- **Temporary A/B Triage Discipline:** If an existing box is temporarily used to verify line health (testing if ISP BRAS/cable works):
  1. Record the exact baseline configuration (e.g. `Lan3` account `hyn_gftth_datlp0` / password).
  2. Perform the connectivity test.
  3. **IMMEDIATELY REVERT** the production box back to baseline without waiting for user prompting.
  4. Never leave the production box in a degraded state (e.g. 0 live proxies due to blank fields or overwritten accounts).

## 2. Port Planning & Farm Anti-Collision Standards
When introducing new multi-WAN / proxy rotation nodes into an active farm:
- **Port Allocation Map:**
  - `MobiProxy` (Production): Ports `5101` - `5138` (across Lan1 - Lan4).
  - `R3G Thái Bình` (Multi-WAN Node):
    - Preferred starting port: `5141` or dedicated block `6101+` to guarantee zero port overlap across device inventories.
    - Standard 2-Line Allocation: 8 ports on Line 1 (`5141..5148`), 8 ports on Line 0 (`5151..5158`).
- **ISP BRAS Concurrent Session Limits (Viettel FTTH):**
  - Viettel BRAS profiles (e.g., `TBH8001BRA01`) enforce a hard maximum of **8 concurrent PPPoE sessions** per contract/line.
  - Attempting to dial a 9th session (`mvl18`) triggers immediate `Timeout waiting for PADO packets` (PADI dropped by BRAS).
  - Always bound MACVLAN provisioning scripts to max 8 sub-interfaces per physical fiber line.
