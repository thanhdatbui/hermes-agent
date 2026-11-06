# Chi Tiết Sự Cố MobiProxy Cổng 1 & Lỗ Hổng TikTok Fail-Open UDP (2026-11-05)

## 1. Case Study: Sự Cố Ngắt Kết Nối MobiProxy Từ Xa
- **Hành vi sai phạm:** Coordinator tự động gọi API `network.delete_lan` xóa toàn bộ các LAN 4, 3, 2, 1 trên box `test.taadaa.click` để chuẩn bị cài lại dải cổng 8-8-8-8.
- **Hậu quả:** 
  Cổng `proxy01` (LAN 1) chính là đường PPPoE duy nhất cấp IP WAN Internet và chạy DDNS Cloudflare cho chính bản thân con box. Khi cổng này bị ngắt, box mất kết nối Internet ra ngoài, tên miền bị drop, toàn bộ quyền điều khiển từ xa bị cô lập hoàn toàn.
- **Bài học khắc cốt ghi tâm:**
  - Không bao giờ được ngắt đường truyền duy nhất nối ta với thiết bị remote khi không có kênh out-of-band dự phòng.
  - Cấm làm phiền con người ở thực địa.

## 2. Chi Tiết Lỗ Hổng Rò Rỉ IP Gốc App TikTok Qua QUIC UDP
- **Hiện tượng:**
  Proxy HTTP TCP (`192.168.110.2:20001`) chết ➔ Trình duyệt web (Chrome) mất mạng, nhưng App TikTok vẫn lướt video ầm ầm.
- **Kỹ thuật:**
  - Engine `TTNet / Cronet` của ByteDance dùng QUIC qua UDP 443. Khi TCP proxy timeout, nó tự động fallback gửi UDP 443 trực tiếp ra Gateway (`192.168.110.1`).
  - Gói tin đi thẳng ra IP WAN cáp quang nhà mình (`113.23.110.227`), làm lộ toàn bộ hoạt động của nick farm.
- **Cách khắc phục trên MikroTik RouterOS:**
  - Chuyển Rule Drop Direct WAN (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`) lên vị trí index 0 (Top của filter table).
  - Khóa chặt `out-interface-list=WAN` đối với toàn bộ IP nguồn `192.168.0.0/16`.
  - Tách dải IP farm ra khỏi nhóm `FPT_LAN` (vốn có quyền forward ra ngoài).
