# Bóc Tách Bản Chất L3/L4 Firewall vs L7 Proxy & Cạm Bẫy MobiProxy Web v3.0.67 Hardcoded Auth

## 1. Bản Chất L3/L4 Firewall (MikroTik) vs L7 Application Proxy (Singbox)
- **MikroTik RouterOS (L3/L4 Engine):**
  - Chỉ nhìn thấy IP nguồn/đích, Port nguồn/đích và trạng thái TCP/UDP (`SYN`, `ESTABLISHED`).
  - Mù hoàn toàn nội dung ứng dụng, không thể đọc HTTP Header, không thể tự động chèn thông tin tài khoản xác thực (Basic Auth / `Proxy-Authorization`).
  - Nhiệm vụ tối thượng: Lọc gói tin (Accept/Drop), chống leak IP gốc khi proxy rớt, định tuyến ở tốc độ phần cứng (wire-speed).
- **Singbox / 3proxy / Tinyproxy (L7 Application Proxy):**
  - Đóng vai trò "thông dịch viên" tầng ứng dụng: Bóc tách gói tin HTTP CONNECT / SOCKS5, nạp thông tin xác thực (`User:Pass`) upstream, chuyển tiếp dòng dữ liệu qua kết nối socket TCP.
  - Phải chạy trong User-space (Golang / C), gây chi phí chuyển mạch ngữ cảnh (Context Switching) và tiêu tốn CPU đáng kể khi chịu tải cao (66k - 120k pps).

## 2. Tại Sao Không Thể Định Tuyến Thuần Túy Ở Router Mà Bắt Buộc Cần Singbox?
- **Đầu phát (Samsung S7 Wi-Fi Aruba):** Gửi gói tin thô tới đích máy chủ TikTok (`dst-IP: TikTok CDN, Port 443`).
- **Đầu nhận (MobiProxy / R3G Thái Bình):** Là các máy chủ HTTP Proxy (chạy `3proxy` hoặc `Tinyproxy` lắng nghe trên các port `5101..5158`). Chúng không phải là Router L3 / VPN Gateway để nhận gói tin thô, mà bắt buộc phải nhận request theo chuẩn giao thức `HTTP CONNECT`.
- Nếu MikroTik dùng PBR/DNAT bốc gói tin thô ném thẳng vào port 5101 của MobiProxy, dịch vụ proxy ở Thái Bình sẽ trả về lỗi cú pháp (`Malformed Request`) và drop kết nối ngay lập tức.
- Do đó, bắt buộc phải có một Proxy Client trung gian (Singbox) đứng ở giữa để đóng gói request thành chuẩn `HTTP CONNECT`.

## 3. Cạm Bẫy Firmware MobiProxy Control (Web v3.0.67): Hardcoded `auth strong`
- **Hiện tượng:**
  - Trên giao diện Web MobiProxy (`#security`), khối form *"Xác thực và mật khẩu hàng loạt"* cho phép chọn chế độ *"Không xác thực"* hoặc *"Danh sách IP"* và ấn *"Áp dụng cho tất cả proxy"*.
  - Bảng danh sách proxy (`#proxies`) không có trang cấu hình/chỉnh sửa riêng cho từng port lẻ (chỉ có nút Reset và nút tác vụ hiển thị menu xem nhanh).
- **Cạm bẫy thực tế:**
  - Nút *"Áp dụng cho tất cả proxy"* trên bản firmware `Web v3.0.67` bị nghẽn I/O / lỗi backend script bên trong hộp: Tiến trình backend không ghi đè lại file template cấu hình 3proxy và không reload tiến trình 3proxy trong RAM.
  - Khi kiểm tra thực tế bằng client HTTP probe (không truyền user/pass), toàn bộ các port `5101..5138` vẫn trả về mã lỗi `HTTP Error 407: Proxy Authentication Required`.
  - Cột *XÁC THỰC* trên giao diện web vẫn giữ nguyên nhãn `strong`.
- **Bài học vận hành:**
  - Tuyệt đối không tin tưởng trạng thái dropdown trên web MobiProxy khi chưa có bằng chứng `urllib.request` probe trả về `HTTP 200`.
  - Chừng nào hộp MobiProxy chưa thực sự nhả password, cụm máy Kibe bắt buộc vẫn phải đi qua Singbox để tự động nạp `mobi1:TaadaaMobi#2026!`.
