# Chi Tiết Vận Hành: MobiProxy DDNS Fast Rotation & R3G OpenWrt Dual-Cluster Triage (2026-11-05)

## 1. Bài Học Hiện Trường: MobiProxy Xoay IP Nhanh (Fast DDNS Rotation)
- **Hiện tượng:** Nhà mạng Viettel tại cụm MobiProxy Thái Bình có thể tự động reset/xoay IP WAN đại diện liên tục trong khoảng thời gian ngắn (ví dụ: `116.107.124.153` -> `117.5.179.223` -> `116.107.124.158`).
- **Nút thắt:** Nếu các rule Kernel DNAT trên MikroTik (`dst-port 20001..20038 -> to-addresses <IP>`) trỏ tĩnh vào IP cũ, toàn bộ farm Kibe sẽ bị lỗi kết nối hàng loạt (Connection Refused / Timed out) khi IP thay đổi mà cronjob chưa kịp quét.
- **Giải pháp cơ giới hóa:**
  - Nâng cấp tần suất cronjob `mobiproxy-scan-guard-auto-ip` (`update_mikrotik_scan_guard.py`) lên **1 phút/lần** (`* * * * *`, với `no_agent: true`).
  - Hàm `sync_mikrotik_mobiproxy_dnat()` trong script tự động phân giải domain `test.taadaa.click`, so sánh với `to-addresses` hiện có trên MikroTik, và tự động nạp PATCH cập nhật toàn bộ 38 rule DNAT trong vòng < 60 giây.

## 2. Bản Chất Sự Cố R3G OpenWrt 2 Line 16 PPPoE
- **Cấu hình Tinyproxy:** Cả 16 cổng Tinyproxy trên R3G (`5141..5158`) vốn dĩ KHÔNG DÙNG PASSWORD (`NO_AUTH_IN_TINYPROXY`), bảo vệ hoàn toàn bằng whitelist IP MikroTik (`Allow 171.231.180.189`).
- **Nút thắt DNS ngầm:**
  - File `/etc/resolv.conf` trên R3G bị Tailscale chèn nameserver ma `100.100.100.100`. Khi Tailscale daemon không chạy, Tinyproxy gửi truy vấn DNS phân giải domain upstream bị timeout 5 giây, gây ra lỗi `502 Bad Gateway` và rớt kết nối proxy trên các ca nuôi acc non.
  - Sửa dứt điểm bằng cách ghi đè `/etc/resolv.conf` thành `nameserver 8.8.8.8` và `nameserver 1.1.1.1`.
- **Nút thắt Asymmetric Routing (Đường đi một nẻo, đường về một ngả):**
  - Tên miền `tb.taadaa.click` chỉ trỏ về 1 line PPPoE (`wan_sub11`), trong khi các cổng 5141..5148 bind vào `WAN2` (dải CGNAT 100.77.x.x). Khi nhận gói tin vào bằng line này nhưng Tinyproxy trả lời bằng line khác, trạm BRAS của Viettel drop gói tin theo cơ chế uRPF.
  - Giải pháp bền bỉ chuẩn công nghiệp: Kết nối đường hầm WireGuard Site-to-Site giữa MikroTik Đà Nẵng và R3G Thái Bình (`10.200.0.1 <-> 10.200.0.4`), MikroTik DNAT vào IP nội bộ WireGuard để cô lập hoàn toàn luồng routing trả về.

## 3. Thu Hồi Bảo Mật: Xóa Bỏ VPS Hết Hạn
- Khi VPS (ví dụ: Doravo Sentinel) hết hạn dịch vụ, nhà cung cấp cloud sẽ tái cấp phát IP đó cho người khác.
- BẮT BUỘC rà soát và xóa sạch WireGuard Peer của VPS hết hạn trên router MikroTik (`/interface/wireguard/peers remove [find comment~"Doravo"]`) để triệt tiêu hoàn toàn nguy cơ người thuê sau sử dụng key cũ đột nhập vào mạng LAN farm.
