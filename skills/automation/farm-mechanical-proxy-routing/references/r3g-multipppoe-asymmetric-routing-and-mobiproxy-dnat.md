# R3G OpenWrt Multi-PPPoE Asymmetric Routing vs MobiProxy Kernel DNAT Triage

## 1. Bản Chất Asymmetric Routing trên Xiaomi R3G (ImmortalWrt 21.02)
- **Cấu hình vật lý:** 2 line cáp quang vật lý -> Quay đa phiên 16 session PPPoE:
  - Line 1 (LAN2): `pppoe-WAN2`, `wan_sub2..sub8` (Port Tinyproxy 5141-5148)
  - Line 0 (LAN1): `pppoe-wan`, `wan_sub11..sub17` (Port Tinyproxy 5151-5158)
- **Cơ chế Tinyproxy:** Trong `/root/generate_all_proxies.sh`, mỗi instance bind vào IPv4 động của card PPPoE tương ứng (`Bind 100.123.x.x`). Tinyproxy hoàn toàn KHÔNG CÓ password (`NO_AUTH_IN_TINYPROXY`), bảo vệ bằng `Allow <MikroTik_IP>`.
- **Nguyên nhân Kernel DNAT Timeout sang R3G:**
  - Tên miền `tb.taadaa.click` chỉ trỏ về IP của 1 line PPPoE đại diện (`pppoe-WAN2`).
  - Gói tin DNAT từ MikroTik Đà Nẵng gửi vào IP của `pppoe-WAN2` trên cổng 5141.
  - Tinyproxy nhận và xử lý, nhưng khi phản hồi, bảng định tuyến Policy Routing của OpenWrt (16 table độc lập `101..217`) đẩy gói tin trả về ra sai interface PPPoE khác thay vì quay ngược về đường `pppoe-WAN2`.
  - Kết quả: Đứt gãy TCP 3-way handshake một chiều, MikroTik chờ 5s báo timeout.

## 2. MobiProxy (4G USB Dongle / Box) vs R3G Routing
- **MobiProxy:** Chỉ có 1 cổng WAN ra ngoài (default gateway duy nhất) -> Không bao giờ bị lỗi Asymmetric Routing. Một khi tắt password, Kernel DNAT (`dst-nat` từ `20002` sang `5102`) thông mạng siêu tốc ngay lập tức (`0.46s`).
- **R3G OpenWrt:** Bắt buộc phải có `CONNMARK` trên OpenWrt để ghim kết nối phản hồi (`iptables -t mangle -A PREROUTING -j CONNMARK --save-mark` và `OUTPUT -j CONNMARK --restore-mark`) trước khi DNAT hoạt động.

## 3. Quy Trình Chuyển Đổi No-Auth Trên MobiProxy Control Web v3
- **Bẫy nút hàng loạt:** Nút "Áp dụng cho tất cả proxy" trong tab `#security` không nạp lại backend process trong firmware v3.0.67.
- **Thao tác từng port chuẩn xác:**
  1. Trong `#proxies`, tìm hàng `proxyXX`.
  2. Mở thẻ `<details>` bằng `summary` (dấu 3 chấm `•••`).
  3. Click `button[data-action="proxy-access"]` để mở HTML5 `<dialog>`.
  4. Chọn `select[name="mode"]` hiển thị (`offsetParent !== null`) giá trị `none`.
  5. Bắt buộc click chính xác nút submit: `button#access-save`.
  6. Sau khi click `#access-save`, API `api.php?action=proxy.access` trả HTTP 200, cột XÁC THỰC chuyển sang nhãn xám `none`.
  7. Kiểm tra kết nối không auth qua cổng 51xx: phải phản hồi HTTP 200 OK ngay lập tức.
