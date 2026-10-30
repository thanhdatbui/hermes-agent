# Tailscale Persistence, CGNAT Subnet & Safe Second WAN Isolation

## 1. Tailscale State Persistence on OpenWrt Flash (/etc vs /tmp)
Khi cứu hộ headless hoặc chạy qua CLI, cờ `--state=/tmp/tailscaled.state` lưu key trên tmpfs (RAM). Router mất nguồn/reboot sẽ mất sạch chứng chỉ, rớt khỏi tailnet.
- **Vị trí lưu bền vững**: `/etc/tailscale/tailscaled.state` (trên overlay flash).
- **Procd init script (`/etc/init.d/tailscale`)**:
  ```sh
  #!/bin/sh /etc/rc.common
  USE_PROCD=1
  START=90
  STOP=10
  start_service() {
      procd_open_instance
      procd_set_param command /usr/sbin/tailscaled --state=/etc/tailscale/tailscaled.state --port=41641
      procd_set_param respawn
      procd_close_instance
  }
  ```
- **Fallback autorun tại `/etc/rc.local`**:
  ```sh
  /usr/sbin/tailscaled --state=/etc/tailscale/tailscaled.state --port=41641 >/dev/null 2>&1 &
  sleep 3
  tailscale up --hostname=r3g-thaibinh --accept-routes=true >/dev/null 2>&1 &
  exit 0
  ```
- **Firewall Zone cho Tailscale**:
  ```sh
  uci set firewall.@zone[3].device='tailscale0'
  uci commit firewall && /etc/init.d/firewall reload
  ```

## 2. Giải mã hiểu lầm IP CGNAT `100.64.0.0/10` vs IP Public Viettel
- **Dải 100.x trên Tailscale (`100.115.94.49`)**: Là IP overlay ảo do Tailscale cấp trong tailnet private.
- **Dải 100.x trên PPPoE Viettel (`100.77.187.230`)**: Là dải CGNAT chuẩn RFC 6598 của nhà mạng Viettel cấp cho thuê bao cáp quang dân dụng.
- **Xác nhận kết nối**: Khi router quay được IP CGNAT `100.77.x.x` và ping `8.8.8.8` RTT 27ms (0% loss), router đã thông Internet quốc tế hoàn toàn. Tailscale lập tức online và mở cổng SSH 22 + LuCI 80/443.

## 2.1. Quản lý thiết bị trùng lặp trên Tailscale Admin Console (Dọn Node Rác)
- **Hiện tượng**: Khi router được deploy lại, reset state hoặc đổi hostname nhiều lần, Tailscale Admin Console sẽ xuất hiện nhiều node trùng lặp (ví dụ `r3g-thaibinh` cũ có chấm xám `Offline` và `r3g-thaibinh-1` mới có chấm xanh lá `Connected`).
- **Xác minh node thật**:
  * Chạy `tailscale status --json` từ local machine kiểm tra IP (`100.115.94.49`), status `Online: True`, và `LastSeen`.
  * Trên Tailscale Admin Console web UI, tìm đúng node cũ bị Offline (chấm xám), bấm vào menu `•••` ở góc phải, chọn `Remove...` để xóa bỏ vĩnh viễn, tránh gây nhầm lẫn khi tra cứu IP.

## 2.2. Kiểm chứng vật lý khi người nhà cắm / rút dây (Physical Carrier vs Interface State)
- **Tránh kết luận vội vã khi Tailscale chập chờn**: Khi người tại chỗ thao tác rút/cắm dây (ví dụ rút dây cổng giữa `lan1`), tay có thể va quẹt làm lỏng tạm thời cổng bên cạnh (`lan2`), khiến Tailscale ngắt kết nối trong 30-60 giây rồi tự reconnect.
- **Quy trình kiểm chứng hiện trường 2 bước**:
  1. Kiểm tra carrier phần cứng:
     ```sh
     cat /sys/class/net/lan1/carrier # 0: không có tín hiệu điện/chưa cắm chặt; 1: có tín hiệu 1Gbps
     cat /sys/class/net/lan2/carrier # 1: đường sống bình thường
     ```
  2. Đo đạc đầu cuối (End-to-End Test): Dùng máy PC local gọi test HTTPS ra ngoài qua từng cổng proxy (`5102..5108`) để chứng minh lưu lượng thực tế ra IP Public Viettel Thái Bình (`117.5.x.x`), độc lập với việc cổng phụ có cắm dây hay không.

