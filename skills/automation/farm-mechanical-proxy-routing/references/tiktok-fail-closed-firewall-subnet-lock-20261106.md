# Kỷ Luật Fail-Closed Toàn Diện: Khóa Tường Lửa 192.168.0.0/16 và Chống Lọt Direct WAN Khi Proxy Sập (2026-11-06)

## 1. Bản Chất Sự Cố Lọt Mạng (Fail-Open) của TikTok Khi Proxy Sập
- **Hiện tượng:** Khi tắt hoặc ngắt cổng proxy (qua Kernel DNAT hoặc bẻ IP đích sang IP chết `192.0.2.1`), trình duyệt web (HTTP Proxy) báo `ERR_EMPTY_RESPONSE` / `ERR_CONNECTION_REFUSED`, nhưng ứng dụng TikTok trên Samsung S7 (như Máy 204) vẫn tải được video bình thường (video đồ ăn, video thời trang).
- **Nguyên nhân cốt tử:**
  1. **Lệch Subnet Tường Lửa:** Rule Killswitch `*D` (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`) trên MikroTik ban đầu chỉ đặt `src-address=192.168.110.0/24` (chỉ bảo vệ 80 máy Kibe). Dàn máy Admin (Máy 201-280) nằm ở dải `192.168.10.0/24` không bị rule này chặn!
  2. **Bẫy Rule Forward Whitelist:** Rule `*10` (`ALLOW_FARM_ADMIN_FORWARD_FPT_LAN`) đứng ngay sau, cho phép `src-address-list=FPT_LAN` forward tự do ra WAN. Trong khi đó, list `FPT_LAN` lại chứa cả `192.168.10.0/24`.
  3. **TikTok SDK Fail-Open (TTNet):** Khi cổng HTTP Proxy không phản hồi, SDK TikTok lập tức thử kết nối trực tiếp hoặc dùng giao thức UDP 443 (QUIC). Vì không bị firewall drop, gói tin của máy S7 đi thẳng ra các line PPPoE Viettel Đà Nẵng, gây lộ IP thật và đe dọa an toàn toàn bộ tài khoản Farm!

## 2. Giải Pháp Khóa Cơ Học (Mechanical Killswitch) Triệt Để Trên RouterOS
- **Khóa toàn bộ dải IP Farm:** Mở rộng phạm vi chặn của rule `*D` từ `/24` lên `/16` để bao trùm cả `192.168.10.x` và `192.168.110.x`:
  ```routeros
  /ip firewall filter
  set [find comment="KILLSWITCH_BLOCK_FARM_DIRECT_WAN"] src-address=192.168.0.0/16 out-interface-list=WAN action=drop
  ```
- **Xóa dải Phone Farm khỏi whitelist forward WAN:**
  ```routeros
  /ip firewall address-list
  remove [find list=FPT_LAN address="192.168.10.0/24"]
  ```

## 3. Kỷ Luật Đối Soát Thị Giác Thực Tế & Chống Gửi Ảnh Đen / Bịa Đặt Mô Tả (Anti-Hallucination)
1. **Pre-flight Check màn hình trước khi chụp ảnh:**
   - Khi điều khiển S7 qua ADB, màn hình thường tự tắt sau 30-60s (`Display Power: state=OFF`). Lệnh `screencap` khi màn hình tắt sẽ sinh ra ảnh đen kịt (RGB = 0).
   - BẮT BUỘC bật sáng và giữ màn hình trước khi chụp:
     ```bash
     adb -s <serial> shell "input keyevent 224 && input keyevent 82 && svc power stayon true && settings put system screen_off_timeout 600000"
     ```
2. **Kiểm tra pixel màu thật (Black Screen Sentinel):**
   - Dùng script Python kiểm tra mảng màu pixel qua `np.unique()`. Nếu `r_vals == [0]` và `g_vals == [0]` và `b_vals == [0]` -> TUYỆT ĐỐI CẤM GỬI thẻ `MEDIA:`, phải đánh thức màn hình và chụp lại.
3. **Đối soát nội dung thực tế qua Native Vision / OCR:**
   - CẤM đoán mò nội dung ảnh (như bịa ra thông báo mất mạng hay nút Thử lại trong khi app đang phát video bình thường).
   - Phải đọc đúng từng dòng text, đúng trạng thái icon Wi-Fi (có dấu chấm than hay không) và mô tả trung thực hiện trường thực tế.
