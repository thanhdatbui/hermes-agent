# SSOT Proxy Identity Presentation, Anti-Scan Mechanics, and Hot Standby Invariants

## 1. Problem & User Correction
- **Confusion Encountered:** Displaying the intermediate bridge/hop (e.g. `192.168.110.2:202xx` or Sing-box internal listener) in SSOT records (`PROXYgandienthoai.xlsx`), master databases (`farm_master.db`), and Web Ledger UI (`kibe:1905`), HOẶC tự ý đem IP WAN động của router (`117.5.x.x`) đi gán trực tiếp cho điện thoại Android.
- **User Correction (Quy chuẩn dứt khoát):** 
  * *"Tao muốn làm y như bên mobi proxy ấy? Là định tuyến đầy đủ, sao mày cứ chế cháo v??? R tại sao lại qua direct wan 117.xxx (cái ip 117.5.62.126 là ip của gì thế) ?"*
  * Điện thoại Android trong farm **BẮT BUỘC** trỏ qua Gateway LAN nội bộ `192.168.110.2:<port>` (Sing-box làm cầu trung chuyển ra ngoài). CẤM TUYỆT ĐỐI gán IP WAN động ngoài Internet hay domain Tailscale vào điện thoại.

## 2. Distinction: SSOT Identity vs. Mechanical L3/L4 Hop
1. **SSOT Identity (User-facing & Multi-app integration):**
   - Represents the true exit IP origin (e.g. `tb.taadaa.click:51xx` for Thai Binh Viettel line; `test.taadaa.click:51xx` for MobiProxy).
   - Used by GPM browser profiles when warming Hotmail/Gmail accounts matching S7 phones: GPM profiles run on PC must know the true proxy endpoint to bind the browser profile to the exact same exit IP / Geo-location as the phone (preventing fraud checkpoints / 48h locks from Microsoft/OpenAI due to location mismatch).
   - Displayed in `farm_master.db.machines.proxy_endpoint`, `PROXYgandienthoai.xlsx`, and `http://kibe:1905`.

2. **Mechanical Routing Hop (Device-level execution):**
   - Android S7 phones lack built-in proxy auth support and risk leaking farm IP if remote connections drop.
   - Therefore, devices connect via local Wi-Fi to MikroTik Sing-box container (`192.168.110.2:200xx` cho MobiProxy, `192.168.110.2:202xx` cho R3G) hoặc direct LAN listener `192.168.110.2:100xx`.
   - Sing-box enforces fail-closed kill-switch and forwards via Windows PortProxy / Tailscale / Direct WAN to the destination.
   - The runner script (`set_proxy_farm_admin_adb.py` or watchdog) translates the SSOT target (`tb.taadaa.click:51xx`) into the local forwarder port (`192.168.110.2:202xx`) when issuing `settings put global http_proxy`.

3. **CẤM GÁN TAILSCALE ENDPOINT / DIRECT WAN IP VÀO EXCEL GÁN ĐIỆN THOẠI (Hard Invariant):**
   - CẤM TUYỆT ĐỐI gán domain/IP phân giải qua mạng Tailscale (như `tb.taadaa.click` -> `100.115.94.49`) hoặc IP WAN động (`117.5.x.x`) trực tiếp vào file cấu hình `PROXYgandienthoai.xlsx` của dàn điện thoại.
   - **Cơ chế gây lỗi dây chuyền:**
     * File `set_proxy_farm_admin_adb.py` trích xuất port từ proxy string và gán thẳng `192.168.110.2:<port>` vào Android `settings put global http_proxy`.
     * Nếu trong Excel để `tb.taadaa.click:5141`, script sẽ gán `192.168.110.2:5141` lên S7. Cổng 5141 không hề lắng nghe trên MikroTik LAN mà nằm trên PC Admin / R3G -> kết nối đứt.
     * Nếu gán IP WAN động `117.5.x.x`: Vài ngày router quay số PPPoE đổi IP mới là toàn bộ dàn máy mất kết nối lập tức.
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
   - Hoạt động song song 2 cơ chế:
     * Quản trị nội bộ kín qua Tailscale (`tailscale0`).
     * Direct WAN có Whitelist iptables (`Allow-Proxies-WAN-Whitelist`) chỉ chấp nhận kết nối từ MikroTik Đà Nẵng và PC Kibe.
   - S7 phones access this via MikroTik Sing-box (`192.168.110.2:202xx`) -> Outbound sang R3G.
   - Vừa nhẹ tải Hardware NAT, vừa bảo vệ chống scan sập router.

