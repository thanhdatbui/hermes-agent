# OpenWrt Tinyproxy Multi-WAN Egress Fallback & Default Route Pitfalls

## 1. Bản chất Hiện tượng: Hàng loạt cổng Proxy ăn chung 1 Egress IP (Default Route Collapse)
Trên router OpenWrt (như Xiaomi R3G) chạy nhiều session PPPoE:
- Khi tắt hoặc comment chỉ thị `Bind <ip_addr>` trong Tinyproxy (`#Bind $ip_addr`) để tránh lỗi bất đối xứng:
- **Tác dụng phụ nghiêm trọng:** Tinyproxy mở socket outbound mà không gán IP nguồn cụ thể (`SO_BINDTODEVICE` hoặc `bind()` INADDR_ANY).
- Khi đó, Linux kernel sẽ tự động bốc IP nguồn và interface theo **Default Route** trong bảng định tuyến chính (`main`/`default`).
- **Hậu quả:** Toàn bộ các cổng proxy (ví dụ cả 16 port 5141..5158) dù listen trên các port khác nhau nhưng khi gửi request ra Internet đều chui qua cùng 1 interface mặc định (thường là WAN2 hoặc WAN1), dẫn đến việc **toàn bộ các máy điện thoại ăn chung 1 địa chỉ IP Public duy nhất**.

## 2. Rủi ro CGNAT Tái phát trên Đường truyền Viettel
- Khi quay số PPPoE trên các gói cước gia đình / doanh nghiệp nhỏ của Viettel:
  - Nếu chưa được tổng đài ghim profile Non-CGNAT cứng vào port thuê bao trên OLT:
  - Sau mỗi lần router reboot hoặc ngắt kết nối quay lại, hệ thống BRAS có thể ngẫu nhiên cấp IP dải Carrier-Grade NAT `100.64.0.0/10` (như `100.77.98.x`).
  - Toàn bộ các session dính CGNAT khi ra Internet đều bị trạm NAT của Viettel gom chung vào 1 IP Gateway công cộng duy nhất (ví dụ `117.5.152.50`).

## 3. Cấm Sửa Đè Trực Tiếp & Làm Mất Kết Nối Tailscale Headless
- **CẤM TUYỆT ĐỐI:** Tự ý SSH chạy các lệnh `killall -9 tinyproxy`, sửa config rồi restart hàng loạt khi đang kết nối qua đường hầm Tailscale trên thiết bị headless ở xa.
  - Trên router chip yếu (MT7621), việc restart dồn dập các tiến trình proxy hoặc cấu hình sai route/interface có thể làm nghẽn CPU, loop network hoặc đứt session của daemon `tailscaled`, dẫn đến mất kết nối SSH và biến router thành "cục gạch từ xa".
- **Quy trình chuẩn an toàn:**
  1. Luôn sử dụng watchdog tự phục hồi độc lập trên router (`/etc/rc.local` hoặc cron định kỳ) để tự khởi động lại `tailscale` nếu ping gateway mất.
  2. Bắt buộc test từng port đơn lẻ (`tp_5141.conf`) với cơ chế fallback trước khi áp dụng toàn bộ.
  3. Để cô lập luồng ra cho từng port proxy mà không gây treo mạng, sử dụng `mwan3` hoặc cắm cờ `fwmark` gắn với từng port inbound thay vì sửa thô bạo vào config lúc router đang phục vụ traffic.
