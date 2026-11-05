# Kiến Trúc Kernel DNAT Toàn Diện Cho MobiProxy & R3G (Giải Cứu CPU MikroTik)

## 1. Bản Chất Kỹ Thuật Đột Phá
- **Thực trạng cũ:** Chạy Sing-box Container trên MikroTik RouterOS x86 để nạp Auth L7 và làm proxy hub cho 160 phone S7 (80 Kibe + 80 Admin) khiến 4 core CPU bị bão context-switching và ngắt mạng (66.000 - 127.000 pps), đẩy CPU lên 95% - 97.6% liên tục.
- **Giải pháp dứt điểm:**
  1. Chuyển toàn bộ các cổng MobiProxy (5101..5138) sang chế độ "Không xác thực" (`mode=none`) dựa trên việc đã có tầng bảo vệ Firewall IP Whitelist (Scan Guard) tại trạm.
  2. Dùng Kernel DNAT phần cứng RouterOS (`dst-nat`) trên các cổng 20001..20038 bắn thẳng sang IP WAN của MobiProxy.
  3. Kéo CPU MikroTik từ **97.6% rơi thẳng về 0.4% - 1.6%**, giảm độ trễ từ 1.5s xuống 0.45s.

## 2. Thao Tác Chuyển "Không Xác Thực" Trên MobiProxy Control (Web v3.0.67)
- **Cạm bẫy:** Form đổi hàng loạt trong `#security` bị lỗi backend (silent drop), không áp dụng vào runtime của 3proxy.
- **Thao tác chuẩn:**
  1. Vào `#proxies` -> Tìm từng hàng proxy (`proxy01` đến `proxy38`).
  2. Mở thẻ `<details>` của cột tác vụ: Click vào dấu 3 chấm `•••` (`summary`).
  3. Click nút `button[data-action="proxy-access"]` để mở HTML5 Dialog.
  4. Trong dialog: Chọn `select[name="mode"]` có `value="none"`.
  5. Bắt buộc click nút lưu với selector chính xác: `document.querySelector('#access-save').click()`.
  6. Kiểm tra cột XÁC THỰC đổi sang nhãn màu xám `none`.

## 3. Khắc Phục Hiện Tượng Rớt Mạng Hàng Loạt Do MobiProxy Xoay IP
- **Nguyên nhân:** Nhà mạng Viettel định kỳ đổi IP cổng WAN của MobiProxy (từ `116.107.124.153` sang `117.5.179.223`), khiến các rule DNAT tĩnh trên MikroTik trỏ vào IP cũ bị timeout.
- **Khóa cơ học tự động hóa:**
  - Nâng cấp cronjob `mobiproxy-scan-guard-auto-ip` chạy script `update_mikrotik_scan_guard.py` với lịch **1 phút/lần (`* * * * *`)** và `no_agent=True`.
  - Hàm `sync_mikrotik_mobiproxy_dnat()` tự động phân giải `test.taadaa.click`, phát hiện IP mới và cập nhật `to-addresses` cho toàn bộ 38 rule DNAT trên MikroTik trong vòng 60 giây.

## 4. Phân Tích Lỗi Asymmetric Routing Trên R3G (2 Line 16 PPPoE)
- **Nguyên nhân R3G bị Timeout/502 khi DNAT:**
  - Tên miền `tb.taadaa.click` trỏ về 1 IP của 1 interface PPPoE (ví dụ `wan_sub11`).
  - Gói tin DNAT gửi vào interface này nhưng khi Tinyproxy xử lý xong, bảng Policy Routing OpenWrt đẩy gói tin trả về qua interface PPPoE khác.
  - Cơ chế `uRPF` của trạm ISP Viettel lập tức DROP gói tin trả về vì lệch đường.
- **Rủi ro Mangle:** Can thiệp thô bạo vào bảng Mangle từ xa có nguy cơ cao làm rơi gói tin SSH quản trị (cổng 22) hoặc kích hoạt `rp_filter=1` của kernel OpenWrt, làm mất SSH từ xa.
- **Giải pháp chuẩn:** Dựng đường hầm WireGuard Site-to-Site giữa MikroTik và R3G để DNAT vào IP nội bộ cố định, triệt tiêu 100% lỗi Asymmetric Routing.

## 5. Thu Hồi Kết Nối Cũ & Phòng Ngừa Bảo Mật
- Xóa vĩnh viễn Peer WireGuard của VPS hết hạn (Doravo Sentinel `10.200.0.3/32`) trên MikroTik RouterOS để chặn nguy cơ tái cấp phát IP bị xâm nhập mạng nội bộ farm.
