---
name: farm-remote-network-safety-and-quic-killswitch
description: "Kỷ luật an toàn tuyệt đối khi can thiệp thiết bị mạng remote (MobiProxy/R3G/MikroTik) và kiến trúc chặn rò rỉ IP gốc TikTok qua giao thức UDP/QUIC."
---
# Farm Remote Network Safety & TikTok UDP/QUIC Anti-Leak Architecture

## 1. Kỷ Luật Can Thiệp Thiết Bị Mạng Remote (Out-of-band Boundary)
- **VÙNG CẤM TUYỆT ĐỐI:** CẤM Coordinator tự ý gửi API xóa mạng (`network.delete_lan`), reboot, reset router khi thiết bị chỉ có DUY NHẤT một kênh kết nối WAN/DDNS qua chính đường mạng đó.
- **CẤM LÀM PHIỀN CON NGƯỜI THỰC ĐỊA:** Bất kỳ thao tác nào có nguy cơ làm mất quyền điều khiển từ xa dẫn tới việc User phải nhờ người ở thực địa rút nguồn/cắm dây là THẤT BẠI NGHIÊM TRỌNG NHẤT về an toàn vận hành. Thao tác có rủi ro ngắt mạng bắt buộc phải lập Action Mandate xin phê duyệt.

## 2. Bản Chất Cơ Chế Lộ IP Gốc Của App TikTok (Fail-Open UDP/QUIC)
- Cài đặt proxy Android thông thường (`http_proxy`) chỉ ép các luồng **TCP HTTP/HTTPS**.
- App TikTok chạy engine `TTNet / Cronet`. Khi proxy TCP bị timeout, nó kích hoạt **Fail-Open**: tự động bỏ qua proxy và bắn thẳng các gói tin **UDP 443 (QUIC)** và **UDP 53 (DNS)** ra Default Gateway của mạng LAN.
- Nếu router không chặn cứng ở Layer 3/4, video và API của TikTok sẽ đi thẳng ra **IP cáp quang mạng gốc**, gây lộ IP toàn bộ dàn nick farm.

## 3. Kiến Trúc Tường Lửa MikroTik (L3/L4 Killswitch Bắt Buộc)
Để đảm bảo khi proxy chết thì TikTok cũng phải chết mạng theo (Fail-Closed):
1. **Rule Drop Direct WAN phải đặt tại TOP (Vị trí 0 của Chain Forward):**
   ```text
   /ip firewall filter
   add chain=forward action=drop src-address=192.168.110.0/24 out-interface-list=WAN comment="KILLSWITCH_BLOCK_FARM_DIRECT_WAN"
   ```
2. **Loại trừ dải farm khỏi danh sách forward tự do:**
   - Cấm để dải IP farm (`192.168.110.0/24`) nằm trong `FPT_LAN` hay bất kỳ allowlist nào đứng trước rule Killswitch.
3. **Chặn sạch UDP 443 (QUIC) & UDP 53 (DNS) ra WAN:**
   - Drop toàn bộ UDP 443 và UDP 53 từ dải điện thoại để ép TikTok app không thể lách qua giao thức QUIC.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