## 3. Quy tắc an toàn sống còn khi cấu hình đường WAN thứ hai (Chống rớt Tailscale)
Khi router đã online qua WAN thứ nhất (đang giữ default route nuôi Tailscale):
- **CẤM TUYỆT ĐỐI**: Để đường WAN thứ hai tự động gán default route (`add_default_route` / `defaultroute '1'`). Hai đường đè route trong bảng `main` sẽ làm gói tin Tailscale đi sai cổng hoặc bị drop, văng SSH ngay lập tức.
- **Quy tắc cô lập đường thứ hai**:
  1. Set `uci set network.wan.defaultroute='0'`.
  2. Dùng bảng routing riêng (Policy Routing / Table 100) cho đường thứ hai để phục vụ MACVLAN/Proxy xoay.
  3. Đường thứ nhất (`WAN2`) độc quyền giữ Default Route hệ thống nuôi SSH/Tailscale.

## 4. Bẫy nhầm lẫn / trùng lặp tài khoản PPPoE trên Dual-WAN (False PADO Timeout)
- **Cơ chế khóa cổng của ISP (Port / Circuit ID Binding)**: Nhà mạng Viettel/VNPT khóa tài khoản PPPoE tương ứng 1:1 theo cổng quang trên trạm OLT/BRAS.
- **Hiện tượng**: Khi cấu hình chéo qua lại, nếu cả 2 interface (`wan` trên `lan1` và `WAN2` trên `lan2`) đều bị gán trùng 1 username (ví dụ cả hai đều điền `hyn_gftth_tamnhb1`), thì cổng cắm vào đường cáp Line 0 sẽ bị trạm BRAS từ chối trả lời gói tin PADO.
- **Hậu quả**: Interface bị báo lỗi `Timeout waiting for PADO packets`, khiến kỹ sư lầm tưởng cổng mạng bị hỏng hoặc modem chưa bật Bridge.
- **Kỷ luật kiểm tra**:
  1. Luôn dùng `uci show network.<interface>` đọc lại username/password thực tế trên từng cổng trước khi kết luận lỗi mạng.
  2. Kiểm tra thanh ghi phần cứng `cat /sys/class/net/<port>/carrier`: nếu trả về `1` thì cáp mạng và modem đối tác đang cấp tín hiệu tốt; lỗi PADO lúc này 100% do sai tài khoản hoặc modem chưa bridge cổng đó.
  3. Đảm bảo mỗi cổng cắm đúng tài khoản được cấp theo hợp đồng của sợi cáp đó (`Line 0` -> `tamnhb0`, `Line 1` -> `tamnhb1`).

## 5. Kiến trúc xoay Proxy Farm trên OpenWrt (MACVLAN + Multi-Session PPPoE + 3proxy)
- **Mục tiêu**: Xoay 8 - 16 cổng proxy trên 1 - 2 đường cáp quang PPPoE (mô phỏng kiến trúc MobiProxy/MikroTik).
- **Phân lớp kiến trúc 4 tầng**:
  1. **Tầng Card ảo (MACVLAN)**: Trên interface vật lý (ví dụ `lan2`), tạo $N$ card ảo (`macvlan1` .. `macvlan8`) với MAC address ngẫu nhiên độc lập (`ip link add link lan2 name macvlanX type macvlan mode bridge`).
  2. **Tầng Quay số Multi-Session**: Mỗi card MACVLAN chạy một session PPPoE độc lập dùng chung tài khoản mạng của line đó. BRAS Viettel cấp $N$ địa chỉ IP Public khác nhau cho từng session.
  3. **Tầng Định tuyến Cô lập (Policy Routing)**: Mỗi session PPPoE được gán bảng định tuyến riêng (`table 101` .. `table 108`), mỗi bảng chỉ có 1 default route qua interface tương ứng. **Interface chính giữ Tailscale (`WAN2`) độc quyền bảng `main`, không bị ảnh hưởng khi xoay proxy.**
  4. **Tầng Dịch vụ Proxy (3proxy / Tinyproxy)**: Mở $N$ port (5101..5108), mỗi port bind ngõ ra vào IP của card MACVLAN tương ứng. Xoay IP từng port bằng lệnh reconnect session (`ifdown wan_subX && ifup wan_subX`) trong 3-5 giây mà không làm gián đoạn các port khác hay đường quản lý Tailscale.
