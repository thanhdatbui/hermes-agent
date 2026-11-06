# Cơ Chế Rò Rỉ IP Gốc Qua QUIC/UDP Của App TikTok & Giải Pháp Phòng Thủ (2026-11-05)

## 1. Hiện Tượng Thực Tế
- Điện thoại cài đặt proxy trên Android qua Wi-Fi / `settings put global http_proxy 192.168.110.2:20001`.
- Cổng proxy 20001 bị lỗi hoặc ngắt kết nối.
- Mở Chrome truy cập web (HTTP/HTTPS): Báo lỗi mất mạng hoặc `ERR_PROXY_CONNECTION_FAILED`.
- Mở App TikTok: Video vẫn chạy mượt mà, lướt feed bình thường.

## 2. Nguyên Nhân Kỹ Thuật (Fail-Open Engine)
1. **Lớp Proxy Android:**
   - Cài đặt `global http_proxy` chỉ can thiệp vào các kết nối socket TCP chuẩn của hệ điều hành.
2. **Lớp Mạng Riêng Của TikTok (Cronet / TTNet):**
   - App TikTok không dùng WebView hay thư viện mạng mặc định của Android mà nhúng bộ engine mạng riêng của ByteDance dựa trên Chromium Cronet (`libttnet.so`).
   - Mặc định tải video được đàm phán qua giao thức **QUIC / HTTP/3 trên nền UDP Port 443**, truy vấn DNS bằng **UDP Port 53**.
   - Các gói tin UDP **hoàn toàn không đi qua HTTP Proxy TCP**!
3. **Cơ Chế Fail-Open Nguy Hiểm:**
   - Khi phát hiện proxy TCP bị nghẽn hoặc rớt kết nối, TTNet tự động chuyển hướng (fallback) toàn bộ dữ liệu ra Default Gateway (Router Wi-Fi).
   - Nếu router Wi-Fi (như AP Aruba / Router Ruijie) cho phép forward traffic ra Internet, toàn bộ video và telemetry của nick TikTok sẽ ăn trực tiếp vào IP WAN cáp quang gốc của Farm.
   - Hậu quả: Dàn nick bị ByteDance gắn cờ cày view cùng 1 IP gốc, dẫn đến flop hoặc shadowban hàng loạt.

## 3. Quy Trình Ứng Phó Khẩn Cấp & Phòng Thủ
1. **Khi phát hiện proxy rớt:**
   - Tuyệt đối CẤM để app TikTok tiếp tục chạy ngầm.
   - Chạy lệnh ADB force-stop dập tắt ngay lập tức:
     `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`
   - Hoặc ngắt kết nối Wi-Fi trên điện thoại để cắt đứt luồng UDP.
2. **Khóa cứng ở tầng Router / Firewall:**
   - Trên router trung tâm cấp mạng cho AP Wi-Fi, bắt buộc có các rule tường lửa L4:
     * `DROP` toàn bộ traffic `protocol=udp dst-port=443` (QUIC) từ dải IP của phone farm.
     * `DROP` toàn bộ traffic `protocol=udp dst-port=53` (DNS) ra ngoài Internet; chỉ cho phép DNS nội bộ.
   - Khi đó, TikTok bắt buộc phải fallback về TCP 443 đi qua Proxy; nếu Proxy chết thì app sẽ mất mạng hoàn toàn (Fail-Closed), bảo vệ 100% không bị lộ IP gốc.
