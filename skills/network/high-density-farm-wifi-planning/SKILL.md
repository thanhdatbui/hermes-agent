---
name: high-density-farm-wifi-planning
description: High-density WiFi RF planning, physical layout, AP placement, and cabling for large Android phone farms (160+ devices, multi-tier metal racks, Aruba Instant IAP, PoE cabling).
tags: [wifi, rf-planning, aruba, high-density, phone-farm, poe, cabling]
---

# High-Density WiFi RF Planning for Android Phone Farms

Use this skill when designing, expanding, troubleshooting, or physically laying out WiFi infrastructure for high-density phone farms (e.g. 80–160+ Android devices on metal racks running automation tools).

---

## 1. Physical Placement & RF Architecture (Cross-Illumination)

### The Faraday / Metal Shadowing Problem
* Multi-tier metal racks containing dozens of closely packed smartphones create severe RF shadowing and local Faraday-cage effects (10–20 dB attenuation between tiers).
* **Never place all APs on one side or clustered in one zone.** Clustering APs within <1.5m in the same corner creates severe near-field RF saturation and receiver desensitization.

### Canonical Layout Rules
1. **Cross-Illumination (Opposite Angles):**
   * Place at least 1 AP on the **opposite wall / far corner (Line-of-Sight, 2.5m–3m)** aiming directly at the front of the rack.
   * Place 1 AP at the **top of the rack (face down)** to cover upper tiers.
   * Place 1 AP at the **bottom tier or far side (face up or side-inward, low Tx power)** to cover bottom tiers.
   * Place remaining APs at cross-angles (e.g. adjacent furniture/wall) to illuminate side angles.
2. **Antenna Orientation:**
   * Aruba APs (AP-325, AP-315) use hemispherical internal antennas radiating outwards from the front face (plastic dome with Aruba logo).
   * **Top rack mount:** Must point **face DOWN** into the phone trays (not facing the ceiling).
   * **Wall/Pole mount:** Must point **face forward** directly at the target phone racks.
   * Do not rely on loose hooks; secure APs with zip ties (cable ties) through the mounting bracket onto metal bars.
3. **Sleeping Space Separation:**
   * Keep high-power APs away from direct head-level sleeping areas. Use far room corners (e.g. entrance door / clothes rack / far foot of bed) for room-spanning cross-illumination.

---

## 2. Aruba Instant OS High-Density Tuning

* **5GHz Only (Disable 2.4GHz):** 2.4GHz only has 3 non-overlapping channels (1, 6, 11) and will collapse under 160 simultaneous transmitters. Force 100% clients to 5GHz.
* **Channel Width:** Use **20 MHz** (or max 40 MHz). Never use 80 MHz in dense environments (avoids Co-Channel Interference / CCI).
* **Channel Separation (Static Channels):**
   * AP 1 (Top Rack): **Channel 36** (UNII-1)
   * AP 2 (Cross Opposite): **Channel 149** (UNII-3)
   * AP 3 (Side Angle): **Channel 44** (UNII-1)
   * AP 4 (Bottom Rack): **Channel 157** (UNII-3)
* **Tx Power Management:**
   * Distant / Cross APs (2.5m–3m): **12–14 dBm**
   * Top Rack APs: **10–12 dBm**
   * Close-range / Bottom Rack APs (20cm–50cm): **6–8 dBm** (prevents receiver saturation on phones).
* **SSID Strategy & AP Zone Isolation (Strict 1 AP = 1 SSID):**
   * **The Cluster Broadcast Trap:** In an Aruba Instant (IAP) cluster, all APs broadcast all SSIDs simultaneously by default. If one AP is powered off or reboots, the surviving AP takes over all SSIDs (Failover). When the AP powers back on, stationary devices will remain stuck on a single AP unless forced.
   * **Strict AP Zone Binding:**
     * Gán `Zone: zone1` cho AP 1 (Top Rack / AP-325) và bind vào SSID `kibe 1` (gán cho Máy 01–40).
     * Gán `Zone: zone2` cho AP 2 (Cross Opposite / AP-325) và bind vào SSID `kibe 2` (gán cho Máy 41–80).
     * Gán `Zone: zone3`, `zone4` cho các AP mở rộng tương ứng.
     * **Kết quả:** Mỗi AP chỉ phát duy nhất SSID được chỉ định, đảm bảo phân bổ tải 40 máy/AP tuyệt đối 100%.
   * **Disable Client Match:** Phone farms are stationary; dynamic steering causes unnecessary roaming, disconnects automation sessions, and drops VPN/proxy tunnels.
   * **Farm Hardware Kill-Switch Isolation:** Farm Wi-Fi subnets block direct internet access at the router firewall. Non-farm devices (e.g. personal smartphones/laptops) connecting to farm SSIDs will show "No Internet Connection" unless configured with the local proxy port (e.g. `192.168.110.2:2000N`).
