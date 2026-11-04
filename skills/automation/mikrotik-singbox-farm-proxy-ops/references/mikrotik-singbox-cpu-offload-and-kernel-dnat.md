# Mikrotik Singbox CPU Optimization & Kernel DNAT vs L7 Proxy

## Bối Cảnh & Hiện Tượng
- Farm 160 điện thoại Samsung S7 cày video TikTok đẩy lưu lượng qua router MikroTik x86 (`192.168.110.2`) ra các trạm upstream tại Thái Bình (MobiProxy 4G ports 5101-5138 và Xiaomi R3G 16 PPPoE ports 5141-5158).
- Router MikroTik x86 bị nghẽn CPU kịch trần 92% - 98% dù RAM còn trống tới 4.8 GB.
- Lưu lượng đo được trên card ảo `veth-singbox`: ~122 Mbps và 66.000 - 127.000 PPS (Packets Per Second).

## Nguyên Nhân Gốc Rễ
1. **L7 Proxy Container Overhead trên RouterOS:** 
   - Singbox chạy trong Docker container trên RouterOS v7 qua virtual ethernet pair (`veth`).
   - Mỗi gói tin video TikTok phải đi 2 lần qua Netfilter/veth (`Phone -> Bridge -> veth -> Singbox Go user-space -> veth -> WAN`).
   - Hơn 100.000 PPS làm CPU vắt kiệt vì ngắt mạng mềm (`softirq`) và context-switching.
2. **Khai báo cổng thừa trong Singbox Config:**
   - 48 máy Admin kênh chính thực chất đang chạy trực tiếp ra 35 line PPPoE nội bộ qua `3proxy` (`mirotik1.taadaa.click:10008-10035`), hoàn toàn KHÔNG qua Singbox.
   - Việc khai báo cả 160 máy vào Singbox làm phình to file config và mở 160 listeners ảo không cần thiết.
   - Singbox chỉ cần gánh 80 máy Kibe (MobiProxy) + 32 máy Admin kênh non (R3G).

## Giải Pháp Giảm Tải Triệt Để: Kernel DNAT Thay Thế Singbox
- **Tại sao bỏ được Singbox:**
  - Điện thoại S7 gửi ra là `HTTP CONNECT`.
  - MobiProxy và R3G nhận vào cũng là HTTP Proxy (`3proxy` / `tinyproxy`).
  - Cả hai đầu nói cùng giao thức HTTP Proxy, không cần L7 proxy trung gian để chuyển đổi.
- **Rào cản duy nhất của MobiProxy: Mật khẩu (User/Pass Authentication):**
  - Singbox trước đây phải đứng giữa chỉ vì nó tự bơm `mobi1..mobi32 / TaadaaMobi#2026!` vào upstream.
  - MobiProxy đã có sẵn tường lửa Whitelist IP (Scan Guard) chặn sạch từ L3/L4 trước khi bắt tay TCP. Mật khẩu là hoàn toàn dư thừa trong mạng farm nội bộ.
  - **Hành động:** Chuyển MobiProxy sang chế độ `Không xác thực` (No-Auth) -> Cho phép MikroTik làm Kernel DNAT thẳng tắp ở tốc độ dây cáp (`wire-speed`), kéo CPU từ 96% xuống < 5%.
- **Vấn đề Asymmetric Routing trên R3G (2 line vật lý quay 16 PPPoE):**
  - Tên miền `tb.taadaa.click` chỉ trỏ về 1 line PPPoE. Gói tin vào đường này nhưng Tinyproxy trả lời bị 16 bảng định tuyến con đẩy sang line PPPoE khác, gây timeout.
  - Cần cặp rule `DNAT + SNAT (Masquerade)` trên MikroTik hoặc quy tắc `CONNMARK` trên R3G để đảm bảo gói tin vào cổng nào trả về đúng cổng đó.
