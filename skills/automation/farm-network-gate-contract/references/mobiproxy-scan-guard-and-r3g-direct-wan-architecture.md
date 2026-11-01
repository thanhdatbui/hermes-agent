# MobiProxy vs OpenWrt R3G: Anti-Scan (Scan Guard) Architecture & Direct WAN Implementation

## 1. Cơ Chế Chống Scan (Scan Guard) Của MobiProxy (`test.taadaa.click`)
- **Bản chất kỹ thuật:** 
  * Scan Guard trên box MobiProxy là cơ chế **Whitelisting ở tầng Tường lửa (Kernel Firewall - iptables / nftables)**, hoàn toàn không phải phần mềm quét hành vi tầng ứng dụng.
  * Khi mở các cổng proxy (`5101..5138`) ra Internet công cộng (Public WAN), hàng ngàn botnet toàn cầu (Shodan, Censys, bot quét proxy tự động) liên tục gửi gói tin probe/scan. Nếu để traffic này chạm vào tiến trình proxy (`3proxy`, `tinyproxy`) hoặc web server PHP-FPM, CPU và RAM của box sẽ bị quá tải, dẫn đến hiện tượng treo cứng hoặc văng mã lỗi `502 Bad Gateway`.
- **Cơ chế hoạt động thực tế (Trích xuất từ Dashboard & API):**
  * **API endpoint:** `api.php?action=proxy.scan_guard.get` / `proxy.scan_guard.save`.
  * **Payload cấu hình:**
    ```json
    {
      "enabled": true,
      "allowed_ips": "116.110.212.30\n1.52.184.202\n",
      "available": true,
      "max_ips": 256
    }
    ```
  * **Hành vi Firewall:**
    1. Thiết lập rule mặc định: `DROP` toàn bộ traffic đến từ Internet nhắm vào dải port proxy `5101..5138`.
    2. Thiết lập exception `ACCEPT`: Chỉ chấp nhận các gói tin có IP nguồn nằm trong danh sách `allowed_ips` (IP WAN của Router MikroTik Đà Nẵng và IP Host Kibe).
    3. Cập nhật tức thì vào kernel iptables (O(1)) mà không cần khởi động lại dịch vụ proxy, không làm rớt kết nối đang chạy.
- **Cơ chế đồng bộ IP động (Dynamic IP Sync):**
  * Do Router MikroTik ở Đà Nẵng dùng đường truyền PPPoE IP động, mỗi khi quay PPPoE đổi IP mới thì IP cũ sẽ bị Scan Guard chặn.
  * Cron job `mobiproxy-scan-guard-auto-ip` (Job ID: `3a92a822ace9`, chạy `*/5 * * * *`) thực thi script `update_mikrotik_scan_guard.py` để tự động phát hiện IP WAN MikroTik mới và gọi API cập nhật whitelist lên box MobiProxy.

---

## 2. So Sánh Mô Hình Mạng: MobiProxy vs Xiaomi R3G

| Tiêu chí | Cụm MobiProxy (`test.taadaa.click`) | Cụm Xiaomi R3G (`tb.taadaa.click`) |
| :--- | :--- | :--- |
| **Bản chất đường truyền** | **Direct WAN (Internet công cộng)** | **Mạng riêng ảo Tailscale (WireGuard) & Direct WAN Whitelist** |
| **Cổng mở ra ngoài** | Mở cổng `5101..5138` ra Public IP WAN | Mở cổng `5141..5158` ra WAN kèm Anti-Scan Whitelist |
| **Nguy cơ bị scan** | Rất cao (bắt buộc phải có Scan Guard) | Đã triệt tiêu qua Whitelist IP Viettel /16 & IP Kibe |
| **Tải phần cứng (CPU/RAM)** | Nhẹ (dùng Hardware NAT của SoC, iptables O(1)) | Siêu nhẹ khi chạy Direct WAN + HWNAT (không ép decode VPN) |
| **Khả năng tương thích S7** | Thông qua Sing-box MikroTik (`192.168.110.2:200xx`) | Thông qua Sing-box MikroTik (`192.168.110.2:202xx`) |