* **Aruba Management & API Protocol Quirks:**
   * **WebUI & swarm.cgi API Port:** Aruba Instant WebUI and API run on port `4343` (`https://<AP_IP>:4343/swarm.cgi`).
   * **API Protocol:** Uses POST requests to `/swarm.cgi` with form payload (`opcode=login`, `nosid=true`, `user=admin`, `passwd=...`) and header `X-Requested-With: XMLHttpRequest`.
   * **Automation Reference:** See `references/aruba-swarm-api-automation.md` for complete Python script recipes for swarm login, `opcode=config`, and `opcode=action` per-AP commands.
   * **Android Fleet Wi-Fi Automation:** See `references/android-wifi-automation-adb.md` for zero-UI Wi-Fi joining via `adb-join-wifi.apk` and fast parallel verification across 80+ devices.
   * **SSH Host Key:** Older Aruba Instant firmware uses `ssh-rsa` (OpenSSH requires `-oHostKeyAlgorithms=+ssh-rsa`).
* **Broadcast & Airtime Optimization:**
   * Enable `broadcast-filter all` / `broadcast-filter arp` (AP proxies ARP instead of flooding airtime).
   * Set Min Basic Rate (`a-basic-rates`) to **12 Mbps** or **18 Mbps** (eliminates low-rate beacon overhead).
   * Set Preferred Master on the most capable AP (e.g. AP-325 over AP-315).

---

## 3. Ethernet Cabling & PoE Power Delivery Rules

### The CCA (Copper-Clad Aluminum) Trap
* Cheap Cat6 patch cords often use **CCA (Nhôm mạ đồng)**.
* **Do NOT use CCA cables for PoE Access Points:**
  * Aluminum has ~60% higher resistance than pure copper. Under high load (15W–20W PoE 48V draw), CCA suffers severe **voltage drop (sụt áp)** and heats up, causing Aruba APs to reboot spontaneously under heavy farm workloads.
  * CCA causes port auto-negotiation to silently downgrade from **1 Gbps (1000M) to 100M**, choking bandwidth.
* **Only PoE lines require pure copper:** General PC/modem cables with dedicated DC power supplies do not suffer PoE voltage drop, but the main uplink (Modem ↔ MikroTik ↔ Switch) should remain 1 Gbps pure copper.

### Cable Selection Guidelines
* **PoE AP Drops:** Use **100% Pure Copper / Bare Copper (OFC)**:
  * Budget / Factory-molded: Vention Cat6 Round (Pure copper, molded RJ45), Hikvision Cat6 UTP (24AWG, DS-1LN6-UU), CommScope / AMP Cat6, Dintek Cat6.
  * High-EMI / Premium: Cat7 F/FTP / S/FTP (e.g. Ugreen NW107 PVC / NW150 braided nylon for anti-abrasion against metal rack edges).
* **Avoid Flat Cables (Dây dẹt):** Flat patch cords use ultra-thin 32AWG conductors which cause excessive resistance and thermal buildup over PoE. Always use round cables (24AWG–28AWG).

### Selective Cable Upgrade & Audit Discipline
* **Never replace all existing cables indiscriminately.**
* **Mandatory Upgrade (New Pure Copper):**
  * All patch cables from Switch PoE ➔ Aruba APs (prevents PoE voltage drop & reboot loop).
  * Main Uplink cable (Router / Gateway ➔ Switch).
* **Audit & Keep Existing (Non-PoE devices / PCs / box controllers):**
  * Inspect physical link speed and error counters (Winbox Interfaces / OS stats).
  * Windows check: `Get-NetAdapter | Select-Object Name, LinkSpeed, MediaConnectionState`
  * If LinkSpeed = 1 Gbps and Rx/Tx/FCS Packet Errors = 0, keep existing cables. Only replace individual cables if link downgrades to 100 Mbps or error rate rises under load.

---

## 4. Farm Switch & Topology Architecture

