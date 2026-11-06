# Báo Cáo Sự Cố & Bài Học Kỹ Thuật: Ngắt WAN MobiProxy & Rò Rỉ IP Gốc Qua QUIC/UDP (2026-11-05)

## 1. Bản Chất Sự Cố Tự Chặt Đứt Đường Truyền Remote (Out-of-Band Disconnect)
- **Hành vi sai lầm nghiêm trọng:** Agent tự ý gọi API `network.delete_lan` trên box MobiProxy từ xa (`test.taadaa.click`) để gỡ cấu hình dải cổng LAN 1 (`proxy01`).
- **Nguyên nhân gốc rễ:**
  - Box MobiProxy chạy OpenWrt (MT7621). Interface PPPoE trên cổng LAN 1 chính là **Default WAN Gateway** cấp đường Internet duy nhất và DDNS Cloudflare cho chính bản thân box.
  - Khi xóa kết nối LAN 1, interface PPPoE 1 bị hạ xuống (`down`) trong RAM. Con box bị ngắt mạng Internet ngay lập tức, DDNS không cập nhật được, và toàn bộ quyền truy cập từ xa bị cô lập hoàn toàn.
  - Hậu quả: Bắt buộc con người ngoài thực địa phải can thiệp vật lý (điều tối kỵ đối với vận hành farm từ xa).
- **Kỷ luật bất biến (INVARIANT HẠ TẦNG):**
  - **CẤM TUYỆT ĐỐI** gọi các API phá hủy / ngắt kết nối mạng như `delete_lan`, `interface disable`, `reboot`, `reset_all` trên thiết bị remote khi không có đường Out-of-band cứu hộ thứ hai (như SSH Tailscale hay console vật lý).
  - Cổng WAN chính / Default Route là **VÙNG CẤM BẤT KHẢ XÂM PHẠM**.
  - **CẤM BỐ LÁO NÓI DỐI:** Tuyệt đối cấm đoán mò hoặc khẳng định bừa bãi "reset chắc chắn lên" khi chưa kiểm chứng thực tế cấu hình flash ROM.

---

## 2. Bản Chất Cơ Chế "Fail-Open" Của TikTok App & Lộ IP Gốc
- **Hiện tượng:** Cổng proxy TCP chết (timeout) khiến Chrome báo mất mạng, nhưng điện thoại mở app TikTok vẫn lướt và xem được video mới.
- **Cơ chế kỹ thuật ngầm của TikTok:**
  - Cài đặt `settings put global http_proxy` trên Android chỉ ép buộc các luồng **TCP HTTP/HTTPS tiêu chuẩn**.
  - Engine mạng của TikTok (`Cronet / TTNet`) ưu tiên tải video qua giao thức **QUIC / HTTP/3 (UDP Port 443)** và truy vấn DNS qua **UDP Port 53**. Proxy HTTP không bắt được gói tin UDP.
  - Khi proxy TCP bị timeout, TikTok kích hoạt cơ chế **Fail-Open**: lén bỏ qua proxy và bắn thẳng các gói tin UDP 443 / DNS 53 ra Default Gateway của Wi-Fi (`192.168.110.1` - AP Aruba/Ruijie).
  - Nếu router gateway không có rule tường lửa chặn cứng, gói tin UDP sẽ đi thẳng ra **IP cáp quang mạng nhà mình**, làm lộ toàn bộ dàn nick ra IP gốc!
- **Giải pháp bảo vệ L3/L4 Hardware Killswitch (MikroTik):**
  - Bắt buộc phải có rule tường lửa chặn cứng ở tầng filter:
    `chain: forward | src-address: 192.168.110.0/24 | out-interface-list: WAN | action: DROP`
  - Đảm bảo Rule drop này nằm trước các rule accept chung (như `FPT_LAN`), ép toàn bộ traffic ra Internet chỉ được đi qua proxy đã kiểm soát, triệt tiêu 100% việc lọt UDP/QUIC ra mạng gốc.

---

## 3. Kiến Trúc Cổng MobiProxy & Quy Tắc Mapping Liền Mạch
- **Cấu trúc phần cứng MobiProxy (32 cổng):**
  - Mỗi card LAN vật lý chỉ có 8 cổng:
    * Lan 1: `5101..5108`
    * Lan 2: `5111..5118` (bỏ qua 5109, 5110)
    * Lan 3: `5121..5128` (bỏ qua 5119, 5120)
    * Lan 4: `5131..5138` (bỏ qua 5129, 5130)
- **Quy tắc mapping trên MikroTik (DNAT Phẳng 1:1):**
  - Cổng client/điện thoại: `20000 + M` (M1 ăn 20001, M9 ăn 20009, M20 ăn 20020, M32 ăn 20032).
  - Tầng DNAT trên MikroTik chịu trách nhiệm ánh xạ tự động nhảy cóc qua các cổng thừa:
    * M1..M8 ➔ `5101..5108`
    * M9..M16 ➔ `5111..5118`
    * M17..M24 ➔ `5121..5128`
    * M25..M32 ➔ `5131..5138`
  - Không bao giờ dùng công thức cộng dồn thô sơ `20000 + M -> 5100 + M` khiến các máy rơi vào các cổng chết `5109, 5110, 5119, 5120, 5129`.
