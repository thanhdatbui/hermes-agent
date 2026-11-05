---
name: mikrotik-kernel-dnat-and-multiwan-proxy-ops
description: "Vận hành Kernel DNAT trên MikroTik, cấu hình MobiProxy No-Auth, xử lý Asymmetric Routing R3G Multi-PPPoE và cơ chế Dead Lock Reap cho pipeline."
---
# MikroTik Kernel DNAT & Multi-WAN Proxy Operations (MobiProxy & R3G)

## 1. Bản chất hạ tầng: MobiProxy vs Xiaomi R3G
- **MobiProxy:** Cắm 4 line mạng cáp quang vật lý (Lan1..Lan4), mỗi line quay đa phiên 8 PPPoE chia ra các port proxy 5101..5138.
  - Trên web quản trị v3.0.67, bảng danh sách `#proxies` có menu dấu 3 chấm `•••` -> `Cấu hình truy cập` -> modal HTML5 Dialog với nút `#access-save` để đổi chế độ xác thực từng port sang `none` (Không xác thực).
  - Tắt pass trên MobiProxy an toàn 100% nhờ lớp tường lửa Chống scan proxy (Scan Guard Whitelist IP) tại mục `#security`.
- **Xiaomi R3G:** Cắm 2 line mạng cáp quang vật lý, quay đa phiên 16 đường PPPoE con:
  - Line 1 (LAN2): Cổng 5141-5148 (`pppoe-WAN2`, `wan_sub2..sub8`).
  - Line 0 (LAN1): Cổng 5151-5158 (`pppoe-wan`, `wan_sub11..sub17`).
  - 16 port Tinyproxy trên R3G vốn dĩ **không hề cài mật khẩu** (`BasicAuth` = none), bảo vệ bằng whitelist `Allow <mikrotik_ip>`.

## 2. Kỷ luật vận hành Kernel DNAT trên MikroTik
- **Giải phóng CPU tuyệt đối:** Kernel DNAT xử lý gói tin wire-speed ở tầng L3/L4 của chip MikroTik mà không cần chuyển ngữ cảnh L7 sang user-space Singbox container, giúp CPU router rơi thẳng từ ~97% về ~1.6%.
- **Thứ tự Rule NAT:** Các rule Kernel DNAT per-device (`chain=dstnat dst-port=2000X to-addresses=<proxy_ip> to-ports=510X`) BẮT BUỘC phải đặt trước rule gom Singbox (`*30E`).
- **Đồng bộ DDNS 1 phút / lần:** Khi MobiProxy đổi IP WAN qua PPPoE quay số, script `scripts/update_mikrotik_scan_guard.py` tự động phân giải `test.taadaa.click` và cập nhật tức thời `to-addresses` cho 38 rule DNAT. Cronjob phải chạy mỗi 1 phút (`* * * * *`).
- **Fail-Closed & Chống lộ IP:** Khi proxy sập / mất kết nối, máy S7 bị ngắt kết nối (TCP drop/timeout) tự nhiên và hiện dấu chấm than trên Wi-Fi. Rule tường lửa `*D` (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`) cùng khóa UDP 443/53 đảm bảo 100% không bao giờ rò rỉ IP gốc Đà Nẵng ra ngoài.
- **CẤM Cron tự đổi proxy gây mất mạng:** Tuyệt đối không bật các cronjob tự động heal/reset cổng MobiProxy ngoài giờ kiểm soát (như `cron_mobiproxy_healer.py`) làm rớt phiên nuôi của farm.
- **Dọn sạch VPS hết hạn:** Xóa vĩnh viễn mọi WireGuard peer/route/firewall của VPS đã hết hạn (như VPS Doravo Sentinel) để đóng sập hoàn toàn cửa ngõ vào mạng LAN farm.

## 3. Asymmetric Routing trên R3G Multi-PPPoE & Giải pháp PBR 2 chiều Dứt điểm
- **Nguyên nhân Timeout/502 khi DNAT sang R3G:** Tên miền `tb.taadaa.click` trỏ về IP của 1 line PPPoE duy nhất, nhưng Tinyproxy cổng 5141..5148 lại bind trên line `WAN2`. Gói tin vào một đường nhưng phản hồi trả ra đường khác, bị cơ chế uRPF của ISP Viettel drop ngay tại trạm.
- **Lỗi DNS Resolv:** Cấm để địa chỉ DNS ma (như `100.100.100.100` khi Tailscale không chạy) trong `/etc/resolv.conf` của R3G khiến Tinyproxy bị treo 5s mỗi khi phân giải tên miền. Bắt buộc dùng `8.8.8.8` và `1.1.1.1`.
- **Giải pháp PBR 2 chiều Triệt để trên OpenWrt R3G (Đã kiểm chứng LIVE S7):**
  1. **Sinh đủ 16 instance Tinyproxy:** Chạy `sh /root/generate_all_proxies.sh` để cả 16 cổng (`5141..5148` trên LAN2 và `5151..5158` trên LAN1) mở socket listening `0.0.0.0:51xx`.
  2. **Mở Firewall Input cho MikroTik WAN1:** Thêm rule firewall trên OpenWrt cho phép IP WAN chính của MikroTik (`171.231.180.189`):
     ```sh
     uci add firewall rule
     uci set firewall.@rule[-1].name='Allow-Proxies-MikroTik-WAN1'
     uci set firewall.@rule[-1].src='wan'
     uci set firewall.@rule[-1].proto='tcp'
     uci set firewall.@rule[-1].dest_port='5141 5142 5143 5144 5145 5146 5147 5148 5151 5152 5153 5154 5155 5156 5157 5158'
     uci set firewall.@rule[-1].src_ip='171.231.180.189'
     uci set firewall.@rule[-1].target='ACCEPT'
     uci commit firewall && /etc/init.d/firewall reload
     ```
  3. **Ép luồng phản hồi về đúng cổng WAN nhận (PBR rule):**
     ```sh
     ip rule add to 171.231.180.189 table 200 priority 5000
     ip route replace default dev pppoe-wan table 200
     ```
     Toàn bộ gói tin phản hồi của 16 cổng proxy khi gửi lời đáp về MikroTik Đà Nẵng sẽ được ép đi ngược ra bằng đúng interface `pppoe-wan`, triệt tiêu 100% lỗi Asymmetric Routing, phản hồi wire-speed `0.55s – 0.6s` và máy S7 (như Máy 203) nhận chuẩn IP Viettel không có chấm than Wi-Fi.

## 4. Kỷ luật Pipeline & Dead Lock Reaping
- **Cấm ngụy biện Canary khi sửa router:** Sửa router RouterOS/OpenWrt là thao tác cấu hình thiết bị qua REST API / SSH, không được ngụy biện hay lạm dụng pipeline Canary của app Android.
- **Tự động dọn lock rác (`Dead Lock Reap`):** Pipeline `unified_patch_pipeline.py` khi acquire repo lock phải kiểm tra `psutil.pid_exists(pid)`. Nếu PID cũ đã chết, tự động unlink file lock để tránh tình trạng deadlock đóng băng hệ thống.
