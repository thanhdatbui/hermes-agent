# Direct WAN Whitelisting: Subnet /16 vs Single IP Trap & ISP Dynamic Pool Architecture

## 1. Bản Chất Bài Toán Whitelist Chống Scan (Scan Guard)

Khi mở Direct WAN cho proxy node (như Xiaomi R3G hay MobiProxy) để client từ xa (MikroTik Farm, Host Controller) kết nối vào, firewall bắt buộc phải có cơ chế **Anti-Scan (Scan Guard)** để DROP botnet/crawlers trên Internet.

Có 2 mô hình thi công với sự khác biệt cốt lõi:

| Tiêu chí | Mô hình Single IP (MobiProxy GUI) | Mô hình Subnet /16 (OpenWrt iptables Direct) |
|---|---|---|
| **Cơ chế nạp** | Nhập từng IP đơn lẻ (`116.110.212.30`) qua form web | Nạp trực tiếp cả dải CIDR (`116.110.0.0/16`) vào firewall |
| **Độ nhạy IP đổi** | Cực cao: đổi IP là đứt kết nối ngay lập tức | Miễn dịch: IP đổi trong dải ISP vẫn thông luồng 100% |
| **Phụ thuộc Cron** | BẮT BUỘC có cron poll 5 phút gọi API update IP | KHÔNG CẦN cron cập nhật liên tục |
| **Rủi ro rớt mạng** | Có độ trễ 0-5 phút gián đoạn trước khi cron chạy | Zero downtime khi PPPoE quay số đổi IP |

---

## 2. Cái Bẫy "Dải IP ISP Đa Đầu Số" (ISP Dynamic Pool Trap)

### A. Triệu chứng & Sai lầm phổ biến
- Agent/Coordinator thường ngộ nhận: *"Viettel Đà Nẵng chỉ có 1 đầu số (ví dụ 116.110.x.x)"*.
- Hậu quả: Khi cấu hình firewall chỉ whitelist `116.110.0.0/16`, ngày hôm sau router MikroTik hoặc modem quay số đổi sang đầu số khác (ví dụ `116.99.x.x`, `171.231.x.x`, `27.79.x.x`) ➔ **Toàn bộ kết nối sang node bị firewall DROP thẳng cánh**, gây sập farm hàng loạt máy.

### B. Kiểm chứng thực tế từ router cấp nguồn (MikroTik 35 line)
Khi kiểm tra bảng địa chỉ của 35 line PPPoE trên MikroTik Đà Nẵng:
```
Unique /16 prefixes: ['116.110', '116.99', '171.231', '27.79']
```
Nhà mạng Viettel tại cùng 1 khu vực thực tế luân chuyển giữa **4 block /16 hoàn toàn khác nhau**:
1. `116.110.0.0/16`
2. `116.99.0.0/16`
3. `171.231.0.0/16`
4. `27.79.0.0/16`
Cộng với dải FPT/Viettel tại máy điều khiển Kibe: `1.52.0.0/16`, `1.53.0.0/16`.

---

## 3. Kiến Trúc Cấu Hình Chuẩn Trên OpenWrt (UCI Firewall)

### A. Quy tắc khai báo UCI
Khai báo đầy đủ toàn bộ các block `/16` đã khảo sát vào `src_ip`:
```sh
uci set firewall.allow_proxies_wan=rule
uci set firewall.allow_proxies_wan.name='Allow-Proxies-WAN-Whitelist'
uci set firewall.allow_proxies_wan.src='wan'
uci set firewall.allow_proxies_wan.proto='tcp'
uci set firewall.allow_proxies_wan.dest_port='5141 5142 5143 5144 5145 5146 5147 5148 5151 5152 5153 5154 5155 5156 5157 5158'
uci set firewall.allow_proxies_wan.src_ip='116.110.0.0/16 116.99.0.0/16 171.231.0.0/16 27.79.0.0/16 1.52.0.0/16 1.53.0.0/16'
uci set firewall.allow_proxies_wan.target='ACCEPT'
uci commit firewall
/etc/init.d/firewall reload
```

### B. Tinyproxy config tương ứng
Trong file cấu hình tinyproxy (`/etc/tinyproxy/instances/tp_*.conf`), các dải trên cũng phải được `Allow`:
```conf
Allow 127.0.0.1
Allow 100.64.0.0/10
Allow 192.168.0.0/16
Allow 116.110.0.0/16
Allow 116.99.0.0/16
Allow 171.231.0.0/16
Allow 27.79.0.0/16
Allow 1.52.0.0/16
Allow 1.53.0.0/16
```

### C. Quy tắc vận hành (Checklist)
1. Trước khi whitelist theo subnet, **bắt buộc query trực tiếp router nguồn (MikroTik / modem)** để lấy danh sách distinct prefixes hiện hữu. CẤM tự ý đoán 1 đầu số đại diện.
2. Với mô hình OpenWrt Direct WAN Subnet Whitelist: **KHÔNG CẦN cronjob gọi API đổi IP mỗi 5 phút**. Tường lửa hoạt động tĩnh, O(1), tự động đón đúng toàn bộ các lần IP rotation của farm nguồn.

---

## 4. Đánh Giá Rủi Ro Bảo Mật: Whitelist Subnet /16 Có Bị Phá Không?

- **Mối lo ngại:** Mở whitelist hơn 400.000 IP (4 block `/16` của ISP), liệu người dùng khác trong cùng dải mạng có chui vào router phá hoại được không?
- **Phân tích ranh giới bảo vệ (Blast Radius):**
  1. **Cổng quản trị router (SSH 22, LuCI 80/443) đóng 100% trên WAN:** Tường lửa chỉ mở quản trị duy nhất qua interface `tailscale0`. Người ngoài cùng dải mạng Viettel không có cách nào chạm tới shell hay web cấu hình.
  2. **Cổng mở chỉ là proxy trung gian (L7 HTTP/SOCKS):** 16 cổng proxy chỉ có chức năng forward web traffic ra các interface PPPoE động. Chúng không có quyền thực thi lệnh (command execution), không có shell, không thể truy cập tài nguyên nội bộ mạng LAN farm.
  3. **Đặc tính ẩn danh của IP động R3G:** Kẻ muốn dùng ké proxy bắt buộc phải biết chính xác IP WAN động hiện tại của router ở Thái Bình (`117.5.x.x`) và đúng dải port `5141..5158`. IP này thay đổi sau mỗi chu kỳ quay số.
  4. **Kết luận:** Whitelist subnet `/16` cho proxy port là hoàn toàn an toàn, vừa loại bỏ 100% botnet toàn cầu vừa đảm bảo zero-downtime khi router nguồn đổi IP.
