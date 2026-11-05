# Quy trình Triển khai Kernel DNAT & Mangle Bypass cho Cụm Admin (R3G OpenWrt)

## 1. Bản chất sự cố dấu chấm than (!) trên Wi-Fi Android Farm
Khi chuyển các máy Admin non (`192.168.10.x`) sang chạy Kernel DNAT cổng `20201-20232` trỏ sang R3G Thái Bình, thiết bị bị mất kết nối và hiện dấu chấm than trên thanh trạng thái Wi-Fi do 2 nguyên nhân cốt lõi:
1. **Xung đột bảng Mangle trên MikroTik:**
   - 287 rule Mangle trên MikroTik ép các máy Admin đi ra các line `WAN8..WAN35` theo IP nguồn (`192.168.10.x`).
   - Khi gói tin gửi tới cổng DNAT, bảng Mangle đóng dấu cờ `mark-routing` khiến gói tin bị ném ra sai line WAN (`pppoe-out8` thay vì `pppoe-out1`).
   - R3G chỉ mở Whitelist nhận và trả lời cho `pppoe-out1` (`171.231.180.189`) -> R3G drop gói tin ngay từ cửa.
2. **Thiếu tham số `action=dst-nat` khi tạo rule qua REST API:**
   - Khi tạo rule NAT bằng REST API của RouterOS mà không khai báo rõ `'action': 'dst-nat'`, RouterOS sẽ để mặc định là `action=None` (hoặc passthrough), khiến gói tin không được chuyển tiếp cổng thực sự -> Client nhận lỗi `ERR_CONNECTION_REFUSED` / `WinError 10061`.

## 2. Giải pháp Kỹ thuật Triệt để (Standard Operating Procedure)

### Bước 1: Nạp Mangle Accept lên Top #0 của MikroTik
Tạo rule prerouting accept cho dải cổng proxy `20201-20280` và đưa lên vị trí đầu tiên (trước rule `*2`):
```routeros
/ip firewall mangle add chain=prerouting protocol=tcp dst-port=20201-20280 action=accept comment="BYPASS_MANGLE_FOR_ADMIN_R3G_DNAT"
/ip firewall mangle move [find comment="BYPASS_MANGLE_FOR_ADMIN_R3G_DNAT"] destination=0
```
Tác dụng: Khi client gửi request tới cổng proxy, rule này cho phép gói tin đi thẳng ra tuyến WAN chính (`WAN1`), triệt tiêu việc bị Mangle ép ra sai cổng WAN.

### Bước 2: Cấu hình Tường lửa & Tuyến phản hồi trên R3G OpenWrt
1. Chạy `/root/generate_all_proxies.sh` để mở đủ 16 port Tinyproxy (`5141..5148`, `5151..5158`).
2. Mở firewall cho dải subnet MikroTik:
   ```bash
   uci add firewall rule
   uci set firewall.@rule[-1].name='Allow-Proxies-MikroTik-Subnets'
   uci set firewall.@rule[-1].src='wan'
   uci set firewall.@rule[-1].proto='tcp'
   uci set firewall.@rule[-1].dest_port='5141 5142 5143 5144 5145 5146 5147 5148 5151 5152 5153 5154 5155 5156 5157 5158'
   uci add_list firewall.@rule[-1].src_ip='171.231.0.0/16'
   uci add_list firewall.@rule[-1].src_ip='116.110.0.0/16'
   uci set firewall.@rule[-1].target='ACCEPT'
   uci commit firewall && /etc/init.d/firewall reload
   ```
3. Nạp rule định tuyến ép câu trả lời về đúng table WAN chính (`table 200` qua `pppoe-wan`):
   ```bash
   ip rule add to 171.231.0.0/16 table 200 priority 5001
   ip rule add to 116.110.0.0/16 table 200 priority 5002
   ```

### Bước 3: Nạp 32 Rule Kernel DNAT có `action=dst-nat` trên MikroTik
- Tạo các rule chuyển tiếp `20201..20232` sang IP WAN đại diện R3G (`116.107.127.118:5141..5158`).
- Bắt buộc khai báo `'action': 'dst-nat'` trong payload REST API.
- Đẩy toàn bộ 32 rule DNAT này lên trước rule gom Singbox `*30E`.

## 3. Nghiệm thu Thực tế Gate 6 trên Thiết bị Thật
1. Kiểm tra trực tiếp trên máy thật qua ADB (`with_device_lock.py`):
   - Mở trình duyệt Samsung Internet hoặc Chrome truy cập `http://icanhazip.com`.
   - Chụp màn hình qua screencap (`raw.dump` -> PNG) và dùng Native Multimodal Vision soi mắt:
     - Dãy số IP hiển thị to rõ giữa màn hình đúng chuẩn IP Viettel của line R3G tương ứng.
     - Thanh trạng thái góc trên bên phải: Vạch sóng Wi-Fi căng đét, **chấm than (!) biến mất hoàn toàn 100%**.
2. Kiểm tra `dumpsys connectivity`: Trả về `Capabilities: INTERNET & VALIDATED & FOREGROUND`, xác nhận hệ điều hành Android đã thông suốt mạng.
