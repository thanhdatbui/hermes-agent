# Multi-WAN PPPoE Policy Routing, Firewall Masquerade & Cross-Device Reference Pitfalls

## 1. Remote Web Terminal (ttyd/LuCI) Command Chaining Trap
- **Bẫy Nuốt Ký Tự**: Trình duyệt qua remote desktop (UltraViewer/AnyDesk) hoặc web console `ttyd` thường nuốt mất ký tự `&&`, `&`, `|`.
- **Hậu Quả**:
  - `cmd1 && cmd2` biến thành `cmd1 cmd2` -> gây lỗi cú pháp (vd `Usage: uci [...]`).
  - Lệnh chạy nền `&` bị nuốt -> process chiếm giữ terminal, khi bấm `Ctrl+C` thoát lệnh thì tiến trình nền (daemon) bị kill luôn theo.
- **Quy Tắc**:
  1. Tuyệt đối đưa từng dòng lệnh đơn lẻ, cấm nối `&&`.
  2. Muốn chạy ngầm daemon (như `tailscaled`) trên OpenWrt, dùng `start-stop-daemon -S -b -x ...` thay vì gõ dấu `&` thủ công.

## 2. Multi-WAN Interface Case-Sensitivity & Ping Interface Trap
- **Linux Netdev Phân Biệt Hoa Thường**: Trong OpenWrt, interface `WAN2` sinh ra l3 device là `pppoe-WAN2` (chữ in hoa).
- **Bẫy Test Sai Cổng**: Nếu gõ `ping -I pppoe-wan 8.8.8.8` (chữ thường) trong khi cổng đang sống là `pppoe-WAN2` và cổng `wan` đang rớt, kết quả sẽ luôn báo `100% packet loss` gây phán đoán sai lệch là toàn bộ mạng mất kết nối.
- **Quy Tắc**: Luôn lấy tên device chuẩn từ `ifstatus <IFACE>` (trường `"l3_device"`) trước khi ép interface bằng cờ `-I`.

## 3. Firewall Masquerade & Default Route Pitfall on OpenWrt Multi-WAN
- Khi tạo interface WAN phụ (`WAN2`) thủ công:
  - Nếu chưa gán vào Firewall Zone `wan` (`uci add_list firewall.@zone[1].network='WAN2'`) và bật `masq='1'`, gói tin trả về từ Internet không được NAT/Masquerade, dẫn tới rớt 100% packet loss.
  - Cần đảm bảo có default route rõ ràng hoặc mwan3 policy routing phân tách riêng từng interface để tránh xung đột routing table giữa 2 đường PPPoE.

## 4. Bẫy Suy Diễn Kết Quả Khi Ảnh / Log Chưa Hiển Thị (Evidence-First Rule)
- Tuyệt đối không bao giờ phán `connection timed out` hay `fail` khi terminal chưa chạy xong lệnh hoặc chưa in ra stdout tương ứng.
- Khi dán khối lệnh dài bị văng `Usage: ...`, các lệnh sau thực chất chưa chạy; phải hướng dẫn chạy từng lệnh đơn và đọc đúng từng dòng stdout trên màn hình thực tế.

## 5. Tham Chiếu Cấu Hình Chuẩn Từ Router MikroTik Đang Chạy Sống
- Khi nghi ngờ đường mạng ISP cần tag VLAN hay không:
  - Kiểm tra router MikroTik (`/rest/interface/macvlan`, `/rest/interface/pppoe-client`): 60 đường PPPoE chạy qua MACVLAN trực tiếp trên cổng vật lý không cần tag VLAN 35 (`VLAN: 0`), `ac-name` và `service-name` để trống.
  - Điều này loại trừ giả thuyết ISP bắt buộc tag VLAN trên router quay PPPoE dân dụng, tập trung vào routing và firewall NAT.
