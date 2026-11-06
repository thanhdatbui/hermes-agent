# Fail-Closed vs App Fallback Leak & Screen Off Verification Discipline (2026-11-06)

## 1. Bối Cảnh & Sự Cố Thực Tế
Trong phiên vận hành chuyển đổi Kernel DNAT cho dàn máy Farm (80 máy Kibe sang MobiProxy và 32 máy Admin non sang R3G), hệ thống đối mặt 2 sai lầm nghiêm trọng của Coordinator:
1. **Ảo giác kiểm chứng thị giác do Màn hình Điện thoại bị tắt (Display Power: OFF):** Khi chụp ảnh màn hình qua ADB `screencap` trong lúc máy S7 đã rơi vào trạng thái ngủ/tắt màn hình, framebuffer trả về mảng toàn bộ pixel đen kịt (`RGB = [0, 0, 0]`). Coordinator không kiểm tra pixel thật hoặc OCR mà đã vội vàng bịa đặt mô tả ("màn hình hiển thị số IP to rõ...", "trình duyệt báo lỗi...") và gửi `MEDIA:`, vi phạm nghiêm trọng Invariant chống ảo giác thị giác.
2. **Ảo tưởng Fail-Closed khi Proxy sập (Cạm bẫy App TTNet / QUIC Fallback):** Khi giả lập proxy sập (ngắt port hoặc trỏ sang IP chết), trình duyệt Web thuần HTTP (Chrome/Samsung Internet) báo lỗi `ERR_CONNECTION_REFUSED` / `ERR_EMPTY_RESPONSE`, nhưng **App TikTok vẫn lướt video ầm ầm**.
   - Nguyên nhân 1: Video Cache của TikTok đã preload sẵn 3-5 video vào RAM/ROM. CẤM clear cache ứng dụng bừa bãi khi user yêu cầu kiểm tra!
   - Nguyên nhân 2 (Chí mạng): Khi HTTP Proxy không phản hồi, SDK mạng của ByteDance (TTNet) tự động fallback lách qua giao thức UDP (QUIC trên cổng 443) hoặc gửi request thẳng ra Default Gateway. Do tường lửa MikroTik lúc đó chỉ có rule drop cho dải `192.168.110.0/24` (Kibe) mà THIẾU rule drop dải `192.168.10.0/24` (Admin), thiết bị đã tự động lách proxy đi thẳng ra Internet bằng IP gốc Viettel Đà Nẵng!

---

## 2. Kỷ Luật Kiểm Chứng Màn Hình Sáng Trước Khi Screencap
CẤM TUYỆT ĐỐI gửi bất kỳ thẻ `MEDIA:<path>` nào khi chưa kiểm tra 2 điều kiện cứng:
1. **Bật sáng màn hình cơ học:**
   ```bash
   adb shell "input keyevent 224 && input keyevent 82 && svc power stayon true && settings put system screen_off_timeout 600000"
   ```
2. **Kiểm tra Pixel mảng màu (Anti-Black Screen Guard):**
   Trích xuất dữ liệu thô và kiểm tra xem có phải toàn màu đen không:
   ```python
   import numpy as np
   from PIL import Image

   img = Image.open('screenshot.png')
   r, g, b = img.split()[:3]
   is_black = (
       len(np.unique(r)) == 1
       and np.unique(r)[0] == 0
       and len(np.unique(g)) == 1
       and np.unique(g)[0] == 0
       and len(np.unique(b)) == 1
       and np.unique(b)[0] == 0
   )
   if is_black:
       raise RuntimeError(
           'SCREEN IS BLACK (Display Power OFF). DO NOT SEND MEDIA!'
       )
```
3. **Đọc Ground Truth bằng Native Vision / WinRT OCR:** BẮT BUỘC trích xuất chính xác text hiển thị thực tế (bằng chứng thật) trước khi kết luận trạng thái. CẤM gửi đối phó hoặc bịa đặt mô tả khi chưa nhìn thấy pixel thật.

---

## 3. Kiến Trúc Khóa Cơ Học Fail-Closed Chống Rò Rỉ IP Gốc (Trio Killswitch)
Để đảm bảo khi proxy sập, toàn bộ ứng dụng (bao gồm TikTok, trình duyệt, app nền) BẮT BUỘC PHẢI MẤT MẠNG 100%, tuyệt đối không được phép lách ra ngoài:
1. **Rule 1: Khóa cứng toàn bộ dải IP Farm không được đi thẳng ra WAN:**
   - Dải Kibe: `/ip firewall filter add chain=forward src-address=192.168.110.0/24 action=drop comment="KILLSWITCH_BLOCK_FARM_DIRECT_WAN"`
   - Dải Admin: `/ip firewall filter add chain=forward src-address=192.168.10.0/24 action=drop comment="KILLSWITCH_DROP_ADMIN_DIRECT_WAN"`
2. **Rule 2: Khóa cổng UDP 443 (Chặn đứng giao thức QUIC lách proxy):**
   - `/ip firewall filter add chain=forward protocol=udp dst-port=443 action=drop comment="KILLSWITCH_FARM_QUIC_UDP"`
3. **Rule 3: Khóa cổng DNS UDP 53 đi thẳng ra ngoài (Chống DNS Leak):**
   - `/ip firewall filter add chain=forward protocol=udp dst-port=53 action=drop comment="KILLSWITCH_FARM_DNS_UDP"`

---

## 4. Kỷ Luật Định Tuyến Kernel DNAT & Mangle Bypass Cho Multi-WAN
Khi MikroTik có nhiều line PPPoE (ví dụ 35 line WAN) và chạy Policy-Based Routing (PBR / Mangle):
- Các gói tin từ điện thoại Farm gửi tới các port proxy DNAT (`20201..20280`) BẮT BUỘC phải được bypass khỏi bảng Mangle ép WAN:
  ```routeros
  /ip firewall mangle
  add chain=prerouting dst-port=20201-20280 protocol=tcp action=accept comment="BYPASS_MANGLE_FOR_ADMIN_R3G_DNAT"
  # Di chuyển rule này lên vị trí đầu tiên (Top #0) của bảng Mangle
  move destination=*2 numbers=[find comment="BYPASS_MANGLE_FOR_ADMIN_R3G_DNAT"]
  ```
- Nếu không có rule Accept ở đầu bảng, gói tin sẽ bị Mangle ép ra các cổng `WAN8..WAN35`, trong khi router đích ở xa chỉ mở Whitelist và route trả về khớp với `WAN1`, gây ra hiện tượng gãy kết nối hai chiều (Asymmetric Routing), điện thoại mất mạng và hiện dấu chấm than trên Wi-Fi.
