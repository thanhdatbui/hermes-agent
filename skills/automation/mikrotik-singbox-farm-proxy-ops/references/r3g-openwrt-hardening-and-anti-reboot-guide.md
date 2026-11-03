# Cẩm Nang Gỡ Lỗi & An Ninh Hạ Tầng Router Xiaomi R3G OpenWrt

## 1. Các Cạm Bẫy Gây Tự Động Khởi Động Lại (Hardware / Watchdog Reboot)
Khi vận hành Xiaomi R3G (chip MediaTek MT7621, 256MB RAM) gánh 16 cổng Tinyproxy cho farm:

### A. Cạm bẫy Watchcat `ping_reboot`:
- Trong `/etc/config/watchcat` mặc định hoặc bản nạp cũ hay bật `ping_reboot` trỏ tới `8.8.8.8`.
- **Rủi ro:** Khi cáp quang biển chập chờn hoặc ISP Viettel rớt gói ICMP quốc tế, watchcat hiểu lầm là mất mạng và cưỡng chế kích hoạt `reboot` cứng toàn bộ router.
- **Xử lý triệt để:** BẮT BUỘC tắt và vô hiệu hóa watchcat:
  ```bash
  /etc/init.d/watchcat stop && /etc/init.d/watchcat disable
  ```

### B. Cạm bẫy Cronjob `killall tinyproxy` mỗi phút:
- Script tạo proxy tự động (`generate_all_proxies.sh`) tuyệt đối CẤM đưa vào `crontab -l` chạy mỗi phút `* * * * *`.
- **Rủi ro:** Việc kill và khởi động lại 16 process Tinyproxy liên tục mỗi 60 giây gây cạn kiệt PID (Process ID exhaustion), rò rỉ socket và làm chip MT7621 bị nóng/treo, kích hoạt hardware watchdog khởi động lại máy.
- **Xử lý:** Chỉ chạy script này 1 lần duy nhất lúc khởi động hệ thống (`/etc/rc.local`).

### C. Cạm bẫy Phân vùng Flash `/overlay` bị đầy 100%:
- Phân vùng `/overlay` của OpenWrt trên R3G chỉ có khoảng ~39MB.
- **Nguy cơ xâm nhập / malware:** Các file rác Windows lây qua Samba như `Photo.scr` (5.2MB) hoặc binary đóng gói lạ như `netstat.cfg` (5.5MB) trong `/overlay/upper/usr/sbin/` sẽ nuốt sạch dung lượng còn lại (0 bytes available).
- **Hậu quả:** Router không thể tạo file PID, không ghi được lock file `/var/run`, khiến toàn bộ daemon proxy và PPPoE bị crash.
- **Xử lý:** Xóa triệt để các file `.scr`, gỡ bỏ dòng gọi `netstat.cfg` trong `/etc/rc.local` và kiểm tra `df -h /overlay` phải duy trì mức an toàn $\le 75\%$.

---

## 2. Kỷ Luật Ẩn Danh Tuyệt Đối (Elite Anonymous Proxy Chống TikTok Phát Hiện)
- Phần mềm Tinyproxy mặc định luôn tự động chèn header `Via: 1.1 r3g-tpxxxx (tinyproxy)` vào request.
- Nếu gửi header này lên ByteDance / TikTok CDN, hệ thống Risk Engine sẽ lập tức nhận diện thiết bị đang đi qua proxy trung gian.
- **Quy chuẩn bất biến trên R3G:**
  - Trong file cấu hình mẫu `/root/generate_all_proxies.sh` và toàn bộ `/etc/tinyproxy/instances/tp_*.conf`:
    * Xóa bỏ hoàn toàn dòng `ViaProxyName`.
    * Thêm bắt buộc chỉ thị: `DisableViaHeader Yes`.
  - Reload daemon bằng `killall -HUP tinyproxy` (không ngắt kết nối đang chạy).
  - Nghiệm thu qua `httpbin.org/headers` phải xác nhận không còn header `Via` hay `X-Forwarded-For`.

---

## 3. Quản Trị Kết Nối Ổn Định Qua Tailscale
- CẤM gọi lệnh SSH hoặc API kiểm tra trạng thái R3G qua tên miền WAN động (`tb.taadaa.click:22`). Khi WAN PPPoE đổi IP, DNS TTL chưa hết hạn sẽ làm request SSH bị timeout 10-15s, gây đơ giao diện Dashboard.
- BẮT BUỘC dùng IP Tailscale VPN cố định nội bộ: **`100.115.94.49:22`** cho mọi kết nối backend quản trị và probe dữ liệu. Thời gian phản hồi sẽ đạt tốc độ tức thời ~1.1s.
