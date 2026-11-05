---
name: routeros-mangle-bypass-and-dnat-discipline
description: Kỷ luật cấu hình Kernel DNAT trên MikroTik RouterOS kết hợp Mangle Bypass và OpenWrt Policy Routing cho Farm.
version: 1.0.0
---
# RouterOS Mangle Bypass, Kernel DNAT & Multi-WAN Routing Discipline

## 1. Bản chất xung đột giữa Mangle PBR và Kernel DNAT trên MikroTik
- Khi RouterOS áp dụng Policy-Based Routing (Mangle `mark-routing`) để ép cố định từng dải IP điện thoại farm (ví dụ `192.168.10.x`) đi ra các đường WAN vật lý riêng lẻ (ví dụ `WAN8..WAN35`):
  - Mọi gói tin từ điện thoại gửi tới các cổng proxy nội bộ (`20201..20280`) sẽ bị bảng Mangle bắt và đóng dấu routing-mark của WAN phụ đó.
  - Khi router thực hiện DNAT sang router đầu xa (ví dụ Xiaomi R3G ở Thái Bình), gói tin bị đẩy ra ngoài bằng IP của WAN phụ thay vì WAN chính (`pppoe-out1`).
  - Nếu router đầu xa chỉ cấu hình Whitelist và bảng route phản hồi cho WAN chính, toàn bộ gói tin trả lời sẽ bị rớt hoặc lệch luồng (Asymmetric Routing), dẫn đến việc điện thoại bị mất mạng và xuất hiện dấu chấm than (!) trên biểu tượng Wi-Fi (`ERR_CONNECTION_REFUSED` / `ERR_EMPTY_RESPONSE`).

## 2. Giải pháp cơ học O(1) trên MikroTik RouterOS

### Bước 1: Mangle Bypass Rule (Đặt tại TOP #0)
Để gói tin tới các cổng proxy không bị các rule Mangle phía sau gắn cờ ép đường mạng, nạp rule `action=accept` và đẩy lên đầu bảng Mangle Prerouting:
```routeros
/ip firewall mangle add chain=prerouting protocol=tcp dst-port=20201-20280 action=accept comment="BYPASS_MANGLE_FOR_ADMIN_R3G_DNAT" place-before=0
```

### Bước 2: Kích hoạt đầy đủ tham số cho Rule DNAT
Khi nạp rule DNAT qua REST API hoặc CLI, BẮT BUỘC phải chỉ định rõ `action=dst-nat`:
```routeros
/ip firewall nat add chain=dstnat protocol=tcp dst-port=20203 action=dst-nat to-addresses=116.107.127.118 to-ports=5141 comment="DNAT_ADMIN_M203_TO_R3G_5141"
```
Và bắt buộc đẩy tất cả các rule DNAT này lên đứng trước rule gom Singbox `*30E` (`/ip firewall nat move`).

## 3. Cấu hình định tuyến hai chiều và Whitelist trên OpenWrt đầu xa (R3G)
- **Ép tuyến phản hồi (Return Path Routing):**
  R3G quay đa phiên nhiều PPPoE con. Phải ép toàn bộ gói tin gửi về subnet Viettel của MikroTik đi ra đúng cổng WAN cáp quang chính (`table 200` / `pppoe-wan`):
  ```sh
  ip rule add to 171.231.0.0/16 table 200 priority 5001
  ip rule add to 116.110.0.0/16 table 200 priority 5002
  ip rule add to 116.99.0.0/16 table 200 priority 5003
  ip rule add to 27.79.0.0/16 table 200 priority 5004
  ```
- **Mở rộng dải Firewall Whitelist:**
  Mở toàn bộ subnet Viettel của MikroTik trong `/etc/config/firewall`, cấm chỉ mở 1 IP đơn lẻ vì IP WAN quay PPPoE sẽ tự động thay đổi định kỳ.

## 4. Chống bẫy ảnh đen khi chụp kiểm chứng Android (Screen-Off Trap)
- Lệnh `screencap` trên Android khi màn hình tắt (`Display Power: state=OFF`) vẫn tạo ra file ảnh nhưng pixel hoàn toàn là số 0 (RGB=0, ảnh đen sì).
- Trước khi chụp ảnh nghiệm thu Gate 6, BẮT BUỘC:
  1. Đánh thức và mở khóa: `input keyevent 224 && input keyevent 82 && svc power stayon true`.
  2. Kiểm tra `dumpsys power | grep "Display Power"` phải là `state=ON`.
  3. Kiểm chứng nhanh bằng Python PIL/NumPy (`np.unique(r) > 1`) để loại trừ ảnh đen trước khi phát thẻ `MEDIA:`.
