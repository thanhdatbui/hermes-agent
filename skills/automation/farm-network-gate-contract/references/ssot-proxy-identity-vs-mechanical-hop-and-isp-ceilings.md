# SSOT Proxy Identity Presentation, Anti-Scan Mechanics, and Hot Standby Invariants

## 1. Problem & User Correction
- **Confusion Encountered:** Displaying the intermediate bridge/hop (e.g. `192.168.110.2:202xx` or Sing-box internal listener) in SSOT records (`PROXYgandienthoai.xlsx`), master databases (`farm_master.db`), and Web Ledger UI (`kibe:1905`).
- **User Correction:** In SSOT databases, spreadsheets, and Web UI dashboards, the proxy column MUST ALWAYS display the **canonical destination identity** of the proxy assigned to that machine (e.g., `tb.taadaa.click:5141`, `test.taadaa.click:5101:mobi1:...`). It must NOT show raw internal hops or sing-box translation ports.

## 2. Distinction: SSOT Identity vs. Mechanical L3/L4 Hop
1. **SSOT Identity (User-facing & Multi-app integration):**
   - Represents the true exit IP origin (e.g. `tb.taadaa.click:51xx` for Thai Binh Viettel line; `test.taadaa.click:51xx` for MobiProxy).
   - Used by GPM browser profiles when warming Hotmail/Gmail accounts matching S7 phones: GPM profiles run on PC must know the true proxy endpoint to bind the browser profile to the exact same exit IP / Geo-location as the phone (preventing fraud checkpoints / 48h locks from Microsoft/OpenAI due to location mismatch).
   - Displayed in `farm_master.db.machines.proxy_endpoint`, `PROXYgandienthoai.xlsx`, and `http://kibe:1905`.

2. **Mechanical Routing Hop (Device-level execution):**
   - Android S7 phones lack built-in proxy auth support and risk leaking farm IP if remote connections drop.
   - Therefore, devices connect via local Wi-Fi to MikroTik Sing-box container (`192.168.110.2:202xx`) or direct LAN listener.
   - Sing-box enforces fail-closed kill-switch and forwards via Windows PortProxy / Tailscale to the destination.
   - The runner script (`set_proxy_farm_admin_adb.py` or watchdog) translates the SSOT target (`tb.taadaa.click:51xx`) into the local forwarder port (`192.168.110.2:202xx`) when issuing `settings put global http_proxy`.

3. **CẤM GÁN TAILSCALE ENDPOINT VÀO EXCEL GÁN ĐIỆN THOẠI (Hard Invariant):**
   - CẤM TUYỆT ĐỐI gán domain/IP phân giải qua mạng Tailscale (như `tb.taadaa.click` -> `100.115.94.49`) trực tiếp vào file cấu hình `PROXYgandienthoai.xlsx` của dàn điện thoại khi router chưa mở Direct WAN thật.
   - **Cơ chế gây lỗi dây chuyền:**
     * File `set_proxy_farm_admin_adb.py` trích xuất port từ proxy string và gán thẳng `192.168.110.2:<port>` vào Android `settings put global http_proxy`.
     * Nếu trong Excel để `tb.taadaa.click:5141`, script sẽ gán `192.168.110.2:5141` lên S7. Cổng 5141 không hề lắng nghe trên MikroTik LAN mà nằm trên PC Admin / R3G -> kết nối đứt.
     * Hoặc nếu Android kết nối trực tiếp vào IP Tailscale, kernel Android không có route tới dải `100.64.0.0/10` -> `network is unreachable`.
     * Khi proxy chết, cơ chế Captive Portal Check ngầm của Android (Generate 204) fail -> Android đánh dấu Wi-Fi không có Internet và tự ngắt kết nối (`Wi-Fi not connected`), kéo theo gãy hàng loạt ca nuôi.
   - **Quy trình cứu hộ khẩn cấp O(1) khi R3G / Tailscale gặp sự cố:**
     1. Khôi phục `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` về dải cổng nội bộ MikroTik (`10008..10035`).
     2. Đồng bộ file sang máy PC Admin (`192.168.110.119`).
     3. Chạy `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_admin_adb.py` qua ADB Remote để re-apply toàn bộ 80 máy về cổng `192.168.110.2:100xx`.
     4. Kiểm chứng preflight bằng `with_device_lock.py` và `/data/local/tmp/atx-agent curl` trên 2-3 máy đại diện. Không cần đụng vào router từ xa hay làm phiền bên ngoài.

