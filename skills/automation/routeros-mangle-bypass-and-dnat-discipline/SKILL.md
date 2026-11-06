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

## 4. Kỷ Luật Kiểm Chứng Fail-Closed Thực Tế & Chống Gửi Ảnh Đen Kịt (Gate 6 Invariant)
- **Kỷ luật kiểm chứng ngắt mạng (Fail-Closed Verification):**
  - Khi User yêu cầu kiểm tra tính an toàn: "Proxy sập thì máy qua DNAT có mất mạng / mất Wi-Fi không?":
    - Phải test thật bằng cách tắt/chặn đúng cổng proxy phụ đang trỏ (hoặc bẻ `to-addresses` trên MikroTik sang IP dead-end tạm thời).
    - DUY TRÌ TRẠNG THÁI NGẮT MẠNG ĐÓ, mở trực tiếp App TikTok trên điện thoại S7 để chụp ảnh màn hình bằng chứng thực tế: xác nhận App báo "Không có kết nối mạng" / nút "Thử lại", Wi-Fi có dấu chấm than (!).
    - CẤM TUYỆT ĐỐI tự ý bật lại proxy trước khi chụp ảnh khiến app load được video rồi báo cáo sai lệch hiện trường! Chỉ sau khi thu thập bằng chứng đầy đủ và gửi User mới được phép khôi phục lại cổng proxy.
    - CẢNH BÁO BẪY PRELOAD CACHE TIKTOK: App TikTok luôn tải trước (preload) 3-5 video vào bộ nhớ tạm. Khi ngắt proxy ngang, người dùng quẹt tiếp vẫn thấy video phát từ cache. Bắt buộc test kết hợp trình duyệt web (`icanhazip.com` báo `ERR_CONNECTION_REFUSED`) và force-stop TikTok mở lại từ đầu (Cold Start) để triệt tiêu cache.
- **Invariant chống gửi ảnh đen kịt (Anti-Black-Screencap):**
  - Trước khi chụp ảnh màn hình Android: Bắt buộc bật sáng màn hình (`input keyevent 224 && svc power stayon true && settings put system screen_off_timeout 600000`) và xác nhận `Display Power: state=ON`.
  - Trước khi gửi thẻ `MEDIA:<path>`: Bắt buộc chạy kiểm tra pixel `np.unique` qua Python. Nếu phát hiện `len(np.unique(r)) == 1 and np.unique(r)[0] == 0` (ảnh đen sì 100%), CẤM TUYỆT ĐỐI GỬI MEDIA và cấm bịa đặt mô tả.
  - Sau khi xác nhận ảnh có nội dung thật, bắt buộc dùng Native Multimodal đọc chi tiết từng dòng chữ trên ảnh thật để đối soát trước khi gửi tin nhắn cho User.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
