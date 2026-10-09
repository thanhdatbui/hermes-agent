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
1. **Cross-Illumination & 3D Diagonal Separation:**
   * **Rack Placement (2x APs on metal rack):** Place APs diagonally opposite across the rack frame (e.g. **Top-Left corner** for upper tiers and **Bottom-Right corner** for lower tiers). This maximizes 3D physical separation ($\sqrt{H^2 + W^2}$), prevents vertical near-field RF coupling, and balances left-to-right horizontal coverage across wide phone trays. Avoid vertical collinear stacking directly above/below each other on the same side.
   * Place at least 1 AP on the **opposite wall / far corner (Line-of-Sight, 2.5m–3m)** aiming directly at the front of the rack.
   * Place remaining APs at cross-angles (e.g. adjacent furniture/wall) to illuminate side angles.
* **Antenna Orientation & Rack Surface Resting:**
  * Aruba APs (AP-325, AP-315) use hemispherical internal antennas radiating outwards from the plastic front dome (Aruba logo).
  * **Top rack mount:** Must point **face DOWN** into the phone trays. Resting the plastic front dome directly face-down on open metal wire mesh shelves is acceptable and highly effective: the open mesh allows 5GHz RF penetration while the rear aluminum heatsink faces upward into ambient air for passive convective cooling.
  * **Bottom rack mount:** Point **face UP** or tilted 45° inward toward bottom phone trays.
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
* **Tx Power Management (Hierarchical by Distance):**
   * Distant / Cross APs (1.5m–3m+): **12–15 dBm** (bù suy hao cự ly truyền sóng trong không gian phòng).
   * Rack-Mounted APs (Near-Field <0.5m): **6–9 dBm** (khóa cứng `min-tx-power 6`, `max-tx-power 9` trên cả `arm` và `rf dot11a-radio-profile` để chống bão hòa bộ thu RSSI trên điện thoại).
   * 🛑 **CẤM TỰ Ý TĂNG CÔNG SUẤT AP TRÊN KỆ SẮT LÊN 15 dBm:** Con AP-325 đặt trên kệ kim loại nếu bị nâng lên 15 dBm sẽ gây phản xạ kim loại dữ dội, bão hòa bộ thu (receiver desense), gây kickout hàng loạt (`Wlan driver excessive tx fail quick kickout`) và làm hỏng RF của toàn bộ khay điện thoại lân cận. Tuyệt đối tuân thủ trần 6–9 dBm (tối đa không vượt quá 10–12 dBm trong tình huống kiểm tra có kiểm soát).
   * **Lựa chọn Channel (Kênh thấp UNII-1 vs DFS):** Dải 116E (DFS) trên Samsung Galaxy S7 dễ bị chập chờn khi roaming hoặc bắt tay ban đầu; ưu tiên dùng kênh UNII-1 sạch như **36E** (hoặc 44/48) ở mức công suất chuẩn 6–9 dBm để các máy cũ dễ bắt sóng.
* **Master / Virtual Controller (VC) Placement:**
   * Pin or prefer the VC on a distant AP (e.g. AP-315 in clean RF room space) rather than a rack-mounted AP subject to high RF noise, vibration, and physical cabling adjustments during farm operations.
