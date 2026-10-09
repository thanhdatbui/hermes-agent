# MikroTik Proxy Troubleshooting & Firewall Antipatterns

## 1. Context & Architecture
- MikroTik RouterOS quản lý 35 lines PPPoE (`pppoe-out1..35`) và container 3proxy (`172.16.0.2` trên interface `dockers_proxy`).
- Proxy ports:
  - HTTP proxy: `10001` – `10035`
  - SOCKS5 proxy: `20001` – `20080` (M01..M80)
- Anti-scan Policy: `FPT_LAN` whitelist (`192.168.110.0/24`, `192.168.10.0/24`, `127.0.0.1`) cho phép truy cập proxy. External WAN truy cập vào proxy ports bị DROP bởi rule `DROP_EXTERNAL_PROXY_PORTS`.

## 2. Pitfalls & Anti-Patterns đã gặp

### Pitfall 1: Xung đột `src-address` và `src-address-list` trong Filter Rule
- **Triệu chứng**: Rule allow proxy ports không match packet nào (`packets=0`, `bytes=0`), traffic bị trôi xuống rule DROP bên dưới khiến toàn bộ proxy bị chặn (kể cả từ LAN hoặc WAN qua domain).
- **Nguyên nhân**: Khi sửa rule filter qua REST API, nếu vô tình set cả `src-address` (ví dụ `0.0.0.0/0` hoặc `192.168.10.0/24`) VÀ `src-address-list=FPT_LAN`, RouterOS yêu cầu match đồng thời cả 2 điều kiện. Hơn nữa, PATCH giá trị rỗng (`""`) qua REST API trả về `HTTP 400 Bad Request`.
- **Giải pháp đúng**: Xóa rule cũ (`DELETE /ip/firewall/filter/<id>`) và tạo lại rule mới hoàn toàn sạch với `src-address-list=FPT_LAN`, không định nghĩa trường `src-address`. Sau đó dùng `move` đặt ngay trước rule DROP.

### Pitfall 2: Duplicate NAT rules khi chạy script loop không idempotency
- **Triệu chứng**: Bảng `/ip/firewall/nat` phình to với hàng chục rule `dstnat` giống hệt nhau cho cùng 1 port.
- **Nguyên nhân**: Dùng `PUT /ip/firewall/nat` nhiều lần mà không kiểm tra rule đã tồn tại hay chưa.
- **Giải pháp**: Luôn kiểm tra danh sách rules hiện tại (`GET /ip/firewall/nat`) trước khi thêm, xóa các bản sao trùng lặp, chỉ giữ đúng 1 rule cho mỗi port.

### Pitfall 3: 3proxy trả về HTTP 502 Bad Gateway trên plain HTTP
- **Triệu chứng**: `curl` / `urllib` qua proxy tới `http://` trả về `502 Bad Gateway (Host Not Found or connection failed)`.
- **Thực tế**: HTTPS CONNECT method (`https://api.ipify.org`) vẫn hoạt động bình thường 200 OK và trả về đúng IP outbound của line PPPoE. TikTok và các app di động đều dùng HTTPS. Đừng vội kết luận proxy chết chỉ vì test HTTP plain bị 502.

### Pitfall 4: Báo cáo dài dòng khi user hỏi trạng thái kết nối
- **Nguyên tắc**: Khi user hỏi "đã xài được chưa", trả lời THẲNG VÀO TRỌNG TÂM:
  1. PC Kibe: Xài được / Chưa xài được (kèm bằng chứng 1 dòng: IP/port test).
  2. S7 (Phone farm): Xài được / Chưa xài được (kèm SSID Wi-Fi, trạng thái thông port).
  3. Tuyệt đối không giải thích dài dòng lý do kỹ thuật nếu không được yêu cầu.
