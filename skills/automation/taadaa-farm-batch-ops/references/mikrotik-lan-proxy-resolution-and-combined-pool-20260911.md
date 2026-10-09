# Quy Chuẩn Khắc Phục Lỗi Proxy MikroTik Nội Bộ & Hợp Nhất 67 Ports Proxy Pool Cho Batch Download (2026-09-11)

## 1. Hiện Tượng Thực Tế (2026-09-11)
Khi khởi chạy batch download video cho Slot 7 & Slot 8 (`download_by_niche.py`), các request gửi tới `mirotik1.taadaa.click:10001..10007` bị dính lỗi `ProxyError / ConnectTimeoutError` hàng loạt sau 30s timeout do trỏ ra ngoài IP WAN public `171.231.181.33` bị firewall MikroTik DROP.

## 2. Nguyên Nhân Cốt Lõi & Anti-Pattern Cần Tránh
1. **Thiếu Hairpin NAT / Drop WAN trên Router MikroTik**:
   - Tên miền `mirotik1.taadaa.click` phân giải DNS public ra IP WAN `171.231.181.33`.
   - Router MikroTik tại farm đặt firewall rule DROP kết nối WAN vào các cổng `10001..10035` để bảo mật. Khi máy Kibe trong LAN gửi request vòng qua IP WAN bị chặn lại.
2. **Sai Lầm Giả Định Cổng & Đếm Thiếu (Anti-Pattern Bị User Mắng)**:
   - Nhầm tưởng chỉ có 7 cổng và suy diễn "cổng MikroTik đang gán cho điện thoại thì cấm dùng tải", sau đó dồn all-in vào MobiProxy.
   - **Thực tế**: Toàn bộ hệ thống có **35 lines PPPoE MikroTik** (`10001..10035`), cả MobiProxy lẫn MikroTik đều cùng phục vụ farm và phải được hợp nhất để chia đều tải trọng.
3. **Địa Chỉ IP LAN Thực Tế Của Router MikroTik**:
   - Router MikroTik quản lý proxy nội bộ nằm ở IP LAN **`192.168.110.2`** (REST API 9090, proxy ports 10001..10035), không phải gateway `192.168.110.1`.

## 3. Giải Pháp Chuẩn (Standard Fix)
1. **Map DNS nội bộ qua Windows hosts file**:
   - Chèn dòng phân giải cục bộ vào `C:\Windows\System32\drivers\etc\hosts`:
     ```text
     192.168.110.2 mirotik1.taadaa.click
     ```
   - Flush DNS cache: `ipconfig /flushdns`.
   - Kiểm tra socket TCP đến `mirotik1.taadaa.click:10001..10035` -> OPEN 100%, ping ~0.4 - 0.5s.
2. **Hợp Nhất Toàn Bộ 67 Ports Proxy Live (Combined Proxy Pool)**:
   - **32 cổng MobiProxy** (`test.taadaa.click:5101..5132`).
   - **35 cổng MikroTik PPPoE** (`mirotik1.taadaa.click:10001..10035`).
   - **Tổng cộng: 67 ports LIVE 100%**.
   - Lưu vào file pool: `D:/Taadaa/Tiktok-video/combined_proxies_pool.txt`.
   - Khởi chạy downloader với:
     ```bash
     --proxy-pool "D:/Taadaa/Tiktok-video/combined_proxies_pool.txt" --parallel 8
     ```
   - Bộ xoay vòng `next_proxy()` sẽ round-robin đều đặn qua 67 IP 4G/FTTH khác nhau, nâng cao tối đa tốc độ kéo video, triệt tiêu nguy cơ rate limit và không bao giờ nghẽn dồn cục vào 1 cổng đơn lẻ.
