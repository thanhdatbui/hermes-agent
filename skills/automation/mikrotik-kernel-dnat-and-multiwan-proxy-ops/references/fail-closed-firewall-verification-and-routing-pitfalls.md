# Fail-Closed Firewall Verification & Routing Pitfalls on MikroTik (2026-11-06)

## 1. Bản Chất Kỹ Thuật Khi Kiểm Chứng Fail-Closed Trên S7
Khi proxy upstream (MobiProxy/R3G) sập hoặc bị ngắt:
- **Ứng dụng Web thông thường (Chrome, API curl):** Lập tức báo lỗi timeout/refused.
- **Ứng dụng mạng TikTok (ByteDance TTNet/Cronet Engine):**
  1. **Hiệu ứng Video Buffer / Memory Cache:** Player nạp sẵn 2-4 video vào RAM/ROM. Khi vuốt qua lại, người dùng vẫn thấy phát video cũ mượt mà, dễ gây hiểu lầm là máy vẫn còn mạng.
  2. **Cách nhận diện mất mạng thực tế:**
     - Tab Video: Xem hết 2 video đệm, video thứ 3 sẽ quay tròn buffering hoặc đen màn hình.
     - Tab Cửa hàng (Shop): Xuất hiện các ô rỗng màu xám (Skeleton Loading Cards), tìm kiếm không bung sản phẩm.
     - Tab Khám phá / Profile: Không thể tải thêm feed hay thông tin tài khoản.
     - Lệnh kiểm chứng chuẩn: Ép `am force-stop` rồi `am start` (Cold-Boot), màn hình sẽ kẹt tại trang chào mừng hoặc màn đen, không tải được video.

---

## 2. Các Lỗ Hổng Tường Lửa RouterOS Khiến TikTok Lọt Ra IP Gốc

### A. Lỗ hổng QUIC (UDP 443) & DNS Leak (UDP 53)
- TTNet tự động chuyển sang giao thức HTTP/3 QUIC (UDP 443) bypass qua Default Gateway khi HTTP Proxy bị nghẽn.
- **Giải pháp:** Bắt buộc có rule DROP cứng cả UDP 443 và UDP 53 đối với dải mạng Farm `192.168.0.0/16`:
  ```routeros
  /ip firewall filter add chain=forward protocol=udp dst-port=443 src-address=192.168.0.0/16 action=drop comment="KILLSWITCH_BLOCK_QUIC_UDP_443"
  /ip firewall filter add chain=forward protocol=udp dst-port=53 src-address=192.168.0.0/16 action=drop comment="KILLSWITCH_FARM_DNS_UDP"
  ```

### B. Lỗ hổng Mangle Prerouting Bypass
- Bảng Mangle chạy trước Filter Forward. Nếu các rule Mangle gắn `mark-routing=WANx` cho máy farm, gói tin bị ném ra interface PPPoE trước khi rule Filter kịp drop.
- Gói tin gửi tới các cổng DNAT (`20001-20080` cho Kibe, `20201-20280` cho Admin) **BẮT BUỘC PHẢI ACCEPT Ở TOP [0] MANGLE**:
  ```routeros
  /ip firewall mangle add chain=prerouting action=accept protocol=tcp dst-port=20001-20080 comment="BYPASS_MANGLE_FOR_KIBE_MOBIPROXY_DNAT"
  /ip firewall mangle add chain=prerouting action=accept protocol=tcp dst-port=20201-20280 comment="BYPASS_MANGLE_FOR_ADMIN_R3G_DNAT"
  ```

### C. Lỗ hổng Chặn Nhầm Proxy Ports Nội Bộ (Sự cố M205, M207)
- Rule mở cổng proxy nội bộ (`ALLOW_FPT_LAN_PROXY_PORTS` dst-port=10001-10035,20001-20280) nếu đặt `src-address-list=FPT_LAN` mà dải `192.168.110.0/24` bị disable trong list thì toàn bộ máy farm truy cập vào cổng proxy cục bộ sẽ bị rơi vào rule DROP bên dưới.
- **Quy chuẩn:** Đặt trực tiếp `src-address=192.168.110.0/24` vào rule Filter Forward thay vì phụ thuộc address-list lỏng lẻo.

---

## 3. Quy Trình Khôi Phục PPPoE Trên Box MobiProxy & R3G
- Khi xoay IP (reconnect) trên 1 cổng LAN vật lý quay đa phiên PPPoE:
  - Nếu gửi lệnh xoay dồn dập, trạm BRAS Viettel sẽ treo session cũ (`stuck session`), dẫn đến box không nhận được IPv4 Public mới.
  - Phải để thời gian nghỉ (cooldown 2-3 phút) trước khi retry, hoặc khởi động lại modem Viettel để nhả phiên.
