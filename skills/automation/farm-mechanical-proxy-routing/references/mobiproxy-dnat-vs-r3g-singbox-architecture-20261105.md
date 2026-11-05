# Phân Định Định Tuyến Farm: Kernel DNAT (MobiProxy 1-WAN) vs Singbox Proxy L7 (R3G Multi-PPPoE)

## 1. Hiện Trường Kỹ Thuật & Bài Học Thực Nghiệm (2026-11-05)
Trong quá trình tối ưu tải phần cứng Router MikroTik (kéo CPU từ 97.6% về 1.6%), hệ thống đã thực nghiệm triển khai Kernel DNAT (`dst-nat`) cho 2 cụm thiết bị mạng:
1. **Cụm 1: Hộp MobiProxy (Thái Bình) phục vụ 80 máy Kibe (`20001..20038`):**
   - **Đặc điểm phần cứng:** 1 cổng WAN duy nhất đại diện, quay 32-38 session PPPoE nội bộ.
   - **Kết quả Kernel DNAT:** Thành công rực rỡ 100%! Gói tin từ MikroTik gửi tới IP WAN đại diện chui vào cổng nào thì hộp trả về đúng cổng đó. Tốc độ đạt wire-speed 0.45s, CPU MikroTik rảnh rỗi tuyệt đối (0.4% - 1.6%).
   - **Tự động hóa DDNS:** Gắn watchdog 1 phút/lần (`scripts/update_mikrotik_scan_guard.py`) tự phân giải DNS `test.taadaa.click` và đồng bộ `to-addresses` cho 38 rule DNAT khi ISP Viettel xoay IP.
2. **Cụm 2: Xiaomi R3G OpenWrt (Thái Bình) phục vụ 32 máy Admin non (`20201..20232`):**
   - **Đặc điểm phần cứng:** Cắm 2 line quang vật lý quay 16 PPPoE độc lập, mỗi cổng proxy gắn cứng vào 1 interface PPPoE con.
   - **Vấn đề Asymmetric Routing & Mangle Conflict:**
     * Khi MikroTik DNAT tới IP WAN đại diện của R3G, gói tin vào bằng line này nhưng Tinyproxy trả lời bằng line khác $\rightarrow$ Bị firewall ISP Viettel (uRPF) drop gây Timeout.
     * Khi đã cấu hình PBR hai chiều trên R3G (`ip rule add to <MikroTik_IPs> table 200`), việc test từ PC Kibe (`192.168.110.x`) thành công (LIVE 1.1s) do PC đi ra cổng WAN1 (`171.231.180.189`).
     * **Bẫy chí mạng:** Thiết bị thật trong farm (như Máy 203 IP `192.168.10.221`) lại bị bảng Mangle của MikroTik ép đi ra các cổng WAN phụ (`pppoe-out8..out12` mang dải IP khác như `171.231.187.x`).
     * Khi R3G chỉ whitelist WAN1 hoặc đường trả lời bị lệch, kết nối của điện thoại bị bẻ gãy ngay tại cổng mạng $\rightarrow$ Điện thoại S7 bị mất mạng, hiện dấu chấm than (!) trên biểu tượng Wi-Fi và trình duyệt báo `ERR_CONNECTION_REFUSED` / không thể tải trang!

## 2. Quy Chuẩn Kiến Trúc Cốt Lõi (Architecture Contract)
1. **MobiProxy (1-WAN Gateway):** BẮT BUỘC dùng **Kernel DNAT phần cứng**.
   - Miễn nhiễm hoàn toàn với lỗi Asymmetric Routing.
   - Xóa bỏ hoàn toàn gánh nặng L7 Proxy trên PC/Router, giải phóng 95% CPU MikroTik.
   - Luôn duy trì watchdog đồng bộ DDNS 1 phút/lần không dùng LLM (`no_agent=True`).
2. **R3G / Multi-WAN Router (Quay đa phiên trên nhiều line vật lý):**
   - **Giữ nguyên Singbox Proxy Container L7 trên MikroTik:**
     * Singbox hoạt động như một L7 Proxy Termination: Nó kết nối từ IP nội bộ router tới R3G theo tên miền, xử lý handshake và phân giải DNS sạch sẽ, độc lập hoàn toàn với dải IP LAN `192.168.10.x` và bảng Mangle của các máy con.
     * Khi 80 máy Kibe đã được bốc ra chạy Kernel DNAT, chỉ còn 32 máy Admin non chạy Singbox thì CPU MikroTik chỉ tốn ~1.5% - 2.0%, hoàn toàn mát rượi 24/7.
   - **CẤM gượng ép DNAT R3G qua mạng WAN công cộng:** Việc cố tình nạp PBR phức tạp và đè Mangle từ xa vừa có nguy cơ làm rớt SSH quản trị R3G, vừa dễ gây đứt mạng cho các máy farm khi ISP Viettel xoay IP trên 35 line WAN của MikroTik.

## 3. Kỷ Luật Kiểm Chứng Thị Giác Thực Tế (Anti-Blind Verification)
- **Không suy đoán trạng thái kết nối từ lệnh CLI máy tính:** Việc chạy `urllib` qua cổng proxy từ máy tính Kibe thành công KHÔNG đồng nghĩa với việc điện thoại Samsung S7 trong phòng farm có mạng (do khác IP nguồn, khác bảng Mangle và khác cơ chế Captive Portal Check của Android).
- **Kiểm chứng điện thoại bắt buộc 3 yếu tố:**
  1. `dumpsys connectivity`: Kiểm tra trường `everValidated` và `lastValidated` (nếu `false` là đang có dấu chấm than ngầm).
  2. `screencap` màn hình thật và dùng vision/OCR đọc trực tiếp pixel:
     - Phải dismiss các modal/tooltip che khuất (như "Chuyển đổi tab dễ dàng").
     - Soi rõ thanh trạng thái: Biểu tượng Wi-Fi không có dấu chấm than (!).
     - Soi nội dung trang web: Hiển thị chính xác dãy số IP Public Viettel, không xuất hiện dòng chữ "Không có kết nối Internet" hay `ERR_CONNECTION_REFUSED`.
