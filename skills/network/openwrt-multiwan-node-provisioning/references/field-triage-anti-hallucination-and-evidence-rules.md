# Kỷ Luật Thực Địa: Chống Bịa Đặt Output Lệnh, Cô Lập Dual-WAN & Quy Tắc Cứu Hộ Remote

Tài liệu đúc kết từ sự cố cứu hộ Router Xiaomi R3G (ImmortalWrt 21.02) qua UltraViewer/ttyd LuCI khi triển khai 2 line PPPoE Viettel.

---

## 1. Kỷ Luật Bằng Chứng Tuyệt Đối (Anti-Hallucination OCR Rule)
- **CẤM TUYỆT ĐỐI bịa đặt output lệnh chưa chạy:** Khi User gửi ảnh terminal dán chuỗi lệnh ghép (ví dụ `echo ... && nslookup ... && wget ...`), bộ đệm clipboard ttyd thường nuốt ký tự hoặc chỉ thực thi lệnh đầu tiên (`ping`). Các lệnh sau chưa kịp in ra stdout. 
- **Quy tắc fail-closed:** Nếu OCR không đọc thấy text của lệnh (không có `nslookup`, không có `wget`), Coordinator BẮT BUỘC phải thừa nhận lệnh chưa chạy hoặc chưa có kết quả. Tuyệt đối KHÔNG ĐƯỢC tự suy diễn ra các thông báo lỗi kinh điển như `;; connection timed out; no servers could be reached` hay `download timed out` khi không có chữ đó trên màn hình. Hành vi này gây mất lòng tin nghiêm trọng từ người dùng.

---

## 2. Bẫy Chẩn Đoán Lầm: Đổ Lỗi ISP "Walled Garden" vs Xung Đột Dual-WAN Local
- **Hiện tượng:** Cổng `pppoe-WAN2` nhận IP `172.17.x.x` (hoặc CGNAT), ping gateway trạm BRAS `27.68.227.150` được (0% drop, 2ms), nhưng `ping 8.8.8.8` bị 100% packet loss.
- **Bẫy suy diễn sai:** Vội vàng kết luận do ISP chưa mở luồng Internet / cấp nhầm dải Walled Garden và xui giục User bắt thợ chỉnh trạm, trong khi thợ đã kiểm chứng bằng router khác gọi Zalo bình thường.
- **Nguyên nhân cốt lõi thật sự:**
  1. **Xung đột 2 Default Route trong bảng `main`:** Cả 2 interface `wan` và `wan2`/`WAN2` cùng bật `defaultroute '1'`. Khi một line bị PADO timeout hoặc down, kernel Linux giữ default route cũ hoặc bảng định tuyến bị tranh chấp luồng phản hồi (Asymmetric routing / reverse path filtering `rp_filter`).
  2. **Thiếu Firewall Masquerade cho Interface mới:** Trên OpenWrt, interface tạo thủ công trên LuCI mang tên chữ HOA (ví dụ `WAN2`) thường chưa được gán vào Firewall Zone `wan` (`uci get firewall.@zone[1].network`). Thiếu Masquerade và MSS Clamping (`mtu_fix`), mọi traffic forward hoặc local ping qua netdev đó bị drop sạch.
- **Quy tắc cô lập:** Trước khi kết luận do ISP, BẮT BUỘC phải **cô lập về Single-WAN**:
  - Tạm thời tắt interface thứ 2: `uci set network.wan.disabled='1' && uci commit network && ifdown wan`.
  - Ép duy nhất 1 default route vào interface đang sống: `ip route replace default dev pppoe-WAN2`.
  - Bật masquerade: `uci set firewall.@zone[1].masq='1' && uci commit firewall && /etc/init.d/firewall restart`.
  - Test ping lại: `ping -c 3 8.8.8.8`.

---

## 3. Kiến Trúc Đối Soát: MikroTik / MobiProxy Policy Routing vs OpenWrt
- **MikroTik RouterOS:** Không bao giờ để 2 line PPPoE đè chung bảng `main`. Mỗi line có 1 routing table riêng (`table=WAN1`, `table=WAN2`), kết hợp mangle `mark-routing` và routing rule `action=lookup-only-in-table`. Cổng nào đi ra gateway cổng đó 100%.
- **MobiProxy (Linux OpenWrt custom):** Dùng `macvlan` tạo interface ảo độc lập, mỗi line gắn vào một bảng định tuyến riêng (`ip route add default dev pppoe-X table 10X` + `ip rule add from <ip> table 10X`). Hoàn toàn không bị đè default route.
- **OpenWrt R3G khi chưa cấu hình `mwan3`:** CẤM TUYỆT ĐỐI bật đồng thời 2 line PPPoE cùng lúc mà không có metric phân cấp hoặc mwan3. Phải đưa 1 line lên Internet ổn định, kích hoạt Tailscale, sau đó mới triển khai Policy Routing / mwan3.

---

## 4. Kỷ Luật Dán Lệnh Qua Web Terminal (ttyd LuCI / UltraViewer)
- Web terminal `ttyd` chạy trên LuCI khi nhận văn bản dán qua UltraViewer thường xuyên bị:
  1. Nuốt sạch ký tự `&&` và `&` (khiến lệnh ghép bị dính chữ thành tham số vô nghĩa văng `Usage: uci`).
  2. Nuốt dấu `&` ở cuối khiến các tiến trình daemon chiếm foreground làm treo terminal.
- **Quy tắc vàng:** Chỉ cung cấp từng dòng lệnh đơn lẻ, độc lập, không dùng `&&`, không dùng `&` chạy ngầm. Nếu cần chạy ngầm daemon, bắt buộc dùng wrapper hệ thống như `start-stop-daemon -S -b -x ...` thay vì gõ `&`.
