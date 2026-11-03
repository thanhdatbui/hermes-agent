# Farm Network Multi-Cluster Proxy & Action Mandate Decoupling (2026-11-03)

## 1. Phân Tách Lưu Lượng Độc Lập Giữa Các Cụm Proxy (MikroTik PPPoE vs Singbox vs R3G)
- **Hiện tượng lẫn lộn cấu hình:** Khi sinh file cấu hình Singbox (`generate_singbox_config.py`), Agent nhồi nhét cả 80 máy Admin vào Singbox, tạo ra 160 listeners ảo làm phình to file cấu hình và lãng phí tài nguyên CPU.
- **Thực tế kiến trúc phân luồng chuẩn của Farm:**
  * **48 máy Admin kênh chính:** Trỏ trực tiếp vào `mirotik1.taadaa.click:10008..10035` (chạy qua 3proxy container đi thẳng ra 35 line PPPoE tại Đà Nẵng) — **HOÀN TOÀN KHÔNG ĐƯỢC CHO QUA SINGBOX**.
  * **32 máy Admin non/yếu (R3G_MACHINES: 203, 204, 208...):** Trỏ về `192.168.110.2:202xx` để Singbox chuyển tiếp sang 16 port của con **Xiaomi R3G Thái Bình** (`tb.taadaa.click:5141..5158`).
  * **80 máy Kibe:** Trỏ về `192.168.110.2:20001..20080` để Singbox chuyển tiếp sang **MobiProxy Thái Bình** (`test.taadaa.click:5101..5138`).
- **Quy chuẩn cập nhật cấu hình:** Khi chạy profile `both`, Singbox chỉ được phép nạp tổng cộng **112 máy** (80 Kibe + 32 Admin non), tuyệt đối không nạp 48 máy Admin PPPoE trực tiếp.

## 2. Bản Chất R3G Hardware Reboot & Giải Phóng Flash Overlay
- **Lỗ hổng P0:** Router OpenWrt R3G bị reboot bất thình lình làm toàn bộ 16 port bị gián đoạn là do 3 nguyên nhân cộng dồn:
  1. Phân vùng Flash `/overlay` bị đầy 100% (0 bytes trống) do file thực thi lạ `Photo.scr` (5.2MB) và `netstat.cfg` (5.7MB). Khi flash đầy, kernel không ghi được lock file và PID khiến hệ thống crash.
  2. Cơ chế tự sát `watchcat` cài `ping_reboot 8.8.8.8`: Khi mạng quốc tế chập chờn, router tự kích hoạt reboot cứng.
  3. Cronjob `generate_all_proxies.sh` chạy `killall tinyproxy` mỗi phút gây cạn kiệt PID.
- **Biện pháp xử lý dứt điểm:**
  - Xóa vĩnh viễn các file rác, giữ `/overlay` trống trên 10MB (> 70% available).
  - Tắt vĩnh viễn `watchcat ping_reboot`.
  - Tắt header `Via` (`DisableViaHeader Yes`) trên toàn bộ các file `tp_51*.conf` để đạt chuẩn **Elite Anonymous**, ngăn ByteDance/TikTok phát hiện proxy trung gian.

## 3. Đồng Bộ Tự Động IP Whitelist Sang R3G (Chống Báo Cáo Chạy Cơm)
- Khi line chính của MikroTik tại Đà Nẵng đổi IP WAN (do Viettel quay số lại), R3G tại Thái Bình sẽ chặn toàn bộ kết nối nếu IP mới chưa có trong Whitelist của Tinyproxy.
- **Kỷ luật tự động hóa:** Script `update_mikrotik_scan_guard.py` chạy cron 5 phút BẮT BUỘC phải SSH sang R3G (qua Tailscale hoặc DDNS `tb.taadaa.click`), tự động cập nhật dòng `Allow <IP_mới>` vào 16 file config và reload `killall -HUP tinyproxy`. CẤM TUYỆT ĐỐI chỉ chạy script thủ công 1 lần rồi báo cáo là "đã tự động".

## 4. Tách Rời Action Mandate Cho Câu Hỏi Tư Vấn / Đàm Thoại (Anti-Loop)
- **Bẫy Lexical Coupling của Gate:** Khi Gate quét từ khóa đàm thoại (`"em sẽ"`, `"đang chạy"`) và ép buộc phải có `tool_call`, Model bị đẩy vào thế chân tường và sinh ra phản xạ chạy các lệnh probe rác (`curl localhost:1905`) để làm token qua cổng.
- **Quy chuẩn ứng xử & thiết kế:**
  - Khi User hỏi câu hỏi phân tích, tư vấn logic, mổ xẻ nguyên nhân (`Tại sao`, `Là sao`, `Khác gì`, `Có nên`, `Tóm lại`): BẮT BUỘC trả lời thẳng thắn, dứt khoát vào bản chất vấn đề.
  - CẤM TUYỆT ĐỐI dùng văn phong hứa hẹn (`"em sẽ tiến hành..."`) ở cuối câu khi chưa thực thi, để tránh kích hoạt bẫy Action Mandate gây vòng lặp lệnh rác.
