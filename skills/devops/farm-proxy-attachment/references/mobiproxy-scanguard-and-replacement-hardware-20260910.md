# MobiProxy v3.0.67 Scan Guard (Kernel Firewall) & Replacement Hardware Analysis

## 1. MobiProxy v3.0.67: Tính Năng "Scan Guard" (Chống Scan Proxy ở Kernel)

### Bản chất thay đổi so với bản cũ
- Trước 3.0.67: Không có tầng lọc firewall kernel riêng cho proxy. Cấu hình whitelist IP chỉ nằm ở application layer (`3proxy / proxy.access_bulk`), khiến gói tin scan TCP từ Internet vẫn chọc thẳng vào daemon, gây quá tải connection tracking và làm crash PHP-FPM (lỗi 502 Bad Gateway) khi bật NAT.
- Từ bản 3.0.67: Seller đã bổ sung tính năng **"Chống scan proxy" (`proxy.scan_guard`)**. Tính năng này ghi danh sách IP được phép trực tiếp vào **Firewall (iptables) ở tầng kernel Linux**, DROP toàn bộ gói tin từ IP ngoài danh sách trước khi chạm vào daemon proxy hoặc PHP.

### Các Endpoint API của Scan Guard
- **Lấy cấu hình hiện tại:**
  `GET /api.php?action=proxy.scan_guard.get`
  Headers: `Cookie: MOBIPROXY_V2=...`
  Response:
  ```json
  {
    "ok": true,
    "data": {
      "enabled": true,
      "allowed_ips": "171.231.195.2\n42.118.214.93\n",
      "available": true,
      "max_ips": 256
    }
  }
  ```
- **Lưu cấu hình Scan Guard:**
  `POST /api.php?action=proxy.scan_guard.save`
  Headers:
  ```http
  Content-Type: application/json
  X-CSRF-Token: <csrf_token_from_meta_or_form>
  X-Requested-With: XMLHttpRequest
  Cookie: MOBIPROXY_V2=...
  ```
  Payload:
  ```json
  {
    "_csrf": "<csrf_token>",
    "enabled": true,
    "allowed_ips": "171.231.195.2\n42.118.214.93\n"
  }
  ```
  *Lưu ý quan trọng:* Bắt buộc phải có header `X-CSRF-Token` và trường `_csrf` trong JSON payload, nếu không server sẽ trả về `HTTP 419 Authentication Timeout / CSRF Mismatch`.

### Ưu điểm vượt trội của `proxy.scan_guard.save`
- **KHÔNG restart 40 tiến trình proxy:** API này chỉ nạp/xóa rule iptables trong kernel.
- **KHÔNG gây OOM / 502:** Khác hoàn toàn với `proxy.access_bulk`, `scan_guard.save` chạy trong 0.2s, RAM tiêu thụ gần như bằng 0, không gây spike RAM của PHP-FPM.
- **Tự động hóa khi MikroTik đổi IP:** Khi IP WAN PPPoE của MikroTik thay đổi, script chỉ cần gọi 1 request `proxy.scan_guard.save` để thêm IP mới vào danh sách whitelist, không cần tắt NAT và không làm gián đoạn các kết nối đang chạy.

---

### 2. Tiêu Chí & So Sánh Thiết Bị Thay Thế Box Proxy Farm (Phân Khúc Rẻ / Cũ)

Khi box hiện tại gặp sự cố hoặc cần tự dựng cụm 32 proxy (4 line mạng x 8 port):
*Quy tắc tư vấn phần cứng (User Preference):* Khách hàng ưu tiên giải pháp tối thiểu chi phí, vừa đủ công suất cho tải thực tế (32 proxy xoay IP), cấm tư vấn các dòng máy đắt tiền (2-3 triệu) cấu hình thừa thãi. Khi tìm kiếm trên sàn TMĐT, phải kiểm tra kỹ phân loại để tránh bẫy giá Barebone (chưa kèm CPU/RAM/SSD).

### A. Phân khúc Siêu rẻ (250k - 350k) — Khuyên dùng nhất:
* **Xiaomi Router 3G v1 (R3G v1 / USB 3.0 / Gigabit):**
  - **Chipset:** MediaTek MT7621A (2 nhân 4 luồng 880MHz, y hệt chip của con box chuyên dụng).
  - **RAM:** **256MB DDR3** (gấp đôi RAM 128MB của box thương mại, chống OOM hoàn toàn).
  - **Cổng mạng:** 1 WAN Gigabit + 2 LAN Gigabit (1000Mbps).
  - **ROM / OS:** Flash sẵn **OpenWrt** (tiếng Anh/tiếng Việt).
  - **Khả năng:** Chạy `mwan3` quay 4 phiên PPPoE trên VLAN qua 1 Switch 5 port Gigabit, cài `3proxy` mở 32 port, cài `WireGuard` nối thẳng về MikroTik farm để đóng sạch toàn bộ port ra ngoài Internet.
  - **Cảnh báo tránh nhầm lẫn:** Tránh mua nhầm bản *Xiaomi Gen 3 (không có G)* giá 200k-250k vì chỉ dùng chip MT7620 và cổng mạng 100Mbps (bị bóp nghẽn). Phải mua đúng bản **R3G v1 (Gigabit)**.

