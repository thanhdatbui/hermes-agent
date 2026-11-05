# Bóc Tách Kỹ Thuật: Cấu Trúc Phần Cứng MobiProxy (38 Slots vs 32 Modems) & Đồng Bộ SSOT MikroTik

## 1. Bản Chất Kiến Trúc Phần Cứng MobiProxy (`test.taadaa.click`)
- Trên box MobiProxy chạy OpenWrt, cấu hình cổng HTTPv4 mặc định xuất phát từ `base_port = 5101`.
- Phần mềm phân bổ proxy theo công thức slot: `port = base_port + (index - 1)`.
- Khi cấu hình phân bổ mạng mặc định là:
  ```json
  "legacy": {
    "lan1": 10,
    "lan2": 10,
    "lan3": 10,
    "lan4": 8
  }
  ```
  Thực tế các modem 4G vật lý cắm trên mainboard chỉ có **8 modem mỗi card LAN**, phân bố ở các slot:
  - **Lan 1:** 8 modem cắm ở slot `1..8` -> Cổng `5101..5108` (Slot 9, 10 bỏ trống -> Cổng `5109, 5110` là proxy ảo / không có modem).
  - **Lan 2:** 8 modem cắm ở slot `11..18` -> Cổng `5111..5118` (Slot 19, 20 bỏ trống -> Cổng `5119, 5120` là proxy ảo / không có modem).
  - **Lan 3:** 8 modem cắm ở slot `21..28` -> Cổng `5121..5128` (Slot 29, 30 bỏ trống -> Cổng `5129, 5130` là proxy ảo / không có modem).
  - **Lan 4:** 8 modem cắm ở slot `31..38` -> Cổng `5131..5138`.

## 2. Rủi Ro Khi Ép Đổi Cấu Hình Về 8-8-8-8 Trên Box
- Nếu dùng API `network.plan` ép chia lại `8, 8, 8, 8`:
  - Slot 9 & 10 sẽ bị ép gán cho Lan 2 (`5109, 5110`). Tuy nhiên trên bo mạch vật lý, slot 9 và 10 không có modem kết nối -> Gọi `proxy_getip` sẽ trả về `fail: proxy_false`.
  - Các modem thật của Lan 2 (đang cắm ở slot 11..18) sẽ bị đứt kết nối hoặc trôi cổng.
- **Quy tắc bất biến:** Giữ nguyên quy hoạch `10-10-10-8` trên box MobiProxy để bảo toàn 100% kết nối phần cứng.

## 3. Khắc Phục Lệch Dây Chuyền Trên Router MikroTik (`192.168.110.2`)
- **Sai lầm cũ:** Rule DNAT trên MikroTik dùng công thức tịnh tiến `dst-port 200xx -> to-ports (51xx = 200xx - 14900)`. Khi gặp các khe trống 9, 10, 19, 20, 29, 30, toàn bộ các máy phía sau bị trượt cổng hàng loạt (Cascade Port Drift), đẩy lưu lượng vào cổng ảo gây lỗi `ConsumerPreflightError`.
- **Bản vá chuẩn hóa DNAT:**
  - Máy 1..8: Cổng `20001..20008` -> `116.107.124.158:5101..5108`
  - Máy 9..16: Cổng `20009..20016` -> `116.107.124.158:5111..5118`
  - Máy 17..24: Cổng `20017..20024` -> `116.107.124.158:5121..5128`
  - Máy 25..32: Cổng `20025..20032` -> `116.107.124.158:5131..5138`
- **Khuyến nghị đồng bộ SSOT:**
  - Để tránh người vận hành hoặc agent nhầm lẫn 2 port thừa, trên file Excel `PROXYgandienthoai.xlsx` và bảng `machines` trong SQLite `farm_master.db`, chuẩn hóa địa chỉ proxy của Farm Kibe thành IP LAN nội bộ phẳng: `192.168.110.2:20001` đến `192.168.110.2:20032` (M tương ứng cổng 20000 + M). Mọi nghiệp vụ định tuyến và nhảy cóc cổng để Router MikroTik xử lý ngầm ở tầng Netfilter.
