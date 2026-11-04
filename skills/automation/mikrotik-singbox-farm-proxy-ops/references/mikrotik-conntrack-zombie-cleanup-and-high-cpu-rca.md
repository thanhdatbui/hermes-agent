# MikroTik High CPU Root Cause Analysis: Zombie Conntrack Accumulation & TCP Timeout Tuning

## 1. Hiện Tượng Nghịch Lý: Điện Thoại Đã Tắt Nhưng CPU Router Vẫn 93-95%
- **Triệu chứng:** Kết thúc ca chạy nuôi acc, toàn bộ điện thoại Samsung S7 đã về màn hình chính (`LauncherActivity`, app TikTok đã đóng hoàn toàn), không có video nào đang phát, nhưng CPU của con Mini PC MikroTik x86 vẫn kẹt cứng ở mức **93% - 96%** với lưu lượng ảo **>65.000 pps**.
- **Ngộ nhận thông thường (Anti-Poisoning):** Cho rằng "vẫn còn điện thoại đang lén cày video ngầm" hoặc "phần cứng MikroTik x86 quá yếu".

## 2. Nguyên Nhân Gốc Rễ: Bão Kết Nối Ma (Zombie Connection Accumulation)
- Khi 160 máy S7 lướt TikTok đồng thời, mỗi máy mở từ 20 đến 50 kết nối HTTP/2, streaming chunk, WebSocket và telemetry tới các máy chủ CDN.
- Khi app TikTok đóng, các kết nối TCP không gửi cờ ngắt kết nối sạch sẽ (`FIN` / `RST`).
- **Điểm chết trong RouterOS:** Thông số mặc định của Linux Connection Tracking trên RouterOS:
  ```text
  /ip firewall connection tracking
  tcp-established-timeout: 1d (GIỮ KẾT NỐI SUỐT 24 TIẾNG!)
  generic-timeout: 10m
  udp-stream-timeout: 3m
  ```
- **Hệ quả vật lý:** Bảng conntrack tích tụ lên tới **hơn 102.800 kết nối ma (`total-entries: 102864`)**. Con MikroTik phải duy trì và liên tục polling hàng chục vạn kết nối đã chết này trong RAM và CPU, khiến 4 nhân CPU x86 bị vắt kiệt để xử lý ngắt mạng `softirq`.

## 3. Giải Pháp Tinh Chỉnh Conntrack Timeout Chuẩn Farm
Giảm các thông số timeout của Conntrack về ngưỡng an toàn cho môi trường farm mobile automation:
```routeros
/ip firewall connection tracking set tcp-established-timeout=30m generic-timeout=2m udp-stream-timeout=1m udp-timeout=10s
```
- Khi điện thoại đóng app TikTok quá 30 phút, RouterOS sẽ tự động quét dọn và giải phóng toàn bộ các socket ma.
- Bảng conntrack giảm từ 10 vạn xuống còn vài nghìn entries, triệt tiêu 90% tải CPU không cần thiết mà không làm gián đoạn các luồng mạng đang hoạt động thực sự.