## 5. MikroTik Hot Standby Pool & Fleet Balance Accounting
- **Phân bổ tài nguyên 35 Line PPPoE MikroTik trên toàn Farm:**
  * **Tổng cộng 35 Line Public IP** (`pppoe-out1` đến `pppoe-out35`).
  * **Dàn Kibe (Máy 1 - 80):** 64 máy dùng MobiProxy (`5101..5138`), 16 máy (`M33..M38` và `M71..M80`) ăn **7 IP đầu tiên (`10001..10007`)** qua Sing-box `20033..20080`.
  * **Dàn Admin (Máy 201 - 280):** 32 máy non/yếu chuyển sang 16 port R3G Thái Bình (`20201..20218`), 48 máy kênh chính ăn **24 IP (`10008..10027` & `10032..10035`)** theo chuẩn vàng 1 IP : 2 máy.
  * **Tài nguyên dôi dư toàn Farm:** 35 - 7 (Kibe) - 24 (Admin) = **Đúng chính xác 4 IP MikroTik (`10028..10031`)**.
- **Giải mã nhầm lẫn "Dư 2 cổng" vs "Dư 4 cổng":**
  * **Dư 2 cổng:** Là của cụm **Sing-box R3G Thái Bình** (`20201..20218` có 18 port danh định nhưng R3G chỉ có 16 port thật `5141..5148` & `5151..5158`, dẫn đến **khuyết/dư 2 port đệm ở giữa là `20209` và `20210`**).
  * **Dư 4 cổng:** Là **4 port Public IP thật của MikroTik (`10028..10031`)** làm Hot Standby.
- **Quy tắc Hot Standby Invariant:**
  * CẤM gán cố định máy nuôi dài hạn vào 4 port `10028..10031` hoặc 2 port ảo `20209..20210`.
  * Khi đối soát danh sách cổng thừa, phải kiểm tra đồng thời cả 2 cụm (Kibe + Admin) trên `farm_master.db` để tránh báo cáo nhầm 7 port đầu của Kibe (`10001..10007`) là "cổng dư vô thừa nhận".

## 6. Router Hardware Bottlenecks: Hardware NAT vs. Tailscale Software Crypto (MT7621 Ceiling)
- **Root Cause of Performance Discrepancy (MobiProxy vs. R3G):**
  - Both devices run the **MediaTek MT7621** (MIPS 880MHz, 2 cores / 4 threads), but MobiProxy has only 128MB RAM while R3G has 256MB RAM and 128MB NAND Flash.
  - **MobiProxy Direct TCP:** Utilizes MT7621 **Hardware Flow Offload (Hardware NAT)**. Forwarding packet headers bypasses CPU, keeping CPU usage at 5–10% even with 32 ports (64 devices).
  - **R3G Tailscale Tunnel:** MT7621 lacks hardware cryptographic acceleration (ChaCha20-Poly1305). WireGuard encryption runs in software on MIPS CPU cores, capping throughput at ~120–150 Mbps. At 16 ports (32 devices), CPU is 30–35%; at 32–40 ports, CPU reaches 70–85%; beyond 40 ports, video buffering occurs.
- **Direct WAN Routing Equivalence:**
  - If R3G adopts Direct WAN (DDNS Cloudflare + iptables IP whitelist), the routing path becomes **100% structurally identical** to MobiProxy:
    * Samsung S7 -> `192.168.110.2:202xx` (Sing-box) -> Outbound `tb.taadaa.click:51xx` (Direct WAN) -> R3G `iptables` ACCEPT MikroTik IP -> Tinyproxy -> Viettel PPPoE -> Internet.
  - **Key Architectural Benefit:** Eliminates the Windows PortProxy hop on PC Admin (`192.168.110.119`), decouples proxy uptime from PC Admin reboots, và phục hồi năng lực Hardware NAT tối đa.
