# Asymmetric Routing Trap & Direct WAN Tinyproxy Bind Hazard

## 1. Hiện Tượng & Bẫy Kỹ Thuật (Incident 2026-10-31)
Khi chuyển router OpenWrt (Xiaomi R3G) từ mô hình VPN Tailscale nội bộ sang **Direct WAN (truy cập proxy trực tiếp qua IP Public WAN)**:
- **Hiện tượng:**
  * Client ngoài Internet (IP trong Whitelist) gửi request TCP SYN tới IP WAN của router trên cổng proxy `5151` $\to$ Gói tin đến được router và firewall đã ACCEPT (bộ đếm packet tăng).
  * Nhưng client bị lỗi `Tunnel connection failed: 403 Access denied` hoặc `Connection timed out` (không nhận được gói SYN-ACK phản hồi).
- **Nguyên nhân kép:**
  1. **Lỗi ACL của Tinyproxy (`403 Access denied`):**
     * Trong file config Tinyproxy (`tp_51xx.conf`), mặc định chỉ có:
       ```
       Allow 127.0.0.1
       Allow 100.64.0.0/10
       Allow 192.168.0.0/16
       ```
     * Khi truy cập từ ngoài Internet qua WAN IP, IP nguồn là IP Public của client (ví dụ `116.110.x.x` hoặc `1.52.x.x`), Tinyproxy thấy không nằm trong ACL nên trả về ngay `HTTP 403 Forbidden / Access Denied`.
  2. **Bẫy Định Tuyến Bất Đối Xứng Do Chỉ Thị `Bind` (`Connection Timed Out`):**
     * Trong config Tinyproxy có dòng: `Bind <ip_addr_pppoe>`.
     * Khi có chỉ thị `Bind <ip_addr>`, socket outbound/inbound của Tinyproxy bị ép gắn chặt vào IP của interface PPPoE đó.
     * Khi client từ ngoài kết nối vào IP WAN chính (`pppoe-wan`), nhưng gói phản hồi của Tinyproxy lại bị policy routing (`from <ip_addr> lookup <tbl>`) định tuyến qua interface khác hoặc bị drop do reverse path filtering (rp_filter) $\to$ **Asymmetric routing**.
     * Hậu quả: Gói tin phản hồi không bao giờ quay lại được client, dẫn tới timeout.

## 2. Giải Pháp Chuẩn Hóa
1. **Bỏ chỉ thị `Bind` cứng trong Tinyproxy:**
   - Trong script sinh config (`generate_all_proxies.sh`): Comment dòng `Bind $ip_addr` $\to$ `#Bind $ip_addr`.
   - Để Tinyproxy tự do bind socket theo định tuyến của kernel, việc phân line PPPoE dựa vào `ip rule` và bảng routing riêng (`lookup $tbl`) thay vì ép socket bind.
2. **Bổ sung Dải IP Client vào ACL của Tinyproxy:**
   - Cần thêm dải IP của cụm client farm (MikroTik Đà Nẵng, IP PC quản trị) vào danh sách `Allow` của Tinyproxy:
     ```
     Allow 116.110.0.0/16
     Allow 171.231.0.0/16
     Allow 1.52.0.0/16
     ```
3. **Đồng bộ Whitelist Firewall (Kernel) và ACL (Application):**
   - Firewall OpenWrt (`iptables / fw3`): Drop toàn bộ traffic quét port từ botnet Internet, chỉ cho phép dải IP client vào cổng `5141..5158`.
   - Tinyproxy ACL: Allow các dải IP client tương ứng để tránh trả 403.
   - Nhờ đó, router vừa được bảo vệ an toàn tuyệt đối chống scan, vừa phản hồi HTTP proxy cực nhanh (< 800ms) mà không bị kẹt asymmetric routing.
