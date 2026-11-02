# OpenWrt Multi-WAN Proxy Egress Binding, Tailscale DNS Override & CGNAT Fallacy

## 1. Bản Chất Kỹ Thuật: Ảo Giác "CGNAT 100.77.x.x Bị Khóa" vs Egress NAT Thật Sự
- **Hiện tượng đánh lừa:** Khi lệnh `ip addr` hoặc LuCI ubus dump trên interface PPPoE (ví dụ `pppoe-WAN2`) hiển thị dải IP nội bộ `100.77.x.x` (RFC 6598), Coordinator thường vội vã kết luận "nhà mạng khóa CGNAT, phải gọi tổng đài nhả NAT".
- **Sự thật khách quan:** Trên hạ tầng FTTH Viettel, các session PPPoE gia đình dù nhận IP interface là `100.77.x.x`, nhưng khi gói tin đi qua trạm BRAS ra Internet công cộng, **mỗi session PPPoE độc lập vẫn được trạm NAT ra một IP Public riêng biệt** (ví dụ `117.5.152.x`, `117.5.153.x`).
- **Nguyên nhân dồn chung 1 IP:** Khi directive `Bind $ip_addr` trong file cấu hình Tinyproxy bị comment out (`#Bind $ip_addr`), tất cả instance proxy không bind vào interface tương ứng mà tuôn toàn bộ traffic theo default route của kernel OpenWrt, dẫn đến 16 cổng proxy bị dồn chung về đúng 1 IP Public của interface default!

## 2. Tử Huyệt DNS: Tailscale Ghi Đè `/etc/resolv.conf` Gây Lỗi 500 Unable to Connect
- Khi cài Tailscale trên OpenWrt, MagicDNS sẽ tự động chiếm dụng `/etc/resolv.conf` và trỏ nameserver về `100.100.100.100`.
- Khi Tailscale daemon bị dừng hoặc kết nối VPN chưa thiết lập, router R3G **mất hoàn toàn khả năng phân giải tên miền ra ngoài** (`Could not resolve host`).
- Hậu quả: Tinyproxy nhận request từ client nhưng không resolve được target hostname, trả về lỗi `500 Unable to connect`.
- **Khắc phục triệt để:** Ép cứng `nameserver 8.8.8.8` hoặc `1.1.1.1` vào `/etc/resolv.conf` (hoặc cấu hình dnsmasq không bị Tailscale ghi đè) để đảm bảo router luôn resolve được DNS Direct WAN.

## 3. Kiến Trúc Hoàn Chỉnh: Policy Routing & Tinyproxy Bind
Mỗi sub-interface PPPoE cần 3 thành phần đồng bộ:
1. **Tinyproxy Instance Config (`/etc/tinyproxy/instances/tp_<PORT>.conf`):**
   ```text
   Port <PORT>
   Listen 0.0.0.0
   Allow 0.0.0.0/0
   Bind <IP_OF_PPPOE_INTERFACE>
   ```
2. **Policy Routing Table & IP Rule:**
   ```sh
   # Cho từng port và interface tương ứng:
   ip route replace default dev <INTERFACE_NAME> table <TABLE_ID>
   ip rule del from <INTERFACE_IP> table <TABLE_ID> 2>/dev/null
   ip rule add from <INTERFACE_IP> table <TABLE_ID>
   ```
3. **Math Assert Nghiệm Thu Độc Lập:**
   Bắt buộc đo đạc telemetry thực tế từ client ngoài mạng hoặc local curl qua 16 cổng:
   $$\text{len}(\text{set}(\text{egress\_ips})) == 16$$
   Chỉ khi đủ 16 IP Public độc lập mới được phép báo hoàn tất.