---

## 3. Quy Trình Chuyển Đổi R3G Sang Chế Độ Direct WAN + Scan Guard (Chuẩn MobiProxy)
Nếu muốn giải phóng CPU cho R3G, tận dụng Hardware NAT và chạy Direct WAN mượt mà:

### Bước 1: Khởi động & Cấp phát DDNS Cloudflare / WAN IP
- Cắm nguồn router R3G, đảm bảo kết nối mạng ra Internet ổn định.
- Xác định IP Public của router R3G (ví dụ `117.5.62.126`).

### Bước 2: Cấu hình Tường Lửa Whitelist (Scan Guard) trên OpenWrt
- Tạo rule firewall trên OpenWrt (`uci`):
  ```sh
  uci -q del firewall.allow_proxies_wan
  uci set firewall.allow_proxies_wan=rule
  uci set firewall.allow_proxies_wan.name='Allow-Proxies-WAN-Whitelist'
  uci set firewall.allow_proxies_wan.src='wan'
  uci set firewall.allow_proxies_wan.src_ip='116.110.0.0/16 116.99.0.0/16 171.231.0.0/16 27.79.0.0/16 1.52.0.0/16 1.53.0.0/16'
  uci set firewall.allow_proxies_wan.dest_port='5141-5158'
  uci set firewall.allow_proxies_wan.proto='tcp'
  uci set firewall.allow_proxies_wan.target='ACCEPT'
  uci commit firewall && /etc/init.d/firewall reload
  ```
