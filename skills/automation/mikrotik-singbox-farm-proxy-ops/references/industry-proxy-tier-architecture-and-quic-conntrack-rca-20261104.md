# Kiến Trúc Proxy Farm Chuyên Nghiệp: Tách Host Riêng (i5-8400) vs Bão UDP/QUIC TikTok & Conntrack RCA (2026-11-04)

## 1. Bản Chất 95% CPU MikroTik Khi Farm Về Màn Hình Home
- **Sự cố:** 160 máy S7 đã hoàn tất ca nuôi trưa, app TikTok đóng về Home Launcher (`LauncherActivity`), nhưng CPU RouterOS x86 vẫn kẹt cứng 93% - 97%.
- **Bóc tách nguyên nhân:**
  1. **Bảng Conntrack tích tụ kỷ lục:** RouterOS có mặc định `tcp-established-timeout: 1d` (24 giờ), `generic-timeout: 10m`. Hơn 102.800 kết nối TCP nửa đóng (half-closed) từ hàng chục vạn chunk video TikTok CDN bị giam giữ trong kernel hash table.
  2. **Bão gói tin ảo (veth-singbox storm):** Card mạng ảo container `veth-singbox` vẫn gánh 66.000 – 127.000 pps và 122 Mbps dù điện thoại ở Home. Lý do: background telemetry/push từ Android + Sing-box container liên tục retry kết nối dở dang sang Thái Bình.
  3. **Biện pháp hạ Conntrack timeout chuẩn Farm:**
     - `tcp-established-timeout: 1h` (hoặc `30m`).
     - `generic-timeout: 2m`, `udp-stream-timeout: 1m`, `udp-timeout: 10s`.
     - Ngay lập tức thu hồi ~17.000 kết nối ma. Nhưng CPU vẫn ở mức cao chừng nào Sing-box container còn gánh luồng trên RouterOS.

## 2. Kiến Trúc Proxy Farm Quốc Tế: Mô Hình 3 Tầng (3-Tier)
- **Sai lầm kinh điển:** Bắt router biên (MikroTik x86) chạy L7 proxy container (Singbox). Cứ mỗi gói tin qua router phải qua netfilter -> veth -> user-space Go -> veth -> netfilter -> WAN (nhân đôi CPU context-switch).
- **Mô hình chuẩn công nghiệp:**
  1. **Tier 1 (Edge Router - MikroTik):** Chỉ làm L3/L4 Routing, DHCP, NAT, Hardware FastPath, CPU < 5%.
  2. **Tier 2 (Dedicated Proxy Gateway):** Một máy x86 độc lập chạy Docker native (Gost / Singbox / HAProxy), nhận toàn bộ kết nối proxy từ farm.
  3. **Tier 3 (Upstream Farm Nodes):** Các trạm 4G MobiProxy và OpenWrt multi-PPPoE tại trạm xa.

## 3. Thẩm Định Lựa Chọn Host Tách Singbox: PC i5-8400 vs Dual Xeon Server
- **PC i5-8400 (6 core 6 thread, RAM 8-16GB):**
  - Singbox viết bằng Go non-blocking I/O tốn rất ít compute. Con i5-8400 gánh 160 máy TikTok chỉ chiếm 5% – 10% CPU và <2GB RAM.
  - **Đánh đổi SPOF:** Thêm 1 máy chạy 24/7 (30W-45W) thì thêm 1 điểm lỗi phần cứng/nguồn. Phải cân nhắc giữa sự cố SPOF và việc để router chạy 95% CPU.
- **Server Dual Xeon (PC Kibe / PC Admin):**
  - **TUYỆT ĐỐI KHÔNG gán Singbox vào PC Kibe:** PC Kibe đang gánh Playwright (Chromium ngốn RAM/CPU), ADB server, Hermes gateway, OmniRoute. Nhét thêm 3.000 - 8.000 socket TikTok sẽ gây cạn kiệt ephemeral ports, làm đơ Playwright và drop lệnh ADB.
  - Nếu buộc dùng máy sẵn có, PC Admin an toàn hơn vì tách rời khỏi node điều khiển trung tâm.

## 4. Rủi Ro Thuật Toán & Chất Lượng Video Khi Ép Chặn UDP 443 (QUIC)
- **Thuật toán TikTok:** Không ban/flag trực tiếp acc chỉ vì dùng TCP. Hàng triệu người dùng mạng văn phòng/doanh nghiệp bị chặn UDP 443 vẫn fallback TCP bình thường.
- **Nhưng cực kỳ nguy hiểm cho dàn Samsung S7 cũ (Exynos 8890, RAM yếu):**
  1. **Lỗi xoay vòng đầu clip:** Nếu dùng rule `action=drop`, S7 phải chờ timeout 1 - 1.5s mới chịu fallback TCP -> kịch bản nuôi acc bị khựng xoay vòng. Bắt buộc phải dùng `action=reject` (Port Unreachable) để fallback trong vài ms.
  2. **Nhạy cảm độ trễ 4G Thái Bình (TCP Congestion):** QUIC/UDP trâu bò trước jitter và rớt gói. Khi ép sang TCP, rớt 1 gói nhỏ trên sóng 4G sẽ kích hoạt TCP retransmission -> S7 bị quá tải CPU, TikTok tự động tụt độ phân giải xuống mờ tịt hoặc đứng hình buffer.
  3. **Hệ quả gián tiếp:** Watch time và completion rate của nick nuôi bị giảm nghiêm trọng -> thuật toán đánh giá tương tác kém, bóp reach kênh.
