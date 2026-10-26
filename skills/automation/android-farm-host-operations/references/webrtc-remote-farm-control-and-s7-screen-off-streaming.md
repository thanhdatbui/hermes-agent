# Kiến Trúc Điều Khiển Farm Từ Xa Qua WebRTC & Kỷ Luật Stream Tắt Màn Hình Trên Samsung S7

Tài liệu phân tích kỹ thuật và quy chuẩn vận hành hệ thống điều khiển điện thoại từ xa (Remote Multi-Device Manager / Scrcpy-Web) áp dụng trên dàn Phone Farm (160+ Samsung Galaxy S7).

---

## 1. Khảo Sát Kiến Trúc Hệ Thống (Light Remote / WebRTC Controller)

Hệ thống điều khiển farm từ xa qua WebRTC bao gồm 3 thành phần chính:

1. **On-Device Agent:**
   - Binary native (tương tự `scrcpy-server`, `minicap`, `minitouch`) chạy dưới quyền shell ADB.
   - Đọc trực tiếp frame buffer từ `SurfaceFlinger`, encode phần cứng thành luồng video H.264 hoặc chuỗi MJPEG gửi qua TCP/Unix socket.
   - Nhận tín hiệu điều khiển cảm ứng và inject trực tiếp vào kernel thông qua `/dev/input/event*` hoặc `uinput`.

2. **Central WebRTC/WebSocket Gateway:**
   - Đóng vai trò Media Server & Signaling Server quản lý danh sách thiết bị.
   - Nhóm thiết bị theo cụm (Farm 1, Farm 2...) và giám sát heartbeat kết nối (Online / Offline).
   - Bộ điều phối Multicast Touch: nhân bản tọa độ chạm/vuốt từ 1 máy master sang toàn bộ máy worker được chọn.

3. **Giao Diện Điều Khiển (Web/Mobile Frontend):**
   - **Dashboard Quản Lý:** Bảng trạng thái trực quan, bộ lọc cụm, phím tắt thao tác nhanh (`[Mở]`, `[Khởi động]`).
   - **1:1 Remote Control:**
     * Stream màn hình Android độ trễ thấp (< 100ms qua WebRTC).
     * Đầy đủ phím điều hướng chuẩn: `Back`, `Home`, `Recent`.
     * Tùy chọn chất lượng: Low / Med / High (15 / 30 / 60 FPS, giới hạn bitrate).
     * Phím tắt tiện ích: `[Bật/Tắt màn]`, `[Cài APK]`, `[Reboot]`, mở nhanh app (`TikTok`, `YouTube`, `Chrome`).
   - **Group Control (Điều Khiển Đồng Bộ):**
     * Lưới Multi-view hiển thị đồng thời nhiều màn hình.
     * Multicast Sync Touch: vuốt 1 máy, toàn bộ máy tick chọn tự động vuốt theo.

---

## 2. Đánh Giá Giá Trị & Rủi Ro Trên Farm Taadaa (Samsung S7 Exynos 8890)

### Điểm Cộng Vận Hành (Opportunities):
1. **Cứu Hộ Thủ Công Khẩn Cấp (Emergency Fallback):**
   - Khi bot tự động gặp các ca 2FA lạ, checkpoint danh tính, hoặc captcha xoay góc/ghép hình phức tạp mà code automation chưa cover hết: mở WebRTC lên kéo trực tiếp trong 5 giây mà không cần chạy lại dàn cắm cáp hay cầm máy vật lý.
2. **Triệt Tiêu Quá Nhiệt & Phồng Pin (Screen-Off Streaming):**
   - Tính năng **Tắt màn hình vật lý nhưng vẫn stream và nhận cảm ứng** là điểm cộng sống còn cho dòng Samsung S7. Màn hình AMOLED của S7 tỏa nhiệt rất lớn; tắt màn hình giúp hạ nhiệt độ máy từ 48-52°C xuống dưới 38°C, ngăn chặn hoàn toàn nguy cơ nổ/phồng pin khi cắm sạc 24/7.

### Rủi Ro Chí Mạng Cần Kiểm Soát (Risks):
1. **Bẫy Nghẽn CPU & Rớt Máy Offline:**
   - Chip Exynos 8890 trên S7 tản nhiệt kém và hiệu năng encode video có hạn. Nếu bật encoder video stream đồng thời trên 160 máy, CPU S7 sẽ chạm ngưỡng 100%, gây thắt cổ chai bus USB/mạng LAN và dẫn tới hiện tượng crash `adbd` (máy rớt sang trạng thái `offline`).
2. **Xung Đột ADB Socket:**
   - Nếu client remote chiếm dụng socket ADB liên tục mà không giải phóng, tiến trình runner tự động (`automation_core`) sẽ bị kẹt I/O timeout khi thực thi lệnh `screencap` hoặc `input tap`.

---

## 3. Quy Chuẩn Vận Hành Chuẩn Hóa (Farm Governance)

1. **Vòng Lặp Nuôi/Reg Chính Bắt Buộc Giữ 100% Headless:**
   - Toàn bộ tác vụ chạy hàng ngày (Nuôi feed, Đổi profile, Đăng ký nick, Like/Follow) BẮT BUỘC thực thi qua cơ chế headless: `adb exec-out screencap` + `WinRT OCR offline` (tốn đúng 0 token, 0 chi phí băng thông, không kích hoạt video encoder).
2. **Kích Hoạt WebRTC Stream Theo Cơ Chế On-Demand:**
   - Hệ thống remote chỉ được phép khởi động tiến trình stream khi có người dùng hoặc admin chủ động click mở tab xem thiết bị cụ thể.
   - Khi đóng tab hoặc chuyển sang màn hình khác, Gateway BẮT BUỘC gửi tín hiệu ngắt ngay encoder trên máy Android để trả lại 100% CPU cho tác vụ nền.
3. **Kỷ Luật Khung Giờ Ca Nuôi:**
   - Trong các khung giờ cao điểm chạy ca nuôi (Ca 1: 08:30-11:30, Ca 2: 14:00-17:30, Ca 3: 19:30-22:30), CẤM bật tính năng Group Control / Multicast Touch trên các máy đang có lịch chạy feed để tránh xung đột quyền điều khiển ứng dụng.