- **Lưu ý an toàn sống còn (Dead Man's Switch):** Trước khi commit/reload firewall từ xa qua SSH, BẮT BUỘC chạy Dead Man's Switch:
  `nohup sh -c 'sleep 120; cp /root/fw_backup/firewall.safe /etc/config/firewall && /etc/init.d/firewall reload' >/dev/null 2>&1 &`
- CẤM TUYỆT ĐỐI sửa zone mặc định của `tailscale0` kẻo bị khóa cổng SSH.

### Bước 3: Whitelist 4 Dải Mạng Viettel Đà Nẵng & Nhà Kibe
- Trên R3G, cấu hình rule firewall mở rộng chấp nhận toàn bộ 4 dải Subnet `/16` thực tế của ISP Viettel Đà Nẵng + 2 dải mạng Kibe:
  * Viettel Đà Nẵng: `116.110.0.0/16`, `116.99.0.0/16`, `171.231.0.0/16`, `27.79.0.0/16`.
  * Nhà mạng Kibe: `1.52.0.0/16`, `1.53.0.0/16`.
  * Giúp router chống chịu 100% các lần MikroTik quay số đổi IP trong cùng 4 dải mạng Viettel mà không bị gián đoạn trước khi cronjob 5 phút kịp chạy.
  * Cronjob `mobiproxy-scan-guard-auto-ip` (Job ID: `3a92a822ace9`) giữ vai trò chốt chặn đồng bộ tuyệt đối khi ISP cấp dải IP mới hoàn toàn.

---

## 4. Phân Tích An Toàn Bảo Mật Khi Whitelist Dải Mạng Lớn (/16) & Đặc Tính Cron
- **Câu hỏi bảo mật:** Khi whitelist hơn 400.000 IP (4 dải `/16`), người lạ dùng chung mạng Viettel Đà Nẵng có chui vào router phá được không?
  * **HOÀN TOÀN KHÔNG:** Tường lửa R3G khóa chặt 100% cổng quản trị (SSH 22, Web LuCI 80/443) ở phía WAN; chỉ mở quản trị duy nhất trên `tailscale0`.
  * 16 cổng proxy (`5141..5158`) chỉ là cổng trung gian chuyển tiếp lưu lượng web (forward HTTP/SOCKS) ra ngoài IP PPPoE của SIM/line, hoàn toàn không có quyền root, không có shell, không thể truy cập vào mạng LAN nội bộ farm.
  * Kẻ lạ muốn dùng ké proxy thì bắt buộc phải biết chính xác IP WAN động hiện tại của R3G ở Thái Bình (`117.5.x.x`) và đúng port `51xx`.
- **Đặc tính tài nguyên của Cron Auto-Healer / Scan Guard Sync:**
  * Cấu hình bắt buộc: `no_agent: true` (hoàn toàn không gọi LLM/AI, tốn 0 token).
  * Đo đạc thực tế: Truy vấn MikroTik REST API cục bộ chỉ tốn ~14ms.
  * Cơ chế Dedup Cache (`mobiproxy_scan_guard_ips.json`): Nếu IP WAN không đổi, script thoát ngay lập tức (`exit 0`), hoàn toàn im lặng (Zero-drift / Zero-CPU). Chỉ gửi HTTP POST cập nhật khi IP thật sự đổi.

---

## 5. Invariant Gán Proxy Cho Dàn S7 Farm Admin (CẤM CHẾ CHÁO ĐỊNH TUYẾN)
- **S7 không cài Tailscale & không dùng IP WAN động:** 
  * CẤM TUYỆT ĐỐI gán domain Tailscale `tb.taadaa.click` hoặc IP Tailscale `100.x` vào file `PROXYgandienthoai.xlsx` của dàn S7 Admin.
  * CẤM TUYỆT ĐỐI gán IP Public WAN động của R3G (`117.5.x.x`) lên S7 vì vài ngày router đổi IP PPPoE là dàn máy ngắt mạng toàn bộ.
- **Quy chuẩn định tuyến DUY NHẤT đúng chuẩn Farm:**
  * S7 Farm Admin trỏ đúng Gateway LAN nội bộ: **`192.168.110.2:20201..20232`**.
  * Sing-box trên MikroTik nhận cổng `202xx` và tự động định tuyến forward sang R3G Thái Bình (bảo toàn cơ chế Kill Switch và cách ly hạ tầng an toàn tuyệt đối).

---

## 6. Tam Giác Đồng Bộ 3 Tầng Khi Gán/Đổi Proxy (Tri-Sync Invariant)
Khi cập nhật cấu hình proxy cho bất kỳ máy nào trên Farm (đặc biệt khi điều chuyển cụm MikroTik <-> Sing-box R3G), BẮT BUỘC cập nhật đồng thời đủ 3 tầng, cấm làm thiếu:
1. **Tầng Thiết bị (Device ADB Runtime):**
   - Chạy script `set_proxy_farm_admin_adb.py` trên máy Admin qua SSH để nạp `settings put global http_proxy 192.168.110.2:<port>`.
2. **Tầng Bảng tính SSOT (Excel Sync):**
   - Cập nhật file local `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`.
   - Đẩy đè sang máy remote `192.168.110.119` qua script SSH chunking `push_proxy_excel_to_admin.py`.
3. **Tầng Sổ Cái Dữ Liệu Tập Trung (SQLite Master DB):**
   - Cập nhật trực tiếp vào cơ sở dữ liệu `D:/Taadaa/data/farm_master.db`:
     `UPDATE machines SET proxy_endpoint='192.168.110.2:<port>' WHERE machine_id='<N>';`

---

## 7. Quy Trình Kiểm Tra Proxy Fake Chuẩn Trên Máy Thật (Fake IP Verification Protocol)
Khi User yêu cầu *"Kiểm tra proxy fake chuẩn trên các máy chưa"*, Coordinator KHÔNG ĐƯỢC đoán mò hay chỉ đọc file Excel, mà phải kiểm chứng 2 bước thực tế trên thiết bị:
1. **Bước 1 — Kiểm tra Settings Proxy trên máy:**
   - Dùng lệnh trích xuất nhanh $O(1)$: `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Xác nhận dòng `Proxy: 192.168.110.2:<port>` đã nạp đúng cổng quy hoạch (10008..10035 cho MikroTik, 20201..20218 cho Sing-box).
2. **Bước 2 — Đo đạc Egress IP thực tế qua Device-Lock:**
   - Chạy lệnh: `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb.exe -H 192.168.110.119 -s <SERIAL> shell "export http_proxy=http://192.168.110.2:<port>; /data/local/tmp/atx-agent curl --timeout=5s http://api.ipify.org"`
   - Xác nhận HTTP returncode 0 và IP trả về khớp với IP Public của PPPoE line / Sing-box bridge đó.

---
## 8. Bảng Đối Soát Tổng Tài Nguyên Proxy Toàn Farm (160 Phone) & Phân Bổ Dư Thừa
- **Tổng tài nguyên proxy vật lý toàn farm:** 83 Line IP Public độc lập:
  * **Router MikroTik Đà Nẵng:** 35 line PPPoE Viettel Public (`10001`..`10035`).
  * **Box MobiProxy Thái Bình:** 32 port (`5101`..`5138`).
  * **Router Xiaomi R3G Thái Bình:** 16 port (`5141..5148` & `5151..5158`).
- **Nhu cầu 160 phone theo tỷ lệ chuẩn 1:2:** 
  * Cần tối đa $160 / 2 = 80\text{ Line}$ nếu chia đều hoàn hảo.
  * **Thực tế hiện trường Farm chỉ tiêu tốn đúng 79 Line vật lý:**
    - Dàn Admin (80 máy): 32 máy ăn 16 port R3G + 48 máy ăn 24 port MikroTik = **40 line**.
    - Dàn Kibe (80 máy): 64 máy ăn 32 port MobiProxy + 16 máy ăn 7 line MikroTik đầu tiên (`pppoe-out1..7`) = **39 line**.
    - Tổng line đang gánh 160 phone: $40 + 39 = \mathbf{79\text{ Line}}$.
  * **Lý do số học 79 line thay vì 80 line (Phát hiện dồn máy):**
    - 16 máy Kibe MikroTik có 2 nhóm đang bị dồn 3 máy / 1 IP: Line `10006` gánh 3 máy (`M38`, `M71`, `M78`), Line `10007` gánh 3 máy (`M76`, `M79`, `M80`).
    - Quy trình chuẩn hóa 1:2 tuyệt đối: Rút 2 máy `M78` và `M80` tách sang cổng dự phòng `192.168.110.2:10028`. Sau khi tách, cả 160 máy phẳng lì đúng $1:2$ (80 line) và còn dư chuẩn xác 3 line MikroTik (`10029..10031`) + 1 line `khoalee:16002` của ông anh cho.
    - **Invariant an toàn thao tác mạng:** CẤM TUYỆT ĐỐI đổi proxy / tách cổng cho máy S7 khi máy đang trong ca chạy nuôi feed / lướt feed (đang có process active và device-lock). Chỉ thực hiện đổi proxy ngoài khung giờ ca nuôi (sau khi ca kết thúc và nhả lock), kết hợp cập nhật đồng thời SSOT Excel (`PROXYgandienthoai.xlsx`) và SQLite (`farm_master.db`).
    - **Cơ chế Watchdog chuyển mạng khi kết thúc ca (Post-Shift Watchdog Fallback):**
      * Khi viết watchdog canh hết ca nuôi để đổi proxy (như `watchdog_kibe_split_10028.py`), KHÔNG ĐƯỢC chỉ kiểm tra `psutil` chung chung trên toàn bộ process `run_tiktok.py` (vì có thể còn các máy ở cụm/row khác đang lướt kéo dài, dẫn đến bỏ lỡ khung giờ máy mục tiêu đã rảnh).
      * Phải kiểm tra **Target-Specific Lock**: Kiểm tra trực tiếp Device Lock `~/.codex/device-locks/machine_<N>.lock.json` của chính các máy mục tiêu (`M78`, `M80`). Khi các máy mục tiêu đã nhả lock và `mCurrentFocus` trở về màn hình chính Launcher (`com.sec.android.app.launcher`) $\rightarrow$ Kích hoạt đổi proxy ngay lập tức, không để user phải nhắc nhở hay chờ đợi oan.
- **Thực tế Egress IP của 32 máy tách sang Sing-box R3G (20201..20218):**
  * Gán proxy trên Android S7 (`settings put global http_proxy 192.168.110.2:202xx`) chỉ là tầng Inbound vào MikroTik.
  * Tầng Outbound của Sing-box trên MikroTik (`docker/config/config.json`) phải map đúng tag sang R3G Thái Bình mới ra IP Thái Bình (`117.5.152.50`).
  * Khi kiểm tra nghiệm thu *"các máy đã thành IP Thái Bình chưa"*, BẮT BUỘC đo đạc trực tiếp Egress IP từng port (`20201..20218`) ra ngoài (`api.ipify.org`). Không được thấy máy nhận cổng 202xx mà vội kết luận là đã ra IP Thái Bình (thực tế nhiều cổng Sing-box vẫn đang fallback ra line Đà Nẵng nếu bảng route chưa map đủ 16 port).
- **Cân đối dôi dư của chính User:**
  * Tổng 83 line sở hữu - 79 line thực tế đang dùng = **Dư đúng 4 line MikroTik của chính chủ**.
  * Không cần cộng thêm bất kỳ proxy ngoài nào thì bản thân hạ tầng chính chủ đã dư đủ 4 line.
- **Bố trí 4 proxy dự phòng nóng (Hot Standby Pool):**
  * Toàn bộ 4 proxy dôi dư được tập trung cố định thành 4 cổng PPPoE sạch trên MikroTik Đà Nẵng:
    - `192.168.110.2:10028` (`pppoe-out28`)
    - `192.168.110.2:10029` (`pppoe-out29`)
    - `192.168.110.2:10030` (`pppoe-out30`)
    - `192.168.110.2:10031` (`pppoe-out31`)
  * Các cổng này luôn mở sẵn IP Public 24/7, không gán máy nào, đóng vai trò cứu nguy (swap máy khi có line chập chờn) hoặc phục vụ test flow mới.
- **Lưu ý phân biệt số lượng cổng dư để tránh nhầm lẫn:**
  * Dư 2 cổng: Là 2 số ảo trống `20209` và `20210` trên Sing-box do R3G chỉ có 16 port vật lý trong dải `20201..20218`.
  * Dư 4 cổng: Là 4 port PPPoE thật `10028..10031` trên MikroTik Đà Nẵng sau khi chuyển 32 máy Admin sang R3G.
  * Dư 11 cổng (nếu chỉ nhìn máy Admin): Là do 7 cổng `10001..10007` đang phục vụ 16 máy Kibe (`20033..20080`), không phải bị bỏ trống.

---

## 9. Line Proxy Bên Ngoài Ông Anh Cho (`khoalee.duckdns.org`): Phạm Vi & Độ Ổn Định
- **Phạm vi sử dụng (Scope Boundary):**
  * **Phone Farm 160 máy (Kibe + Admin):** **0 máy nào dùng line `khoalee`**. Toàn bộ 160 máy S7 nuôi TikTok chỉ chạy trên 3 hạ tầng chính (MobiProxy Thái Bình, R3G Thái Bình, MikroTik Đà Nẵng) để đảm bảo cách ly và cơ chế Kill Switch.
  * **Hạ tầng AI OmniRoute (`storage.sqlite`):** Line `khoalee` độc quyền phục vụ các provider AI (`antigravity`, `openrouter`, `codex`) trên máy tính. Con `khoalee:16002` hoàn toàn là tài nguyên bonus bên ngoài, tách biệt với 4 proxy dự phòng nóng của Farm.
- **Tình trạng cổng & độ ổn định:**
  * Cổng `16001` (ID 75): **DEAD / TIMEOUT**. CẤM gán cổng này vào bất kỳ provider hay connection nào kẻo gây 503 và kích hoạt providerCooldown.
  * Cổng `16002` (ID 76, auth `5ns08q:AmLmaMJ0`): **LIVE & ỔN ĐỊNH 100%**, latency ~600ms, egress IP Viettel `117.5.188.104`, chịu tải AI mượt mà.

---

## 10. Kiến Trúc Inbound Sing-box Trên MikroTik: `20000 + M` vs Cạm Bẫy Đánh Số Thứ Tự
- **Công thức cổng Inbound chuẩn mực:**
  * Cấu hình container Sing-box trên MikroTik (`docker/config/config.json`) thiết kế mỗi thiết bị Android $M$ một cổng lắng nghe (Inbound listen_port) cố định duy nhất theo công thức:
    $$\mathbf{Port = 20000 + M}$$
  * Ví dụ cụm Admin 32 máy tách R3G:
    - M203 lắng nghe cổng `20203`, M204 cổng `20204` (cả 2 cùng trỏ Outbound sang `5141` của R3G).
    - M208 cổng `20208`, M211 cổng `20211` (cùng trỏ Outbound sang `5142` của R3G).
    - M213 cổng `20213`, M217 cổng `20217` (cùng trỏ Outbound sang `5143` của R3G)...
- **CẠM BẪY TỬ HUYỆT (Sequential Port Numbering Pitfall):**
  * Tuyệt đối CẤM Coordinator / Worker tự ý gom nhóm và gán máy theo số thứ tự dải cổng `20201..20216` trong file Excel hay ADB (ví dụ gán M203, M204 vào port `20201`, M208 vào port `20202`).
  * **Hậu quả chết người:** Cổng `20201` trên Sing-box vốn là cổng inbound của **Máy 201 (thuộc nhóm 48 máy kênh chính MikroTik Đà Nẵng)**. Nếu gán M203 vào `20201`, lưu lượng của M203 sẽ chui vào rule của M201 và đi ra line PPPoE Đà Nẵng, hoàn toàn KHÔNG đi qua R3G Thái Bình và gây trùng chùm IP với các nick chính!

---

## 11. Điểm Mù Của Preflight Check Đơn Lẻ (Single-Device Preflight Blind Spot)
- **Câu hỏi hóc búa của Operator:** *"Khi farm chạy, khâu check proxy có phát hiện ra trường hợp định tuyến nhầm IP như trên không, hay hàng loạt acc chui qua nát hết?"*
- **Cơ chế hoạt động của Preflight hiện tại:**
  * Khâu kiểm tra `preflight.py` (`automation-core`) chạy trên từng máy độc lập ($O(1)$). Nó kiểm tra: Thiết bị có mở được socket và dùng `atx-agent curl` lấy được một Public IPv4 hợp lệ hay không (Fail-Closed nếu timeout hoặc mất mạng).
- **ĐIỂM CHẾT NGUY HIỂM:**
  * Preflight đơn lẻ **CHỈ BIẾT LÀ CÓ MẠNG HAY KHÔNG**, hoàn toàn **KHÔNG BIẾT MÁY ĐANG RA ĐÚNG SUBNET/GEO HAY CHƯA**, và **KHÔNG BIẾT CÓ BỊ TRÙNG IP VỚI MÁY KHÁC TRONG BATCH HAY KHÔNG**.
  * Khi máy bị gán nhầm cổng (như M203 ăn nhầm port 20201 của M201), máy vẫn ra được Internet qua line Đà Nẵng, nên `atx-agent curl` trả về IP thành công $\rightarrow$ **Preflight đơn lẻ vẫn báo PASS 100%**!
  * **Hậu quả thực tế:** Nếu cho farm chạy, hàng loạt acc non và acc chính sẽ cùng lúc lướt TikTok trên chung một IP Đà Nẵng mà hệ thống preflight không hề phát hiện ra, dẫn đến nguy cơ bị thuật toán TikTok phát hiện hành vi farm tài khoản và shadowban hàng loạt.
- **Biện pháp phòng vệ bắt buộc:**
  * Mọi quy trình điều chuyển / phân bổ lại proxy BẮT BUỘC phải chạy **Batch Egress IP Audit**: Quét đồng loạt tất cả các cổng proxy đích để đối soát Egress IP thực tế (xác nhận ra đúng IP Thái Bình `117.5.152.50` và đảm bảo tỷ lệ máy/IP không vượt quá 2:1) trước khi cho phép kích hoạt các ca nuôi TikTok.

---

## 12. Quy Trình Khắc Phục Lỗi Định Tuyến & Công Cụ Thẩm Định Cơ Giới Hóa (`verify_farm_proxy_routing.py`)
- **Quy trình chuẩn phục hồi 32 máy S7 non/yếu về đúng port Sing-box:**
  1. **Tầng Excel & SQLite:** Gán lại toàn bộ 32 máy $m \in \{203, 204, ..., 272\}$ về đúng định dạng cổng nội bộ `192.168.110.2:(20000 + m)` (cập nhật đồng thời `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx` và bảng `machines` trong `D:/Taadaa/data/farm_master.db`).
  2. **Đồng bộ remote:** Đẩy file Excel sang máy Admin-PC (`192.168.110.119`) qua `python D:/Taadaa/tools/push_proxy_excel_to_admin.py`.
  3. **Nạp ADB runtime:** Chạy `python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_admin_adb.py"` để nạp lại `settings put global http_proxy` trên toàn bộ 80 máy Samsung S7.
  4. **Kiểm chứng Canary máy thật:** Chạy `with_device_lock.py` gọi `atx-agent curl http://api.ipify.org` trên máy đại diện (M203, M204, M208, M220, M268) để nghiệm thu IP trả về là đúng Viettel Thái Bình `117.5.152.50`, đồng thời kiểm tra máy kênh chính (M201) giữ nguyên IP Đà Nẵng.
- **Công cụ thẩm định tự động trước ca chạy (`D:/Taadaa/tools/verify_farm_proxy_routing.py`):**
  - Chạy `python D:/Taadaa/tools/verify_farm_proxy_routing.py` (Exit code 0 là PASS, 1 là FAIL).
  - Tự động đối soát chéo: 32 máy non bắt buộc `192.168.110.2:202xx`, 48 máy chính bắt buộc `192.168.110.2:100xx`. Ngăn chặn triệt để mọi lỗi gán đè cổng hoặc dồn máy trước khi khởi động bất kỳ ca nuôi feed nào.

---

## 13. Nguyên Nhân Gốc Rễ Khi Hàng Loạt Cổng R3G Bị Ra Cùng 1 IP (`117.5.152.50`) & Cơ Chế Multi-WAN Binding
- **Hiện tượng nguy hiểm:** Khi kiểm tra 16 cổng Tinyproxy trên R3G (`5141..5158`), toàn bộ các cổng đều thoát ra cùng 1 địa chỉ IP duy nhất `117.5.152.50`, dẫn đến 32 máy S7 bị dồn vào chung 1 IP ngoài Internet.
- **Nguyên nhân kỹ thuật tận gốc:**
  * Router R3G thực tế quay đủ 16 session PPPoE:
    - 8 session trên LAN1 (`pppoe-wan`, `pppoe-wan_sub11..sub17`): Mỗi session nhận 1 IP Public Viettel riêng biệt (`117.5.62.126`, `171.224.72.92`, `116.107.112.230`, `116.104.217.152`...). Kiểm tra trực tiếp bằng `curl --interface pppoe-wan_sub11 http://api.ipify.org` xác nhận ra đúng IP riêng `171.224.72.92`.
    - 8 session trên LAN2 (`pppoe-WAN2`, `pppoe-wan_sub2..sub8`): Nhận IP CGNAT `100.77.98.x` và NAT ra `117.5.152.50`.
  * OpenWrt đã có sẵn 16 routing table riêng (`table 101..108` và `table 200..217`), và `ip rule` quy định rõ `from <IP> lookup <table>`.
  * **ĐIỂM CHẾT:** Trong file cấu hình Tinyproxy (`/etc/tinyproxy/instances/tp_*.conf`), chỉ thị `Bind <IP>` đang bị **comment out (`#Bind ...`)**.
  * Khi `Bind` bị tắt, Tinyproxy không gán source IP khi khởi tạo socket kết nối ra ngoài Internet $\rightarrow$ Kernel Linux tự động đẩy qua Default Route (`pppoe-WAN2`), khiến toàn bộ 16 cổng bị dồn ra chung 1 IP `117.5.152.50`.
- **Nguyên tắc an toàn sống còn khi phát hiện dồn IP:**
  * TUYỆT ĐỐI CẤM CHẠY CA NUÔI khi toàn bộ cổng R3G đang bị dồn 1 IP `117.5.152.50`.
  * Bắt buộc giữ thiết bị ở trạng thái Idle/Launcher cho đến khi cấu hình bind interface / policy routing trên OpenWrt hoàn tất, đảm bảo 8 line PPPoE LAN1 ra đủ 8 IP Public Viettel độc lập trước khi kích hoạt batch.

---

## 14. Đặc Tính Tái Dính CGNAT Của Viettel PPPoE & Invariant Bảo Vệ Tailscale Daemon Trên Router R3G
- **Cơ chế tái bốc CGNAT của Viettel (`100.64.0.0/10` / `100.77.x.x`):**
  * Dù từng có lúc quay ra IP Public sạch, nhưng nếu thuê bao chưa được nhân viên kỹ thuật Viettel **ghim profile Non-CGNAT tĩnh trên cổng OLT trạm**:
  * Mỗi lần modem khởi động lại hoặc interface PPPoE reconnect, BRAS của Viettel sẽ cấp phát IP ngẫu nhiên. Đường truyền có thể bị bốc trúng pool Carrier-Grade NAT (CGNAT).
  * **Giải pháp dứt điểm:**
    1. Reconnect thủ công PPPoE interface đến khi bốc được IP Public sạch (`117.5.x.x`, `171.224.x.x`, `116.107.x.x`...).
    2. Gọi tổng đài Viettel (18008119) cung cấp mã hợp đồng, yêu cầu kỹ thuật: *"Ghim giúp em đường mạng này sang dải IP Public thật (nhả khỏi CGNAT) để lắp camera giám sát"* để khóa chết profile trên trạm OLT.
- **Invariant bảo vệ Tailscale daemon trên router nhúng OpenWrt (MT7621):**
  * Router Xiaomi R3G dùng chip MT7621 và RAM 256MB. Tiến trình `tailscaled` giữ kết nối qua relay (DERP "sin" Singapore).
  * **CẤM hành vi gây nghẽn / drop Tailscale:**
    - CẤM chạy các script shell fork-bomb, vòng lặp restart proxy liên tục không có sleep hoặc killall ồ ạt khiến CPU chạm 100%, làm daemon `tailscaled` bị chậm nhịp keep-alive và rớt session mạng.
    - CẤM chỉnh sửa zone firewall `tailscale0` hoặc can thiệp routing table `main` / `default` làm mất gateway internet của tailscale daemon.
  * **Phương án dự phòng khi R3G bảo trì:**
    - Nếu R3G đang trong quá trình bảo trì routing hoặc rớt kết nối, Coordinator BẮT BUỘC giữ dàn 32 máy S7 ở trạng thái Idle/Lock, hoặc tạm thời chuyển hướng sang các cổng PPPoE MikroTik Đà Nẵng nếu có lịch chạy gấp, tuyệt đối không để farm chạy mù khi router chưa hoàn tất phân luồng.


