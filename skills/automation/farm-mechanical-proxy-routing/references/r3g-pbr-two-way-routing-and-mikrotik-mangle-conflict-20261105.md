# R3G OpenWrt PBR Two-Way Routing & Cross-Cluster MikroTik Mangle Conflict Triage (2026-11-05)

## 1. Bản chất sự cố lệch luồng hai chiều trên Xiaomi R3G (2 Line 16 PPPoE)
- **Triệu chứng:** Khi MikroTik Đà Nẵng DNAT sang các cổng `5141..5158` của R3G Thái Bình, kết nối bị `Timed out` hoặc `502 Bad Gateway`, mặc dù bản thân R3G hoàn toàn không dùng password và 16 line PPPoE đều `ONLINE 16/16`.
- **Nguyên nhân gốc rễ (Asymmetric Routing trên OpenWrt):**
  - Tên miền `tb.taadaa.click` chỉ trỏ về IP của 1 line PPPoE duy nhất (ví dụ `wan_sub11` hoặc `pppoe-wan`).
  - Gói tin DNAT từ MikroTik đi vào qua cổng WAN chính, nhưng tiến trình Tinyproxy tương ứng lại bind vào line PPPoE khác (`WAN2` hoặc `wan_sub2..8`).
  - Khi Tinyproxy trả lời (Reply Packet), bảng routing của OpenWrt đẩy câu trả lời đi ra bằng line PPPoE khác. Trạm BRAS của ISP Viettel kích hoạt cơ chế `uRPF` (Unicast Reverse Path Forwarding) tự động DROP ngay gói tin vì IP nguồn không khớp với interface đi ra!
- **Giải pháp xử lý dứt điểm trên R3G OpenWrt:**
  1. Mở tường lửa `zone_wan_input` cho phép IP WAN chính của MikroTik:
     ```bash
     uci add firewall rule
     uci set firewall.@rule[-1].name='Allow-Proxies-MikroTik-WAN1'
     uci set firewall.@rule[-1].src='wan'
     uci set firewall.@rule[-1].proto='tcp'
     uci set firewall.@rule[-1].dest_port='5141 5142 5143 5144 5145 5146 5147 5148 5151 5152 5153 5154 5155 5156 5157 5158'
     uci set firewall.@rule[-1].src_ip='171.231.180.189'
     uci set firewall.@rule[-1].target='ACCEPT'
     uci commit firewall && /etc/init.d/firewall reload
     ```
  2. Nạp Policy-Based Routing (PBR) ép đường trả lời về đúng MikroTik:
     ```bash
     # Tạo bảng route 200 trỏ default qua pppoe-wan
     ip route replace default dev pppoe-wan table 200
     # Ép toàn bộ gói tin gửi về IP MikroTik đi qua bảng 200
     ip rule add to 171.231.180.189 table 200 priority 5000
     ```
  3. Khởi động lại đủ 16 tiến trình Tinyproxy:
     ```bash
     sh /root/generate_all_proxies.sh
     ```
  - **Kết quả nghiệm thu:** Toàn bộ 16 cổng `5141..5158` trên R3G đồng loạt phản hồi `LIVE` trực tiếp từ Đà Nẵng với tốc độ wire-speed `0.55s – 0.65s`!

---

## 2. Bẫy xung đột Mangle liên cụm trên MikroTik (Cross-Cluster WAN Mangle Conflict)
- **Hiện tượng:** Sau khi R3G thông suốt DNAT, Kibe PC test trực tiếp cổng 5141 ra `LIVE 117.5.152.118 (0.6s)`. Nhưng khi điện thoại Samsung S7 (Máy 203 - dàn Admin non) mở trình duyệt qua cổng MikroTik `20203` thì bị mất mạng, hiện dấu chấm than (!) trên biểu tượng Wi-Fi (`ERR_CONNECTION_REFUSED` / `everValidated: false`).
- **Phân tích nguyên nhân:**
  - Điện thoại Máy 203 mang IP LAN `192.168.10.221`.
  - Trong bảng `/ip firewall mangle` của MikroTik, quy hoạch cũ của dàn Admin có rule:
    `FARM_ADMIN_MAY_203_192.168.10.221_TO_WAN8` $\rightarrow$ Ép toàn bộ gói tin của Máy 203 phải đi ra bằng cổng **`pppoe-out8`**.
  - Trong khi đó, con R3G ở Thái Bình chỉ mở Firewall Whitelist và PBR trả lời về cổng **`pppoe-out1` (IP `171.231.180.189`)**.
  - **Hậu quả:** Gói tin từ Máy 203 ra bằng `pppoe-out8`, nhưng câu trả lời lại quay về `pppoe-out1`. Hai cổng mạng Viettel khác nhau làm kết nối bị gãy đôi ngay tại RouterOS!
- **Bài học điều phối:** Khi nạp rule Kernel DNAT trỏ sang router/proxy ngoại tỉnh, BẮT BUỘC phải đối soát bảng `/ip firewall mangle` để đảm bảo gói tin đi ra ngoài bằng đúng cổng WAN mà router đối tác đã whitelist, hoặc dùng Hairpin/Masquerade SNAT thích hợp.
