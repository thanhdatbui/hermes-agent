# Farm Multi-Site Proxy Offloading & 1:2 Device Ratio Rebalancing

## 1. Context & Operational Constraints
In large Android phone farms (e.g. Farm Admin 80 devices: M201–M280), proxy infrastructure bottlenecks often force undesirable ratios such as **3 machines per 1 IP/proxy**.
- **Impact of 3:1 Ratio:** High risk of concurrent registration rate-limiting, extended cooldown windows between feed sessions, and account correlation flags by platform risk engines (TikTok, Google).
- **Golden Target Ratio:** **1 proxy : 2 devices (1:2)** maximum.

## 2. Cross-Site Offloading: Remote Node Dispatch
When a remote multi-WAN node (e.g., Xiaomi R3G at Thái Bình with 16 dedicated FTTH PPPoE lines) is added to the fleet:
1. **Capacity Sizing & Port Planning:**
   - **Contiguous Non-Conflicting Port Allocation:** MobiProxy currently occupies `5101..5138` (Lan 1: 5101-5108, Lan 2: 5111-5118, Lan 3: 5121-5128, Lan 4: 5131-5138). The canonical contiguous dải port for the new 16-proxy node starts at **`5141`**:
     - Line 1 (cổng giữa `tamnhb1`): `5141..5148` (8 proxy)
     - Line 0 (cổng ngoài `tamnhb0`): `5151..5158` (8 proxy)
   - Sizing at 1:2 ratio: Exactly $16 \times 2 = 32$ machines can be offloaded.
2. **DNS & Cloudflare Governance:**
   - **Cloudflare Account Precedence:** Always verify and use the root domain owner account `thanhdatbui1995@gmail.com` (NEVER use `19951`).
   - **DNS-Only (Gray Cloud) Invariant:** For farm proxy subdomains (e.g., `tb.taadaa.click` -> `100.115.94.49`), record type MUST be `A`, Proxy Status MUST be **DNS Only** (`reserved IP / gray cloud`). Cloudflare Orange Cloud (CDN proxy) will strip/block non-standard HTTP proxy ports (`5141..5158`).
3. **Account Selection Strategy (Anti-Geo-Shock):**
   - **DO NOT Offload Mature / Upload Channels:** Kênh chính, nick già đã có lịch sử gắn chặt với IP local (ví dụ Đà Nẵng) và trạm BRAS miền Trung. Đảo IP đột ngột sang tỉnh khác (Thái Bình) dễ kích hoạt checkpoint OTP, captcha trượt, hoặc bóp reach.
   - **PRIORITIZE Offloading Young / Incubating Channels:**
     - Lọc các máy đang ở giai đoạn Reg hoặc nuôi phôi (Tik1 - Tik3, nhiều acc 0 video).
     - Rút đúng 1 máy yếu nhất từ mỗi nhóm 3 máy/IP -> Đưa 24 nhóm 3 máy/IP về tỷ lệ chuẩn 1:2.
     - Lấy tiếp các máy non/yếu từ các nhóm cuối để lấp đầy đủ 32 slots trên node từ xa.
4. **Execution Timing & Automated Watchdog Deployment:**
   - **Post-Evening Shift Execution:** Thực hiện gán proxy ngay sau ca tối (23:30 - 00:00).
   - **Resting Window (6-12h):** Cần khoảng nghỉ đêm (cooldown) để thiết bị ngắt kết nối session cũ trước khi mở app trên IP mới vào sáng hôm sau.
   - **Automated Deployment Watchdog Contract:** Triển khai qua watchdog tự động (`watchdog_r3g_admin_switch.py`) tích hợp:
     - Pre-condition: `now.hour >= 23 or now.hour < 3` AND 0 active device/batch locks.
     - Idempotency guard: Kiểm tra cờ `.done` trước khi hành động, ghi cờ sau khi hoàn tất.
     - Atomic update: Cập nhật SSOT `PROXYgandienthoai.xlsx` -> Bắn ADB `settings put global http_proxy` -> Toggle Airplane Mode -> Reset về HOME.

## 3. Remote Egress Routing Architecture: Mandatory Sing-Box Inbound (Anti-Leak)
- **STRICT PROHIBITION (Never Point Phones to Remote Domain):**
  - **The Pitfall:** Gán HTTP proxy trên Android S7 trực tiếp ra remote domain (`tb.taadaa.click:<port>`).
  - **The Risk:** Android 7/8 Wi-Fi proxy stack thiếu cơ chế kill-switch phần cứng. Khi proxy rớt kết nối hoặc domain bị lag, Cronet/gRPC của TikTok tự động bypass HTTP proxy và bắn traffic thẳng qua IP Wi-Fi nhà mạng gốc $\rightarrow$ Kích hoạt cờ correlation, checkpoint hoặc shadowban.
- **Mandatory MikroTik Sing-Box Inbound:**
  - Toàn bộ máy S7 trong Farm BẮT BUỘC chỉ trỏ vào IP gateway nội bộ:
    - Kibe: `192.168.110.2:20001..20080`
    - Admin: `192.168.110.2:20201..20280`
  - Container Sing-Box trên MikroTik (`172.17.0.2`) nhận luồng, đóng vai trò **Fail-Closed Mechanical Kill Switch** (nếu proxy upstream sập, Sing-Box reset TCP ngay lập tức, 100% không leak IP gốc).
  - Sing-Box chuyển tiếp qua Windows PortProxy trên PC Admin/Kibe (`192.168.110.119:51xx`), đi xuyên qua tunnel Tailscale tới router R3G Thái Bình (`100.115.94.49:51xx`).

## 4. Full-Spectrum Multi-Tier Farm Data Standardization Protocol
Khi thực hiện chuyển đổi hoặc gán lại dải proxy cho dàn máy, BẮT BUỘC chuẩn hóa đồng nhất trên cả 3 tầng dữ liệu (không được bỏ sót tầng nào):
1. **Tầng 1: Excel Workbooks SSOT (`PROXYgandienthoai.xlsx`):**
   - Cập nhật file cục bộ trên Controller (`D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx`).
   - Cập nhật trực tiếp lên host đích (`admin-farm`) bằng script nạp Base64 qua SSH/PowerShell để tránh độ trễ đồng bộ OneDrive.
2. **Tầng 2: SQLite Master Database (`farm_master.db`):**
   - Cập nhật trường `proxy_endpoint` trong bảng `machines` của `D:\Taadaa\data\farm_master.db`:
     ```sql
     UPDATE machines SET proxy_endpoint = '192.168.110.2:202xx' WHERE machine_id = '<ID>';
     ```
   - Đảm bảo Web Dashboard Ledger (`kibe:1905`) và các runner đọc qua DAL `farm_db.get_machine_info(m)['proxy_endpoint']` phản ánh đúng thông số mới tức thì.
3. **Tầng 3: Thiết Bị Phần Cứng Thật (ADB Hardware State):**
   - Gọi script `set_proxy_farm_admin_adb.py --machines <list>` qua ADB.
   - Kiểm chứng thiết bị online nhận đúng `settings put global http_proxy 192.168.110.2:202xx` và tắt captive portal.