### Star Topology with Segmented Switches & Proxy Gateway
When operating multiple APs alongside worker PCs, local services, and a dedicated Mini PC PPPoE proxy node:
```text
[2x ISP WAN Lines (Bridge)]
        │ (2x Cat6 0.5m)
[Mini PC (MikroTik 30 PPPoE)] ──(1x Cat6 0.5m LAN)──┐
                                                     ▼
[Ruijie 3200 (Gateway/DHCP)] ──(LAN 1: Cat6 0.5m)──► [Switch PoE 8P] ──► 4x Aruba APs (IAP Cluster)
                             ──(LAN 2: Cat6 0.5m)──► [Switch 5P]   ──► 3x Worker PCs
```
* **Keep Aruba APs on a Single PoE Switch:** Aruba Instant (IAP) cluster nodes exchange continuous heartbeat and dynamic RF calibration packets. Keeping them on the same physical switch minimizes inter-AP latency (0ms), isolates cluster traffic from heavy PC transfers, and centralizes PoE budget management.
* **Isolate PC & Worker Traffic:** Worker PCs connected to a separate switch prevent large file transfers (video uploads, system images) from saturating switch backplane switching buffers used by the AP cluster.
* **Mini PC Multi-WAN PPPoE Proxy Invariants:**
  * **Cabling:** 2x short Cat6 (0.5m) from ISP modem (Bridge mode) into Mini PC WAN1 & WAN2; 1x short Cat6 (0.5m) from Mini PC LAN into Ruijie/Switch.
  * **CPU & Session Tracking:** 160 phones generate 16,000–30,000 concurrent sessions. Policy-Based Routing (PBR/Mangle) disables FastPath on RouterOS, routing all packets through CPU.
  * **MSS Clamping:** PPPoE encapsulation lowers MTU (1480–1492). Bắt buộc bật `Change MSS` clamping về `1440`–`1452` trên RouterOS để chống drop gói tin ngầm (fragmentation timeout) khi lướt TikTok/automation.

---

## 5. Aruba Virtual Controller DHCP Scope & Centralized Gateway Routing

When routing farm traffic through a central MikroTik / PBR proxy node:
* **Centralized DHCP Scope on Aruba Virtual Controller:**
  * Configure a central DHCP Scope (e.g. `kibe_dhcp`, subnet `192.168.110.0/24`).
  * Set **Default Gateway** directly to the MikroTik IP (`192.168.110.2`).
  * Set **DNS Servers**: `8.8.8.8`, `1.1.1.1`.
  * Bind the scope directly to all farm SSIDs (e.g. `kibe 1`, `kibe 2`).
* **Zero-Touch Client Configuration:**
  * Keep all Android farm devices on standard **DHCP (Automatic IP)** mode — no manual per-phone static IP or gateway configuration required.
  * When updating DHCP gateway on Aruba: trigger a fleet-wide Wi-Fi toggle (`adb shell "svc wifi disable; sleep 1.5; svc wifi enable"`) to immediately release and renew the DHCP lease and gateway route on all devices.
* **Public IP Inspection via CDP on Non-Rooted Devices:**
  * On devices without `curl` in shell: launch browser (`am start -n com.sec.android.app.sbrowser/.SBrowserMainActivity -d https://api.ipify.org` or Chrome), forward abstract socket `Terrace_devtools_remote` / `chrome_devtools_remote` to local port, and evaluate `document.body.innerText` via WebSocket/CDP to verify outbound public IP.

---

## 6. Farm Scale-Up: Box USB vs. Box LAN Infrastructure Comparison

When scaling past 80+ devices, evaluate the physical and RF bottlenecks:

### Bottlenecks & Trade-offs
1. **Box USB Limits:**
   * **USB Controller Endpoints:** xHCI host controllers limit endpoints (64–128 per controller). A standard PC host with onboard USB can only reliably drive 15–20 Android devices before bus contention occurs. Scaling requires dedicated Quad-Chip PCIe USB expansion cards (e.g. FL1100EX / Renesas controllers).
   * **Airtime Congestion:** 100% of automation traffic and video uploads must go over Wi-Fi, increasing beacon/airtime overhead on APs.
2. **Box LAN Advantages & Technical Requirements:**
   * **Control Plane Isolation:** PC Master communicates via Ethernet (`eth0` / TCP 5555), completely offloading ADB/ATX traffic from the Wi-Fi spectrum.
   * **Dual Interface Routing:** Ethernet must handle only management traffic (`DEFROUTE=no`, no default gateway), while Wi-Fi (`wlan0`) serves 100% Internet/proxy traffic.
   * **Hardware & ROM Prerequisites (Samsung S7 Android 8):**
     * **NTC Dummy Battery:** Must include 10kΩ NTC resistor (B=3950) on `BATT_TEMP` to prevent false low-temperature battery alarms (`-15°C`) and thermal throttling.
     * **OTG VBUS Isolation:** Power load switch with True Reverse Current Blocking on 5V VBUS to prevent back-feed damage to the phone mainboard.
     * **ROM Cleanliness:** Base Stock Android 8, `SELinux Enforcing`, `ro.build.type=user`, `ro.build.tags=release-keys`, auto-enabling `service.adb.tcp.port=5555` with pre-provisioned RSA keys.
     * **AQL Standard:** Follow ISO 2859-1 (General Inspection Level II) for lot acceptance (100% voltage/battery screening + 24h stress test).


