# R3G OpenWrt Multi-PPPoE Port Forwarding & Routing Lessons (2026-11-04)

## 1. Bản Chất Kiến Trúc Vật Lý R3G Farm Thái Bình
- Con Xiaomi R3G (ImmortalWrt 21.02) tại Thái Bình cắm **đúng 2 line mạng vật lý**:
  * Line 1 (cổng LAN2 / interface `tamnhb1`): Quay đa phiên 8 PPPoE (`pppoe-WAN2`, `pppoe-wan_sub2..sub8`) phục vụ **8 port Tinyproxy 5141-5148**.
  * Line 0 (cổng LAN1 / interface `tamnhb0`): Quay đa phiên 8 PPPoE (`pppoe-wan`, `pppoe-wan_sub11..sub17`) phục vụ **8 port Tinyproxy 5151-5158**.
- **Không có cổng WAN độc lập**: Tên miền `tb.taadaa.click` chỉ trỏ về IP Public của một trong 16 line PPPoE (ví dụ `pppoe-WAN2`).
- Mỗi tiến trình Tinyproxy chạy trên 1 port và bind vào IP PPPoE tương ứng (`Bind 100.123.x.x`). Mỗi session có bảng định tuyến riêng (`ip rule from <ip> table <tbl>` và `ip route replace default dev <dev> table <tbl>`).

## 2. Lỗi Asymmetric Routing Khi MikroTik DNAT Sang R3G
- **Hiện tượng**: Trên MikroTik Đà Nẵng cấu hình Kernel DNAT port 20203 sang `tb.taadaa.click:5141` thì kết nối bị `timed out` (mặc dù Tinyproxy đang chạy và port 5141 mở).
- **Nguyên nhân cốt lõi**:
  1. Gói tin từ MikroTik gửi đến IP WAN của `pppoe-WAN2`.
  2. Tinyproxy trên R3G nhận gói tin và xử lý.
  3. Khi gửi phản hồi (reply packet): Do R3G có 16 bảng định tuyến riêng và gói tin phản hồi xuất phát từ Tinyproxy hướng về IP ngoài mạng (MikroTik), nhân Linux OpenWrt đẩy gói tin phản hồi ra Gateway mặc định của bảng main hoặc route khác, **không đi ngược lại đúng interface PPPoE mà gói tin đã đi vào**.
  4. Lệch đường đi (Asymmetric Routing) khiến TCP Handshake giữa MikroTik và R3G không bao giờ hoàn tất.

## 3. Điều Kiện Để DNAT Hoạt Động (Yêu Cầu CONNMARK)
- Để chuyển tiếp TCP xuyên qua R3G thành công:
  * Phía MikroTik: Bắt buộc cấu hình cặp rule **DNAT + SNAT (Masquerade)** để R3G nhìn thấy IP nguồn là chính MikroTik.
  * Phía OpenWrt R3G: Cần có cơ chế **CONNMARK (Đánh dấu kết nối 2 chiều)** trong iptables mangle (`-A PREROUTING -m state --state NEW -j CONNMARK --save-mark` và `-A OUTPUT -m state --state ESTABLISHED,RELATED -j CONNMARK --restore-mark`) để ép gói tin phản hồi đi ra đúng interface PPPoE nó đã vào.
- **Cảnh Báo An Toàn Cực Cao (Remote SSH Bricking Risk)**: Can thiệp vào `iptables -t mangle` từ xa trên router cách hàng trăm km tiềm ẩn nguy cơ làm đá văng cổng SSH (`:22`) và Tailscale nếu rule bắt quá rộng không khóa chặt port proxy (`--dport 5141:5158`).

## 4. Kỷ Luật Giữ Sing-box Tinh Gọn (112 Máy)
- Tách biệt rõ ràng:
  * 48 máy Admin kênh chính: Chạy trực tiếp qua MikroTik PPPoE 3proxy (`10008-10035`), **HOÀN TOÀN KHÔNG CHO VÀO SINGBOX**.
  * 80 máy Kibe: Singbox forward sang MobiProxy (`test.taadaa.click:5101-5138`).
  * 32 máy Admin non: Singbox forward sang R3G (`tb.taadaa.click:5141-5158`).
- Cắt giảm 35% cấu hình Singbox giúp container giảm tải đáng kể mà vẫn giữ an toàn 100% cho đường truyền farm.
