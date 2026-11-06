# Fail-Closed Multi-Tier Verification & Filter Whitelist Trap (2026-11-06)

## 1. Bối Cảnh Thực Tế & Lỗ Hổng Kiến Trúc Đã Bị Bắt Bài
Trong quá trình cô lập rò rỉ IP Direct WAN cho farm:
1. **Lỗ hổng Chặn Nhầm Port Proxy Nội Bộ (Filter Whitelist Trap):**
   - Khi siết chặt an toàn bằng cách disable IP LAN `192.168.110.0/24` khỏi address-list `FPT_LAN` để chống leak mạng ngoài.
   - Nhưng quy tắc Filter `ALLOW_FPT_LAN_PROXY_PORTS` (cổng `10001-10035, 20001-20280`) lại dùng `src-address-list=FPT_LAN`.
   - Hậu quả: Toàn bộ 48 máy kênh chính Admin (`10008..10035`) khi gửi request vào chính router MikroTik bị rớt xuống rule `DROP_EXTERNAL_PROXY_PORTS` ở dưới, làm toàn bộ các máy lành (M205, M207...) mất sạch mạng proxy.
   - **Khắc phục:** Tách bạch rạch ròi: Rule cho phép truy cập proxy nội bộ phải gán cứng `src-address=192.168.110.0/24` độc lập, không dùng chung address-list với các rule cho phép ra ngoài WAN.

2. **Cạm Bẫy Đánh Đồng Dấu Chấm Than Wi-Fi với Rớt Mạng TikTok:**
   - Cột sóng Wi-Fi Android không hiện dấu chấm than (`!`) KHÔNG đồng nghĩa với việc app TikTok có mạng.
   - Android kiểm tra captive portal qua URL `generate_204` của Google; trong khi TikTok chạy engine mạng riêng (`TTNet / OkHttp`).
   - Ngược lại: Khi Wi-Fi hiện dấu chấm than, TikTok vẫn có thể lướt tiếp 1-3 video nếu trong RAM/ROM còn video cache nạp sẵn từ phiên trước.
   - **Quy chuẩn đối soát bắt buộc:** Muốn kiểm tra máy thật sự mất mạng hay chưa:
     * Bắt buộc `am force-stop` dập tắt app hoàn toàn để xóa cache bộ nhớ tạm.
     * Mở lại app ở chế độ Cold-Boot (`am start`).
     * Kiểm tra UI: Nếu app kẹt ở màn hình chào mừng / Skeleton loading cards và `netstat` kẹt ở `SYN_SENT` -> Mới là bằng chứng bất khả xâm phạm chứng minh Fail-Closed hoạt động.

3. **Mangle Bypass Bắt Buộc Cho Cả Hai Cụm Farm:**
   - RouterOS duyệt Mangle Prerouting trước Filter Forward.
   - Khi có nhiều line WAN (35 PPPoE), nếu thiếu rule Bypass `accept` ở vị trí [0] cho dải port proxy nội bộ (`20001-20080` của Kibe và `20201-20280` của Admin):
   - Mangle sẽ tự động gắn routing-mark (`WAN8..WAN35`) làm lệch luồng phản hồi của Kernel DNAT, gây timeout kết nối.