* **SSID Strategy & AP Zone Isolation (Strict 1 AP = 1 SSID):**
  * **The Cluster Broadcast Trap:** In an Aruba Instant (IAP) cluster, all APs broadcast all SSIDs simultaneously by default. If one AP is powered off or reboots, the surviving AP takes over all SSIDs (Failover). When the AP powers back on, stationary devices will remain stuck on a single AP unless forced.
  * **Auto-Connect Isolation Trap & Password Uniformity:** Android chỉ tự động kết nối nếu profile SSID đó đã được lưu trong máy. Dù tất cả các AP dùng chung một mật khẩu Wi-Fi (ví dụ `19051995` để tiện quản lý và chạy script), việc tách tên SSID độc lập (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`) sẽ ngăn chặn hoàn toàn điện thoại tự động nhảy sang AP khác nếu chưa từng lưu profile đó.
  * **Strict AP Zone Binding:**
    * Gán `Zone: zone1` cho AP 1 (AP-325 IP `.253`, MAC `b0:b8:67:cd:bf:8a`) và bind vào SSID `kibe 1` (gán cho Máy 01–40).
    * Gán `Zone: zone2` cho AP 2 (AP-325 IP `.252`, MAC `34:fc:b9:cf:5a:bc`) và bind vào SSID `kibe 2` (gán cho Máy 41–80).
    * Gán `Zone: zone3` cho AP 3 (Distant Room AP-315 #1 - Master VC, IP `.251`, MAC `20:a6:c0:c7:6b:58`) và bind vào SSID `admin 1` (mở rộng/quản trị).
    * Gán `Zone: zone4` cho AP 4 (Distant Room AP-315 #2, IP `.250`, MAC `20:a6:c0:c6:6d:1a`) và bind vào SSID `admin 2` (mở rộng/quản trị).
  * **Phòng Chống Bẫy ASSOCIATION_REJECTION / BSSID Blocklist Trên Client:**
    - Khi máy client bị AP từ chối bắt tay (do kẹt session cũ `Sapcp Ageout`), Android 8 tự động đưa AP vào BSSID Blocklist (`NETWORK_SELECTION_TEMPORARY_DISABLED disableReason=NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION`).
    - Lệnh `svc wifi` hoặc reboot KHÔNG xóa được cờ này. BẮT BUỘC dùng cơ chế 2 tầng: (1) radio toggle nhẹ, (2) ép join qua `adb-join-wifi.apk` với cờ `--es ssid "<SSID>"` (BẮT BUỘC dùng `--es`, nếu dùng `-e` chuỗi có khoảng trắng như `"kibe 1"` sẽ bị shell cắt thành `"kibe"`, làm quét vô tận) để giải phóng blocklist qua Java API.
    - 🛑 **BẤT BIẾN QUY HOẠCH 40 MÁY/AP (CẤM NHẢY CHÉO ĐỂ TRỐN LỖI):** Tuyệt đối duy trì cố định M1–M40 ➔ `kibe 1` (AP .253), M41–M80 ➔ `kibe 2` (AP .252), M201–M240 ➔ `admin 1` (AP .251), M241–M280 ➔ `admin 2` (AP .250). CẤM đề xuất nhảy chéo AP để "né lỗi" hoặc kết nối SSID ngoài (`Dat`) để chữa cháy làm vỡ cân tải farm và nghẽn radio AP đích.
    - **Bẫy Nhiễm Độc Profile Đã Lưu (Saved SSID Poisoning):** Khi lỡ kết nối SSID ngoài (`Dat`), Android OS tự lưu profile vào `WifiConfigStore.xml` với `PRIO: 100`. Chỉ xóa code trên host PC là vô tác dụng; bắt buộc phải chạy lệnh quên mạng (Forget Network) trên từng điện thoại thật để triệt tiêu việc OS tự ý nhảy sang SSID ngoài khi radio bounce. Lệnh `adbjoinwifi` bắt buộc kèm cờ `-S` để force-stop Activity trước khi nạp lại SSID chuẩn.
    - Xem chi tiết tại `references/android-wifi-automation-adb.md` và `references/farm-wifi-aruba-and-network-hygiene.md`.
     * **Quy hoạch dải IP quản trị cụm 4 AP:** Toàn bộ 4 AP nằm trong dải cố định `.250` – `.253` (`.250`: AP-315 #2, `.251`: AP-315 #1 VC, `.252`: AP-325 #2, `.253`: AP-325 #1).
     * **Phân biệt IP Tĩnh Phần Cứng (Flash ap-env) vs DHCP Reservation (Router Ruijie):**
       - Đọc `show ap-env` trên từng AP qua SSH: Nếu có trường `ipaddr: 192.168.110.X`, AP đã được set cứng IP tĩnh trong flash bootloader, khi khởi động sẽ tự giữ IP này mà không xin DHCP từ Ruijie.
       - Nếu `show ap-env` không có dòng `ipaddr`, AP phụ thuộc vào DHCP Reservation (Static Lease theo MAC) trên router gateway Ruijie/MikroTik.
     * **Phát hiện Bẫy SSID Phát Đa Vùng (Multi-Zone Broadcast Trap):**
       - Khi một SSID profile có trường `zone` liệt kê nhiều zone (ví dụ `zone zone1,zone2,zone3,zone4` như SSID `Dat`) hoặc để trống zone (`zone: -`), SSID đó sẽ được phát đồng loạt trên tất cả các AP trong cụm (kể cả 2.4GHz nếu để `rf-band all`).
       - Đối soát bằng `show network` và `show ap bss-table` trên từng node để đảm bảo SSID farm chỉ active đúng 1 zone duy nhất.
     * **🛑 Bẫy Suy Đoán Vị Trí Vật Lý (Top vs Bottom Rack Assumption):** Tên SSID (`kibe 1` / `kibe 2`) và số thứ tự Zone (`zone1` / `zone2`) CHỈ LÀ LOGICAL MAPPING trong Aruba Virtual Controller, TUYỆT ĐỐI KHÔNG tự ý khẳng định cục nào nằm tầng trên hay tầng dưới của kệ sắt khi user chưa xác nhận. Thực tế operator có thể lắp ngược lại hoặc hoán đổi vị trí khay.
     * **3 Cách Xác Định Cục AP Nào Phát SSID Mà Không Cần Đoán Mò:**
       1. **Xem tem MAC / Serial ở mặt sau AP:** Đọc BSSID từ máy client qua `adb shell "dumpsys wifi | grep mWifiInfo"` (ví dụ BSSID `b0:b8:67:5b:f8:b0` thuộc AP `.253`), đối chiếu với tem nhãn MAC LAN/Radio in trên lưng thiết bị.
       2. **Dò cự ly bằng Wi-Fi Analyzer / Điện thoại:** Đưa điện thoại lại sát từng con AP trên kệ sắt; con nào phát SSID mục tiêu có cường độ sóng vọt lên đỉnh (-20 dBm đến -30 dBm) chính là con AP đó.
       3. **Nháy đèn LED định vị (Locate Blink):** Gửi lệnh qua Aruba CLI/API (`ap-leds blink` hoặc action qua `swarm.cgi`) để nháy đèn LED phía trước của con AP mục tiêu, nhận diện trực quan bằng mắt thường mà không làm rớt mạng bất kỳ máy nào.
     * **Dynamic Radio State Activation:** In Aruba InstantOS, a slave AP that has an assigned zone will keep its 5GHz radio in disabled/standby state (`radio0 Channel: -`) until an active SSID profile with that matching zone is configured in the Swarm. As soon as the SSID profile is bound to the zone, the AP dynamically brings up the radio and selects an operational channel.
     * **Kết quả:** Mỗi AP chỉ phát duy nhất SSID được chỉ định, đảm bảo phân bổ tải 40 máy/AP tuyệt đối 100%.
   * **Disable Client Match:** Phone farms are stationary; dynamic steering causes unnecessary roaming, disconnects automation sessions, and drops VPN/proxy tunnels.
   * **Farm Hardware Kill-Switch Isolation:** Farm Wi-Fi subnets block direct internet access at the router firewall. Non-farm devices (e.g. personal smartphones/laptops) connecting to farm SSIDs will show "No Internet Connection" unless configured with the local proxy port (e.g. `192.168.110.2:2000N`).
* **Aruba Management & API Protocol Quirks:**
   * **🛑 Farm Invariant - CẤM tự ý can thiệp AP khi fix điện thoại lẻ:** Khi nhận lệnh cấu hình/kết nối Wi-Fi cho một máy cụ thể (`[MÁY N]`), CHỈ thao tác trên điện thoại qua ADB/Settings. CẤM TUYỆT ĐỐI tự ý gọi API Aruba (`swarm.cgi`), đổi passphrase, reboot/reload AP. Việc gián đoạn AP sẽ làm rớt Wi-Fi 40 máy cùng Rack, gây fail hàng loạt phiên nuôi nick (`blocked-proxy-vpn`).
   * **Bẫy Interactive Prompt khi cấu hình `ap-env`:** Lệnh CLI `ap-env iap_zone <zone>` luôn kích hoạt câu hỏi tương tác: `Do you want to reset the system to take iap_zone into effect(y/n):`. Tuyệt đối không gửi chuỗi lệnh nối tiếp (như `write memory`) vào prompt này vì ký tự đầu sẽ bị hiểu là hủy hoặc gõ lệnh rác vào AP.
   * **Bẫy Tràn Zone (Zone Bleed / Multi-Zone Collapse):** Tuyệt đối không cấu hình AP đơn lẻ chứa nhiều zone (vd `zone1,zone2,zone3,zone4`). Khi AP phát nhiều SSID cùng lúc, điện thoại từ các rack khác sẽ tràn sang dồn tải (lên tới 120+ máy/AP), làm vỡ quy hoạch 40 máy/AP và gây nghẽn airtime toàn cụm.
   * **Chuẩn phân bổ 40 máy/AP:** Cụm AP thiết kế cố định 40 máy/AP (AP .253 cho Rack 1 M1–M40; AP .252 cho Rack 2 M41–M80). Nếu một máy tầng dưới bắt nhầm vào `kibe 1`, AP sẽ bị đầy tải slot (39–40 máy) khiến các máy còn lại của Rack 1 bị từ chối kết nối (`ASSOC-REJECT`). Tuyệt đối không để máy bắt chéo SSID.
   * **WebUI & swarm.cgi API Port:** Aruba Instant WebUI and API run on port `4343` (`https://<AP_IP>:4343/swarm.cgi`).
   * **Ruijie Gateway Static Reservation & Dual-Tier Anchor:** See `references/ruijie-gateway-static-ip-reservation.md` for exact navigation (`Khác` ➔ `LAN` ➔ `Địa chỉ IP tĩnh`), MAC binding table, and dual-tier anchoring across AP `ap-env` and Ruijie DHCP.
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

### The Dual DHCP / Rogue DHCP Server Race Trap (Ruijie vs. MikroTik L2 Contention)
* **Root Cause & Symptom:**
  * When an upstream router/AP (e.g. Ruijie Reyee at `192.168.110.1`) and a proxy router (e.g. MikroTik at `192.168.110.2` / `192.168.10.254`) both run active DHCP servers on the same untagged physical Layer 2 switch port (e.g. MikroTik `ether3`), a **DHCP Race Condition** occurs.
  * Devices connecting to the **same SSID and BSSID** (e.g. `kibe 1` BSSID `b0:b8:67:5b:f8:b0`) receive split IP pools: some get `192.168.110.x` (gateway `192.168.110.1`, domain `lan`) while others get `192.168.10.x` (gateway `192.168.10.254`).
  * MikroTik DHCP lease table (`/rest/ip/dhcp-server/lease`) accumulates multiple `status: conflict` entries when pool addresses collide or ARP replies arrive from uncoordinated dynamic leases.
  * **Intermittent Timeouts:** When MikroTik reboots (or PPPoE/PBR mangle resets), devices leased to `192.168.10.254` lose routing/Internet access entirely, and host PCs on `192.168.110.x` timeout when reaching `192.168.10.x` devices until inter-VLAN forwarding settles.
* **Fast Diagnostic Checklist:**
  1. **Fleet Subnet Scan across ADB:**
     ```bash
     python -c '
     import subprocess, re
     devs = [l.split()[0] for l in subprocess.check_output(["adb", "devices"]).decode().splitlines() if "\tdevice" in l]
     subnets = {}
     for d in devs:
         try:
             out = subprocess.check_output(["adb", "-s", d, "shell", "ip -4 addr show wlan0"], timeout=2).decode()
             m = re.search(r"inet (192\.168\.\d+\.\d+)", out)
             if m:
                 sn = ".".join(m.group(1).split(".")[:3])
                 subnets[sn] = subnets.get(sn, 0) + 1
         except: pass
     print("Fleet Subnets:", subnets)
     '
     ```
     If multiple `192.168.x` subnets appear on the same SSID, two DHCP servers are broadcasting on the L2 domain.
  2. **Authoritative Gateway & Domain Check per Device:**
     ```bash
     adb -s <serial> shell "dumpsys connectivity | grep -A 10 'NetworkAgentInfo.*WIFI'"
     ```
     Examine `Routes`, `DnsAddresses`, and `Domains`: domain `lan` with gateway `192.168.110.1` indicates Ruijie; domain `null` with gateway `192.168.10.254` indicates MikroTik.
  3. **MikroTik REST API Audit:**
     ```bash
     curl -s -u admin:N0spam@@ -X GET http://192.168.110.2:9090/rest/ip/dhcp-server/lease
     ```
     Check if the target MAC is `dynamic: true` vs `dynamic: false` (static lease), and inspect `status` (`bound` vs `conflict`).
* **Definitive Remediation:**
  * **Option A (Preferred):** Disable DHCP Server on Ruijie Reyee WebUI (`http://192.168.110.1`), putting it in pure AP Bridge mode, and let MikroTik manage 100% of DHCP leases and static reservations.
  * **Option B (True VLAN Isolation):** Tag the farm SSID with 802.1Q VLAN ID (e.g. VLAN 10) on the AP, and bind the MikroTik DHCP server to sub-interface `vlan10_kibe` (never physical untagged `ether3`).

### Aruba Virtual Controller Internal DHCP Server Trap (172.31.98.1 Rogue Leases)
* **Triệu chứng & Hiện tượng:**
  * Sau khi đã vô hiệu hóa thành công DHCP Server trên MikroTik qua REST API (`PATCH /rest/ip/dhcp-server/*1` với `{"disabled": "true"}`), chạy rolling cycle Wi-Fi cho farm thì đa số máy chuyển sang `192.168.110.x` (Ruijie Gateway `192.168.110.1`), nhưng vẫn còn một số máy lẻ tiếp tục nhận lại IP dải `192.168.10.x`.
* **Nguyên nhân gốc rễ (Root Cause):**
  * Trên cụm Aruba Instant AP, Virtual Controller (VC) chạy một gateway ảo ngầm tại IP `172.31.98.1`. Nếu trên Swarm có cấu hình DHCP nội bộ (Local DHCP Scope) hoặc gán dải cho VLAN 10, chính con AP Aruba (ví dụ AP-315 MAC `20:a6:c0:c7:6b:58` tại IP `192.168.110.208`) sẽ đứng ra trả lời gói tin DHCP DISCOVER ngay tại tầng AP.
  * Do AP nằm ngay cạnh điện thoại, gói tin `OFFER` từ `172.31.98.1` đến nhanh hơn vài trăm milliseconds so với gói `OFFER` từ Ruijie Gateway (`192.168.110.1`). Điện thoại chọn gói đến trước và gửi `REQUEST` cho dải `192.168.10.x`, khiến Ruijie gửi gói `NAK, reason wrong server-ID`.
* **Kỹ thuật trích xuất gói tin DHCP trực tiếp trên Android:**
  * Chạy lệnh tra cứu O(1) từ buffer log mạng của thiết bị:
    ```bash
    adb -s <serial> shell "dumpsys wifi | grep -i dhcp"
    ```
  * Nhận diện bằng chứng rõ ràng:
    ```text
    RX 20:a6:c0:c7:6b:58 > <phone_mac> ipv4 172.31.98.1 > 192.168.10.x udp 67 > 68 dhcp4 ... OFFER, lease time 86400
    TX <phone_mac> > ff:ff:ff:ff:ff:ff ipv4 0.0.0.0 > 255.255.255.255 udp 68 > 67 dhcp4 ... REQUEST, desired IP /192.168.10.x
    RX 28:d0:f5:2a:62:4a > <phone_mac> ipv4 192.168.110.1 > 192.168.110.x udp 67 > 68 dhcp4 ... OFFER, lease time 7200
    RX 28:d0:f5:2a:62:4a > ff:ff:ff:ff:ff:ff ipv4 192.168.110.1 > 255.255.255.255 udp 67 > 68 dhcp4 ... NAK, reason wrong server-ID
    ```
  * Lấy MAC của bên gửi `RX <MAC>` đối chiếu với bảng ARP / Neighbor trên MikroTik (`GET /rest/ip/neighbor`) để xác định đích danh con AP nào đang phát DHCP lậu.
* **Quy trình Rolling Wi-Fi Cycle chuẩn chống nghẽn AP:**
  * Chia danh sách máy thành từng batch nhỏ (4–5 máy/lô) kèm độ trễ giãn cách (stagger 2–3 giây giữa các batch) qua lệnh:
    ```bash
    adb -s <serial> shell "svc wifi disable && sleep 2 && svc wifi enable"
    ```
  * Chờ 10 giây sau đợt cycle cuối cùng để toàn bộ DHCP client trên điện thoại bắt tay xong trước khi thống kê IP.

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
* **Fleet-Wide Wi-Fi & DNS Health Verification Discipline:**
  * **Android Netd Policy Routing Pitfall:** In modern Android, running raw `ping 8.8.8.8` from unprivileged `adb shell` (UID 2000) may fail if table `main` lacks a default route, even when Wi-Fi is fully operational.
  * **Authoritative Health Signal:** Always parse `dumpsys connectivity` for the `VALIDATED` capability flag under `NetworkAgentInfo [WIFI]` — this proves Android's captive portal probe to Google/HTTP 204 succeeded.
  * **Host PC DNS & Latency Baseline:** Check Windows Event Log Event ID 1014 (`Microsoft-Windows-DNS-Client`) via PowerShell `Get-WinEvent` to distinguish physical cable changeover events from recurring runtime DNS timeouts. Calculate jitter (RFC 3550 / consecutive diff) alongside ping loss across Gateway, Router, and public resolvers (1.1.1.1, 8.8.8.8).

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
3. **The USB Reverse Tethering (ADB Gnirehtet / NetLink USB) Anti-Pattern:**
   * **Bản chất**: Tool cấp mạng qua USB không cần Wi-Fi / không cần Box LAN-OTG (ví dụ `NetLink USB` dựa trên `gnirehtet` của Genymobile) sử dụng Android `VpnService` cục bộ để gom toàn bộ IP packet và đẩy qua socket `adb reverse` trên cáp sạc USB về máy tính.
   * **Lý do TUYỆT ĐỐI KHÔNG DÙNG cho Phone Farm lớn chạy Automation**:
     - **Tràn bộ đệm & Crash ADB Server**: ADB socket sinh ra cho lệnh điều khiển nhẹ và truyền file nhỏ. Bắt `adb.exe` gánh toàn bộ băng thông video TikTok/YouTube của hàng chục máy sẽ làm tràn buffer USB host controller, gây văng `broken pipe` và crash daemon ADB trên Windows.
     - **Hiệu ứng Domino khi lỏng cáp**: Trên các hub USB mật độ cao, chỉ cần 1 cáp sạc chập chờn làm reset USB port controller là toàn bộ các máy đang reverse tethering trên cùng controller bị rớt mạng đồng loạt.
     - **Triệt tiêu Automation của Farm**: Script farm phụ thuộc 100% vào ADB để dump XML giao diện (atx-agent), chụp màn hình và gửi thao tác phím. Băng thông video chiếm dụng đường ADB sẽ khiến các lệnh automation bị nghẽn, lag và timeout liên tục.
     - **Chiếm độc quyền Android VpnService**: Android chỉ cho phép duy nhất một tiến trình nắm giữ `VpnService` tại một thời điểm. Cấp mạng qua USB kiểu này sẽ vô hiệu hóa hoàn toàn khả năng chạy VPN/Proxy app độc lập trên từng thiết bị.


