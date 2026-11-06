---
name: mobiproxy-ops-and-hardware-wan-killswitch
description: "Vận hành an toàn MobiProxy 4G Thái Bình, bẫy ngắt WAN cổng 1, cơ chế QUIC/UDP leak trên TikTok và L3/L4 Quad-Lock Killswitch."
version: 1.0.0
---
# MobiProxy Operations & Hardware WAN Kill-Switch Governance

## 1. Bản Chất Sự Cố Mất Kết Nối MobiProxy Thái Bình (Root Cause)
- **Bối cảnh:** MobiProxy (`test.taadaa.click`) quản trị 32 modem 4G phân bổ trên 4 card LAN vật lý. Cấu hình phân bổ gốc: `lan1: 10, lan2: 10, lan3: 10, lan4: 8`, trong đó mỗi LAN thực tế chỉ cắm 8 modem, dẫn đến 2 cổng đuôi mỗi LAN bị rỗng (`5109-5110`, `5119-5120`, `5129-5130`).
- **Sai lầm chết người:**
  - Để dọn dẹp và gom về `8 - 8 - 8 - 8`, Coordinator tự ý gọi API `network.delete_lan` cho cả 4 LAN (`4, 3, 2, 1`).
  - **Điểm mù tai hại:** Cổng `proxy01` (LAN 1) chính là **đường cấp IP Internet WAN cho chính bản thân con box và là interface cập nhật Cloudflare DDNS**.
  - Khi xóa LAN 1, interface WAN 1 bị hạ (`down`) và chuyển sang `disabled` trong RAM của OpenWrt. Con box lập tức mất kết nối Internet, cắt đứt hoàn toàn phiên API từ xa, cô lập con box và buộc phải can thiệp vật lý tại chỗ.

## 2. Invariant Cốt Lõi: CẤM ĐỤNG VÀO DEFAULT WAN TRÊN THIẾT BỊ REMOTE (Mechanical Gate)
- **VÙNG CẤM TUYỆT ĐỐI:**
  1. Tuyệt đối CẤM gọi `network.delete_lan` đối với LAN 1 hoặc bất kỳ lệnh nào hạ interface default gateway của router/box điều khiển từ xa.
  2. Mọi thao tác cấu hình lại dải cổng MobiProxy **chỉ được phép thực hiện khi có kết nối nội bộ hoặc đường quản trị out-of-band dự phòng**, CẤM thực hiện qua đường WAN duy nhất.
  3. CẤM Coordinator tự ý suy diễn gọi các lệnh phá hủy/tắt mạng mà không có sự phê duyệt tường minh (Action Mandate) từ User.

## 3. Bản Chất Hiện Tượng TikTok Lướt Được Dù Proxy Mất (QUIC/UDP Leak Trap)
- **Hiện tượng:** Cài đặt proxy Android (`settings put global http_proxy 192.168.110.2:20001`) chỉ ép các luồng **TCP HTTP/HTTPS chuẩn** (Chrome, API thông thường).
- **Cơ chế Fail-Open nguy hiểm của TikTok (`Cronet / TTNet Engine`):**
  - TikTok app ưu tiên truyền dữ liệu video qua **QUIC / HTTP/3 (UDP port 443)** và truy vấn DNS qua **UDP port 53**.
  - Proxy Android TCP thông thường **hoàn toàn KHÔNG bắt được gói tin UDP**.
  - Khi proxy TCP chết hoặc timeout, TTNet tự động bỏ qua proxy và bắn thẳng các gói tin UDP 443 ra Default Gateway (`192.168.110.1` của AP Aruba/Ruijie).
  - Nếu router không chặn cứng ở Layer 3/4, toàn bộ video TikTok sẽ chạy thẳng bằng **IP cáp quang mạng gốc (`113.23.110.227`)**, gây cháy nick hàng loạt.

## 4. Giải Pháp Bộ Tứ Phòng Thủ (L3/L4 Quad-Lock Killswitch Trên MikroTik)
Để chống rò rỉ IP gốc ra ngoài khi proxy sập, bắt buộc phải có rule tường lửa chặn cứng tại Router MikroTik:
```text
/ip firewall filter
add chain=forward src-address=192.168.110.0/24 out-interface-list=WAN action=drop comment="KILLSWITCH_BLOCK_FARM_DIRECT_WAN"
```
- **Nguyên tắc Fail-Closed:** Khi proxy chết, toàn bộ traffic từ dàn điện thoại Kibe (`192.168.110.0/24`) đi ra WAN đều bị router drop 100%, điện thoại mất mạng hoàn toàn thay vì lén lút ăn vào IP mạng gốc.
- **Tạm dừng khẩn cấp:** Khi trạm proxy chết, lập tức kích hoạt `am force-stop com.ss.android.ugc.trill` trên toàn bộ dàn máy và pause toàn bộ cronjob nuôi/2FA để bảo vệ tài sản nick.
