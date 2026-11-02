# Kiến Trúc Direct WAN Proxy Trên Xiaomi R3G & Cơ Chế Anti-Scan Whitelist

## 1. Hiện Tượng & Nguyên Nhân
- **Bệnh cũ:** Trên router OpenWrt (Xiaomi R3G MT7621), khi chạy proxy 1:2 (16 cổng `5141..5158`) qua hai đường PPPoE (Line 0 và Line 1):
  - Line 1 bị dính dải IP nội bộ `100.77.x.x` do thiếu `Bind $ip_addr` trong file cấu hình Tinyproxy, dẫn đến toàn bộ traffic đi ra default route dồn về 1 IP duy nhất.
  - Ngộ nhận "nhà mạng khóa CGNAT" sinh ra do không tra cứu lịch sử và mớm cung Cố vấn. Thực tế, khi Tinyproxy `Bind` đúng IP của từng sub-interface, mỗi port khi đi qua trạm Viettel sẽ egress ra một IP Public riêng biệt (`117.5.152.x`, `117.5.153.x`).

## 2. Các Bước Cấu Hình Direct WAN Chuẩn
1. **Tinyproxy Instance Configuration:**
   - Mỗi file cấu hình instance (`/etc/tinyproxy/instances/tp_51xx.conf`) bắt buộc có:
     ```text
     Port 51xx
     Listen 0.0.0.0
     Bind <IP_WAN_SUB_INTERFACE>
     Allow 0.0.0.0/0  # Hoặc whitelist theo subnet
     ```
2. **Policy Routing 16 Bảng:**
   - Gán `ip route replace default dev pppoe-wan_subX table Y`
   - Gán `ip rule add from <IP_WAN_SUB_INTERFACE> table Y`
3. **DNS Resolver:**
   - Đảm bảo `/etc/resolv.conf` có `nameserver 8.8.8.8` (tránh bị Tailscale hoặc DHCP ghi đè làm hỏng phân giải tên miền).
4. **Cloudflare DDNS Tự Động (2 phút/lần):**
   - Script `/root/cf_ddns.sh` chạy cronjob `*/2 * * * *` kiểm tra IP của interface chính, tự động gọi API Cloudflare cập nhật record `tb.taadaa.click`.

## 3. Cơ Chế Whitelist Chống Scan Botnet
- **Tại sao chỉ cần whitelist IP của `pppoe-out1` trên MikroTik Đà Nẵng?**
  - Sing-box chạy trên Router MikroTik (`192.168.110.2`) đảm nhận vai trò Outbound forward traffic từ điện thoại Samsung S7 sang proxy Thái Bình.
  - Khi Sing-box tạo kết nối ra ngoài Internet, nó luôn đi theo Default Route của MikroTik, tức là qua interface **`pppoe-out1`**.
  - Do đó, chỉ cần whitelist IP WAN của `pppoe-out1` (và IP mạng nhà Kibe) là toàn bộ dàn 160 máy S7 thông mạng mượt mà, đồng thời DROP 100% botnet scan trộm từ bên ngoài.
- **Tự động đồng bộ IP:**
  - Script `update_mikrotik_scan_guard.py` chạy định kỳ kiểm tra IP của `pppoe-out1` và PC Kibe, tự động đẩy IP mới lên whitelist khi nhà mạng đổi IP.