### B. Phân khúc Thin Client x86 Nhỏ gọn không ăng-ten (700k - 950k):
* **HP t420 Thin Client (~800k) / Dell Wyse 3040 (~930k):**
  - Chip Intel x86 4 nhân, RAM 2GB, LAN Gigabit, chạy không quạt (fanless) ăn 4-5W điện.
  - Chạy Debian/Alpine Linux, cấu hình iptables và WireGuard chuẩn mực.

### C. Cảnh báo Bẫy Barebone trên Sàn TMĐT (Shopee/Lazada):
- Các sản phẩm Mini PC văn phòng (Dell Optiplex 3050 Micro, HP 400 G3, J1900 Router PC) thường để giá hiển thị 1.2tr - 1.5tr nhưng thực chất là **Barebone (chỉ có vỏ case + main + nguồn, chưa có CPU/RAM/SSD)**.
- Khi chọn phân loại full RAM/SSD, giá sẽ đội lên 2.5tr - 3.5tr, vượt xa ngân sách chỉ để làm proxy xoay.

---

## 3. Thẩm Định Kỹ Thuật Chuyên Sâu từ Sol (GPT-5.6-Sol-High) cho Xiaomi R3G V1 (2026-09-16)

Đánh giá kiến trúc cho bài toán **Edge Proxy / Tunnel Box cho Farm 80 Samsung S7 (TikTok/Gmail)**:

### A. Đánh giá phần cứng & Throughput thực tế
- **SoC MT7621A (MIPS 1004Kc 2 nhân 4 luồng 880MHz) + 256MB RAM DDR3 + Flash 128MB NAND + Full Gigabit:**
  - Farm 80 máy chạy TikTok/Gmail thực tế chỉ tốn **vài chục Mbps**, bản chất là nhiều kết nối TCP ngắn dồn dập, dung lượng băng thông không cao.
  - MT7621A xử lý rất tốt nếu làm **tunnel / forwarding nhẹ**.
  - **Throughput thực tế đo kiểm:**
    * NAT thuần: 700 - 900 Mbps.
    * WireGuard kernel: 80 - 200 Mbps (CPU chiếm 40% - 60%).
    * Shadowsocks AEAD: 50 - 150 Mbps.
    * TLS proxy / Xray userspace: 20 - 80 Mbps (do handshake và xử lý userspace).

### B. Điểm nghẽn sống còn: RAM 256MB & Nguy cơ OOM
- **CẤM:** Không biến R3G thành "server proxy đa năng" chạy Go runtime nặng (Xray, Sing-box full module, Docker, NodeJS, Web Dashboard, Adguard Home, verbose logging) vì sẽ OOM crash ngay.
- **Bảng footprint RAM các dịch vụ:**
  | Dịch vụ | RAM tiêu thụ | Đánh giá kiến trúc |
  | :--- | :---: | :--- |
  | **WireGuard (kernel module)** | **5 - 15MB** | **Hạng 1 (★★★★★): Tối ưu nhất cho edge tunnel** |
  | **redsocks** | **< 5MB** | **Hạng 2 (★★★★☆): Rất nhẹ để redirect traffic** |
  | **shadowsocks-libev** | **5 - 15MB** | **Hạng 3 (★★★★☆): Nhẹ, ổn định** |
  | **3proxy** | **< 5MB** | **Hạng 4 (★★★☆☆): Ổn cho SOCKS/HTTP nội bộ** |
  | **sing-box** | 40 - 100MB | Hạng 5 (★★★☆☆): Chỉ dùng profile tối giản, tắt GUI/log |
  | **xray-core** | 50 - 150MB | Tránh dùng: Nặng RAM, phức tạp, dễ OOM trên 256MB |

### C. Quy tắc triển khai & Tối ưu phần cứng
1. **Tắt hoàn toàn WiFi (`radio0`, `radio1`):** Biến R3G thành một network appliance thuần túy — giảm ngắt interrupt CPU, giảm daemon ngầm, giảm bề mặt tấn công và hạ nhiệt độ.
2. **Nhiệt độ & Nguồn:** MT7621A chạy lâu nhiệt độ khoảng 60–75°C, nên đặt nơi thông thoáng (hoặc tháo nắp tản nhiệt) và dùng nguồn 12V chuẩn đủ dòng.
3. **USB 3.0 Noise:** USB 3.0 phát nhiễu dải 2.4GHz nếu cắm Dcom/dongle (nhưng khi đã tắt WiFi và đi dây LAN thì không ảnh hưởng).

### D. Kiến trúc mạng chuẩn triệt tiêu Bot Scan
- **Mô hình đúng:**
  ```text
  Internet ──► MikroTik (192.168.110.2) ──► Xiaomi R3G V1 ──► WireGuard Tunnel ──► VPS Proxy Exit
  ```
- **Firewall WAN:** DROP toàn bộ inbound từ WAN. Tuyệt đối không mở port proxy ra ngoài Internet như box thương mại cũ.
- **Điểm thẩm định của Sol:** **8 / 10 điểm** trong tầm giá 328.000đ đã nạp sẵn OpenWrt.