## 3. ISP Carrier Concurrent Session Ceiling (Viettel FTTH)
- **Hard ISP Limit on PPPoE Concurrent Sessions:**
  - Standard FTTH Viettel line caps public IP PPPoE sessions (e.g. exactly 35 concurrent sessions on Da Nang line, 8 sessions per line on Thai Binh R3G).
  - Attempting to dial beyond the ISP ceiling (e.g. session #36 on Da Nang MikroTik) triggers CGNAT fallback (e.g. `172.22.x.x` private subnet) where packets are dropped or fail internet routing.
  - **Rule:** Never keep interfaces enabled beyond the known verified public pool limit. Extra declared interfaces must remain `disabled=true`.

## 4. Anti-Scan Mechanics: Public WAN Whitelist (MobiProxy) vs. Stealth Zero-Trust (R3G Tailscale)
1. **MobiProxy (`test.taadaa.click:5101..5138`):**
   - Exposes proxy ports directly to Public WAN Internet.
   - Requires kernel-level **Scan Guard** (`iptables` whitelist) to prevent international botnets (Shodan, Censys) from scanning and crashing the box (502 Bad Gateway).
   - Requires dynamic auto-updating (`update_mikrotik_scan_guard.py`) whenever MikroTik rotates its WAN IP.
2. **Xiaomi R3G (`tb.taadaa.click:5141..5158` via Tailscale `100.115.94.49`):**
   - Completely blocks all inbound traffic on Public WAN (`zone_wan_input` default REJECT/DROP). Ports are totally invisible to the Internet.
   - Traffic is only accepted over encrypted Tailscale VPN (`tailscale0`).
   - S7 phones access this via MikroTik Sing-box -> PC Admin PortProxy (`192.168.110.119:51xx`) -> Tailscale -> R3G.
   - Inherently immune to port scanning without requiring IP whitelist maintenance.

## 5. MikroTik Hot Standby Pool (4 Spare Public IPs)
- **Ports `192.168.110.2:10028..10031`:**
  - MikroTik maintains 4 idle, live public IP PPPoE lines (`pppoe-out28..31`) as a dedicated hot-standby pool.
  - **Use Cases:**
    1. Instant hot-swap when an active PPPoE line experiences jitter, flap, or requires rapid IP rotation.
    2. Ad-hoc allocation for standalone GPM browser profiles (Hotmail/Gmail warming) or fresh tool automation testing without interfering with farm machines.
  - **Invariant:** Prohibit binding permanent farm machines to these 4 ports unless an explicit farm expansion is sanctioned by the operator.

## 6. Router Hardware Bottlenecks: Hardware NAT vs. Tailscale Software Crypto (MT7621 Ceiling)
- **Root Cause of Performance Discrepancy (MobiProxy vs. R3G):**
  - Both devices run the **MediaTek MT7621** (MIPS 880MHz, 2 cores / 4 threads), but MobiProxy has only 128MB RAM while R3G has 256MB RAM and 128MB NAND Flash.
  - **MobiProxy Direct TCP:** Utilizes MT7621 **Hardware Flow Offload (Hardware NAT)**. Forwarding packet headers bypasses CPU, keeping CPU usage at 5–10% even with 32 ports (64 devices).
  - **R3G Tailscale Tunnel:** MT7621 lacks hardware cryptographic acceleration (ChaCha20-Poly1305). WireGuard encryption runs in software on MIPS CPU cores, capping throughput at ~120–150 Mbps. At 16 ports (32 devices), CPU is 30–35%; at 32–40 ports, CPU reaches 70–85%; beyond 40 ports, video buffering occurs.
- **Direct WAN Routing Equivalence:**
  - If R3G adopts Direct WAN (DDNS Cloudflare + iptables IP whitelist), the routing path becomes **100% structurally identical** to MobiProxy:
    * Samsung S7 -> `192.168.110.2:202xx` (Sing-box) -> Outbound `tb.taadaa.click:51xx` (Direct WAN) -> R3G `iptables` ACCEPT MikroTik IP -> Tinyproxy -> Viettel PPPoE -> Internet.
  - **Key Architectural Benefit:** Eliminates the Windows PortProxy hop on PC Admin (`192.168.110.119`), decouples proxy uptime from PC Admin reboots, and restores full Hardware NAT throughput (enabling 48–64 ports on R3G).

## 7. Expanding Physical WANs via Managed Switch (802.1Q VLAN Trunking)
- To exceed the 3 physical ports on R3G (1 WAN, 2 LAN):
  1. Deploy an inexpensive 802.1Q Managed Switch (TP-Link/Tenda).
  2. Map each distinct physical Viettel FTTH fiber line into a separate VLAN (e.g. VLAN 10, 20, 30).
  3. Trunk all VLANs over a single Gigabit Ethernet cable to R3G (Router-on-a-Stick).
  4. Create MACVLAN interfaces on each VLAN sub-interface to dial 8 PPPoE sessions per account.
