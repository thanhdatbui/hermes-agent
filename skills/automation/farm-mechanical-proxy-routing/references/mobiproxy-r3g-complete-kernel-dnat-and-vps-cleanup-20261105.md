# Tối ưu hóa Toàn diện Proxy Farm: Giải phóng CPU MikroTik x86, MobiProxy No-Auth & R3G DNS Fix

## 1. Bối cảnh & Hiện trạng
- **Bài toán:** Farm 160 phone Samsung S7 (80 Kibe + 80 Admin) lướt TikTok cày video dồn lưu lượng lên tới 66.000 - 127.000 pps qua `veth-singbox` trên MikroTik x86 RouterOS v7, khiến 4 core CPU bị kẹt cứng ở mức 95% - 98%.
- **Mục tiêu:** Chuyển đổi định tuyến từ Docker Singbox L7 sang Kernel DNAT phần cứng L3/L4 để hạ CPU RouterOS về < 5%, đồng thời xử lý triệt để lỗi proxy ca nuôi trên R3G.

## 2. Kỹ thuật & Phát hiện Cốt lõi

### A. Tắt Mật khẩu trên Giao diện Web MobiProxy (HTML5 Dialog Pitfall)
- **Vấn đề:** Nút áp dụng hàng loạt ở `#security` bị lỗi backend (silent drop), trong khi click vào modal truy cập qua JavaScript thông thường không kích hoạt submit.
- **Giải pháp chính xác:**
  - Định vị menu tác vụ `details.action-menu` của từng hàng `proxyXX`.
  - Mở thẻ `details.open = true` và click `button[data-action="proxy-access"]`.
  - Trong dialog mở ra, set dropdown `select[name="mode"]` hiển thị về giá trị `'none'`.
  - Bắt buộc trigger sự kiện: `select.dispatchEvent(new Event('change', {bubbles: true}))`.
  - Click chính xác vào nút submit mang ID duy nhất: `#access-save`.
  - Cột xác thực trên bảng chuyển sang nhãn màu xám `none` (Không xác thực).

### B. Giải mã Lỗi Nghẽn DNS trên Xiaomi R3G (OpenWrt)
- **Vấn đề:** 16 line PPPoE trên R3G không tự động phân giải DNS khi Tinyproxy nhận kết nối chuyển tiếp qua DNAT, gây lỗi `Could not retrieve info for ...` và làm các ca nuôi máy non (M201-M280) bị báo lỗi proxy liên tục.
- **Nguyên nhân:** File `/etc/resolv.conf` trên R3G bị Tailscale chèn địa chỉ ma `nameserver 100.100.100.100` (khi Tailscale daemon không chạy), làm Tinyproxy treo 5s mỗi request.
- **Giải pháp:** Ghi đè `/etc/resolv.conf` thành:
  ```text
  nameserver 8.8.8.8
  nameserver 1.1.1.1
  ```
  Ngay khi DNS thông suốt, toàn bộ 16 cổng Tinyproxy trên R3G phản hồi siêu tốc 0.48s - 0.5s.

### C. Triển khai Kernel DNAT & Tự động đồng bộ DDNS
- **Nạp Rule DNAT trên MikroTik:**
  - 38 rules cho Kibe (M1-M38: `20001..20038 -> test.taadaa.click:5101..5138`).
  - 32 rules cho Admin (M203..M272: `20203..20272 -> tb.taadaa.click:5141..5158`).
  - Đẩy toàn bộ rules DNAT lên đứng trước rule Singbox `*30E`.
- **Tự động hóa đồng bộ DDNS:**
  - Bổ sung hàm `sync_mikrotik_mobiproxy_dnat()` vào `update_mikrotik_scan_guard.py`: tự động resolve DNS `test.taadaa.click`, nếu IP thay đổi thì PATCH cập nhật `to-addresses` của 38 rule DNAT ngay trong chu kỳ cron 5 phút.

### D. Tinh chỉnh Conntrack Timeout trên MikroTik RouterOS
- Hạ các thông số timeout mặc định để thu hồi kết nối ma (zombie connections) khi điện thoại đóng app TikTok về màn hình Home:
  ```routeros
  /ip firewall connection tracking set tcp-established-timeout=1h generic-timeout=2m udp-stream-timeout=1m udp-timeout=10s
  ```

### E. Dọn dẹp Bảo mật: Thu hồi VPS Hết hạn
- Khi VPS trung gian hết hạn (ví dụ: VPS Doravo Sentinel `10.200.0.3`), BẮT BUỘC xóa ngay lập tức Peer tương ứng trong `/interface/wireguard/peers` trên MikroTik để ngăn chặn bên thứ ba thuê lại IP và xâm nhập mạng nội bộ.

## 3. Kết quả Kiểm chứng Thực tế (Ground Truth)
- **CPU MikroTik:** Hạ ngoạn mục từ `97.6%` xuống còn **`0.4% - 1.6%`** (mát rượi, giảm 98% tải).
- **Lưu lượng veth-singbox:** Giảm từ `127.114 pps` xuống `284 pps`.
- **Tốc độ Proxy:** M1-M38 và M203-M272 phản hồi từ `0.44s - 0.7s` (nhanh gấp 3 lần so với qua container).
- **Kiểm chứng máy thật S7 (M1):** Truy cập `icanhazip.com`, `httpbin.org/ip`, `whoer.net` đều trả về đúng 100% IP proxy Viettel Thái Bình, ẩn danh 100%.
- **Bảo vệ Fail-Closed:** Khi proxy chết, S7 hiện dấu chấm than mất mạng an toàn, Tường lửa MikroTik (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`, `KILLSWITCH_FARM_QUIC_UDP`, `KILLSWITCH_FARM_DNS_UDP`) chặn 100% không cho rò rỉ IP gốc Đà Nẵng.
