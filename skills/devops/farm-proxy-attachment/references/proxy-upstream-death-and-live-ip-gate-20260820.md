# Lỗ Hổng VPN Gate Ảo & Cơ Chế Xác Thực Live Proxy IP (20/08/2026)

## 1. Bản Chất Lỗ Hổng Proxy Sập Nhưng TikTok Vẫn Chạy (Direct IP Leak)

### Hiện Tượng
- Upstream proxy sập (toàn bộ cổng `test.taadaa.click` hoặc `mirotik1` bị down/timeout).
- Trên thiết bị Android: Chrome báo mất mạng hoàn toàn.
- **TikTok vẫn lướt feed, mở video bình thường.**
- Toàn bộ 80 máy farm bị lộ IP Direct mạng nhà (`113.23.29.121`), gây trùng IP hàng loạt nick trên farm.

### Nguyên Nhân Kỹ Thuật
1. **Lỗ hổng kiểm tra VPN (`check_android_vpn` trong `automation-core/preflight.py`):**
   - Script chỉ kiểm tra: `ip addr show tun0` (có cờ `UP` không) và `dumpsys connectivity` (có chuỗi `NetworkAgentInfo [VPN] CONNECTED/CONNECTED` không).
   - **Thực tế:** Khi ViChanger bật VPN, hệ điều hành Android tạo interface ảo `tun0` tại local thiết bị. Khi proxy upstream chết:
     - Card mạng ảo `tun0` ở local **VẪN Ở TRẠNG THÁI `UP`**!
     - Hệ thống Android vẫn báo `VPN CONNECTED`.
     - Script kiểm tra thấy `tun0 UP` $\rightarrow$ Tưởng VPN đang sống $\rightarrow$ **Cho phép chạy bình thường (False-Pass Gate)**.

2. **Cơ chế Fallback Traffic của TikTok:**
   - Trong bảng định tuyến Android (`ip rule show` / `ip route show table all`), table 1028 chỉ điều hướng gói tin qua `tun0`.
   - Khi `tun0` không có internet phản hồi từ proxy upstream:
     - **Chrome:** Bị chặn do chờ resolve DNS/HTTP qua tunnel.
     - **TikTok App:** Sử dụng đa giao thức (QUIC / HTTP/2 / multi-homed socket). Khi tunnel VPN không phản hồi dữ liệu, TikTok tự động fallback chuyển sang kết nối trực tiếp qua interface mạng gốc (`wlan0` - Wi-Fi direct).
     - Hậu quả: Toàn bộ traffic TikTok chạy thẳng ra IP mạng nhà thật mà script không hề hay biết!

---

## 2. Giải Pháp Xác Thực Live IP Bắt Buộc (3-Layer Hard Gate)

### Lớp 1: Bắt buộc Check "Proxy Live IP Ping" trước khi chạy (Hard Preflight Gate)
- **CẤM TUYỆT ĐỐI** chỉ kiểm tra `tun0 UP` và `dumpsys connectivity`.
- Trước khi khởi chạy bất kỳ script nào (Feed, Follow, Reg, Login, 2FA...): Bắt buộc gửi broadcast kiểm tra Live IP thực tế qua ViChanger:
  ```bash
  adb -s <SERIAL> shell am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller
  ```
- **Điều kiện PASS bắt buộc:**
  1. `result=200` (Broadcast thành công).
  2. `data="<IP>"` chứa IP public hợp lệ (khác rỗng).
  3. **IP trả về KHÔNG ĐƯỢC TRÙNG với IP Direct của PC/mạng nhà** (`PC_DIRECT_IP`).
- **Nếu `result=0` (Proxy chết) hoặc IP trả về trùng IP mạng nhà:** $\rightarrow$ **BLOCK NGAY LẬP TỨC (FAIL-CLOSED)**, dừng worker, ghi log `PROXY_UPSTREAM_DEAD` / `DIRECT_IP_LEAK`, tuyệt đối không mở TikTok.

### Lớp 2: Kiểm tra sức khỏe Proxy Pool từ Host (PC-Level Poller)
- Định kỳ kiểm tra toàn bộ proxy trong workbook mapping từ PC qua `urllib.request.urlopen('http://api.ipify.org')`.
- Phát hiện cổng proxy nào chết $\rightarrow$ Gắn cờ DEAD và tự động tạm ngưng các máy liên quan.

---

## 3. Quy Tắc Timeout 15 Phút Khi Lướt Feed Lỗi
- Khi lướt feed gặp lỗi (`MANUAL_NEEDED` / `FAIL`), AI Auto-Recovery vào phân tích vá lỗi.
- **Sau 15 phút** (tính từ lúc phát hiện lỗi), nếu phiên chạy không tiếp tục hoặc không có can thiệp thành công:
  - Tự động gọi `am force-stop com.ss.android.ugc.trill`.
  - Gửi phím `KEYCODE_HOME` (keyevent 3).
  - Tắt app, giải phóng thiết bị, tránh ngâm sáng màn hình và tránh treo app.
