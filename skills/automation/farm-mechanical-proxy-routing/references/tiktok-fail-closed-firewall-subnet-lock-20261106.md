# Kỷ Luật Fail-Closed Toàn Diện: Khóa Tường Lửa 192.168.0.0/16 và Chống Lọt Direct WAN Khi Proxy Sập (2026-11-06)

## 1. Bản Chất Sự Cố Lọt Mạng (Fail-Open) của TikTok Khi Proxy Sập
- **Hiện tượng:** Khi tắt hoặc ngắt cổng proxy (qua Kernel DNAT hoặc bẻ IP đích sang IP chết `192.0.2.1`), trình duyệt web (HTTP Proxy) báo `ERR_EMPTY_RESPONSE` / `ERR_CONNECTION_REFUSED`, nhưng ứng dụng TikTok trên Samsung S7 (như Máy 204) vẫn tải được video bình thường (video đồ ăn, video thời trang).
- **Nguyên nhân cốt tử:**
  1. **Lệch Subnet Tường Lửa:** Rule Killswitch `*D` (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`) trên MikroTik ban đầu chỉ đặt `src-address=192.168.110.0/24` (chỉ bảo vệ 80 máy Kibe). Dàn máy Admin (Máy 201-280) nằm ở dải `192.168.10.0/24` không bị rule này chặn!
  2. **Bẫy Rule Forward Whitelist:** Rule `*10` (`ALLOW_FARM_ADMIN_FORWARD_FPT_LAN`) đứng ngay sau, cho phép `src-address-list=FPT_LAN` forward tự do ra WAN. Trong khi đó, list `FPT_LAN` lại chứa cả `192.168.10.0/24`.
  3. **TikTok SDK Fail-Open (TTNet):** Khi cổng HTTP Proxy không phản hồi, SDK TikTok lập tức thử kết nối trực tiếp hoặc dùng giao thức UDP 443 (QUIC). Vì không bị firewall drop, gói tin của máy S7 đi thẳng ra các line PPPoE Viettel Đà Nẵng, gây lộ IP thật và đe dọa an toàn toàn bộ tài khoản Farm!

## 2. Giải Pháp Khóa Cơ Học (Mechanical Killswitch) Triệt Để Trên RouterOS
- **Khóa toàn bộ dải IP Farm:** Mở rộng phạm vi chặn của rule `*D` từ `/24` lên `/16` để bao trùm cả `192.168.10.x` và `192.168.110.x`:
  ```routeros
  /ip firewall filter
  set [find comment="KILLSWITCH_BLOCK_FARM_DIRECT_WAN"] src-address=192.168.0.0/16 out-interface-list=WAN action=drop
  ```
- **Xóa dải Phone Farm khỏi whitelist forward WAN:**
  ```routeros
  /ip firewall address-list
  remove [find list=FPT_LAN address="192.168.10.0/24"]
  ```
- **Quy tắc kiểm chứng Fail-Closed:**
  - Sau khi ngắt proxy, mở TikTok và vuốt xem video mới.
  - Kết quả chuẩn: TikTok dừng hình, hiện thông báo `Không có kết nối mạng` kèm nút đỏ `Thử lại`, cột Wi-Fi hiện dấu chấm than (!), tuyệt đối không load được bất kỳ video mới nào từ Internet.
