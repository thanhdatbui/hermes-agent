# R3G Router Stability & Proxy Forensic Pitfalls

## 1. Cạm bẫy Flash Overlay 100% Full trên OpenWrt
- **Hiện tượng:** Phân vùng `/overlay` của Xiaomi R3G (hoặc router OpenWrt có NAND nhỏ ~39-128MB) chạm 100% (`0 bytes available`).
- **Nguyên nhân cốt lõi:**
  1. File lạ rác hoặc malware tự lây lan từ share Samba mở (`smbd/nmbd`) hoặc upload thủ công (ví dụ `Photo.scr` 5.2MB, `backup_20261030/Photo.scr` 6.0MB).
  2. Binary giả lập hoặc malware lưu trữ trên overlay (ví dụ `/overlay/upper/usr/sbin/netstat.cfg` 5.5MB).
- **Hậu quả:** Router không thể ghi PID file (`/var/run`), không thể tạo socket, log bị kẹt, kernel panic hoặc OOM crash.
- **Quy tắc dọn dẹp an toàn:**
  - Tuyệt đối không dùng `find ... -delete` vì BusyBox trên OpenWrt không hỗ trợ `-delete` dẫn đến exit code lỗi.
  - Dùng `rm -f /root/*.scr /root/backup_*/*.scr /usr/sbin/netstat.cfg /overlay/upper/usr/sbin/netstat.cfg 2>/dev/null || true`.
  - Phải đưa `/overlay` về ngưỡng an toàn $\le 70\%$ dung lượng (trống $\ge 10\text{MB}$).

## 2. Bẫy Tự Sát của Watchcat (`ping_reboot`)
- **Cấu hình nguy hiểm:** File `/etc/config/watchcat` bật `option mode 'ping_reboot'` trỏ tới `8.8.8.8`.
- **Rủi ro:** Khi đường truyền PPPoE Viettel gặp hiện tượng jitter hoặc ISP lọc gói ICMP quốc tế, Watchcat sẽ hiểu nhầm mất mạng và kích hoạt khởi động lại phần cứng (hardware reboot), làm sập đồng loạt toàn bộ 16 port proxy.
- **Giải pháp:** Bắt buộc tắt và disable vĩnh viễn:
  ```bash
  /etc/init.d/watchcat stop 2>/dev/null
  /etc/init.d/watchcat disable 2>/dev/null
  killall watchcat 2>/dev/null || true
  ```

## 3. Bẫy Cronjob Killall Gây Sập Toàn Bộ Proxy Loop
- **Cạm bẫy:** Script sinh proxy (`generate_all_proxies.sh`) chứa các lệnh `killall -9 tinyproxy`. Nếu script này bị nhét vào crontab (`* * * * *`), router sẽ liên tục kill và restart 16 proxy mỗi 60 giây $\to$ gây rò rỉ PID (PID exhaustion) và crash kernel.
- **Nguyên tắc:** CẤM tuyệt đối để `generate_all_proxies.sh` trong crontab định kỳ. File này chỉ được chạy 1 lần duy nhất lúc khởi động (`/etc/rc.local`) với độ trễ đệm (`sleep 30`).
- **Phục hồi khẩn cấp khi Tinyproxy bị ngắt:**
  Nếu vô tình kill tinyproxy, phải chạy ngay `/bin/sh /root/generate_all_proxies.sh` trong background để đưa 16 port trở lại trạng thái `LISTEN`.

## 4. Quản trị R3G qua IP Tailscale Cố Định (Chống Lag/Timeout DNS WAN)
- Khi gọi SSH hoặc probe API từ Dashboard sang R3G, tuyệt đối KHÔNG gọi qua domain DDNS WAN (`tb.taadaa.click`) vì mỗi khi PPPoE đổi IP, DNS Cloudflare có độ trễ cập nhật khiến kết nối bị timeout (ngâm 10-15s làm đơ UI Dashboard).
- BẮT BUỘC ưu tiên trỏ thẳng vào IP Tailscale cố định: **`100.115.94.49`**. Thời gian phản hồi sẽ giảm từ 15s xuống còn ~1.1s.

## 5. Bẫy Regex Nhầm Lẫn IP Public 172.x với RFC 1918 Private IP
- **Cạm bẫy trong script watchdog PPPoE:** Kiểm tra `[:pick $ip 0 4] = "172."` rồi tự động ngắt kết nối PPPoE vì tưởng là IP nội bộ.
- **Thực tế:** Viettel cấp rất nhiều IP public sạch thuộc dải `172.245.x.x`, `172.224.x.x`, `172.1.x.x`... Chỉ có dải `172.16.0.0/12` (từ `172.16.` đến `172.31.`) mới là Private IP.
- **RouterOS Script Chuẩn:**
  ```routeros
  :if ([:pick $ip 0 3] = "10." || [:pick $ip 0 7] = "100.64.") do={
      :set isBad true
  } else={
      :if ([:pick $ip 0 4] = "172.") do={
          :local dot2 [:find $ip "." 4]
          :if ($dot2 > 4) do={
              :local octet2 [:tonum [:pick $ip 4 $dot2]]
              if ($octet2 >= 16 && $octet2 <= 31) do={ :set isBad true }
          }
      }
  }
  ```

## 6. Lỗ Hổng Cập Nhật Scan Guard R3G Khi MikroTik Đổi IP WAN
- **Thực trạng:** Cronjob `mobiproxy-scan-guard-auto-ip` (`update_mikrotik_scan_guard.py`) chạy mỗi 5 phút hiện tại **chỉ mới cập nhật Whitelist trên MobiProxy (`test.taadaa.click`)**, hoàn toàn CHƯA cập nhật sang router R3G.
- **Rủi ro rớt toàn bộ 16 cổng proxy Admin:**
  - Trên con R3G, tất cả các file cấu hình Tinyproxy (`/etc/tinyproxy/instances/tp_*.conf`) đang ghi cứng dòng: `Allow 116.110.212.30` (IP hiện tại của `pppoe-out1`).
  - Nếu `pppoe-out1` tại Đà Nẵng đổi sang IP WAN mới: MobiProxy tự động nhận IP sau 5 phút, nhưng R3G không được cập nhật sẽ lập tức trả về lỗi `403 Forbidden` đối với toàn bộ kết nối gửi từ MikroTik sang qua đường WAN!
- **Giải pháp chuẩn:** Bổ sung logic kết nối SSH qua Tailscale `100.115.94.49` vào script `update_mikrotik_scan_guard.py`: khi IP MikroTik thay đổi, tự động sửa dòng `Allow <IP_mới>` trong các file `tp_*.conf` trên R3G và reload daemon.

## 7. Giải Mã Hiện Tượng CPU MikroTik x86 Đạt 90-95% (Băng Thông Video Farm)
- **Không quy kết cảm tính:** Khi thấy CPU RouterOS chạm ngưỡng 90-95%, CẤM tự ý quy kết cho lỗi phần mềm hay vòng lặp vô tận khi chưa đo đếm lưu lượng mạng thực tế.
- **Bản chất kỹ thuật đo kiểm:**
  - Trên interface `veth-singbox` (Container Sing-box gánh 80 máy farm): Lưu lượng trung chuyển đạt $\approx 15\text{ MB/s}$ (~120 Mbps) với mật độ gói tin cực khủng: **hơn 105.000 packets/giây**.
  - Xử lý mạng ảo hóa Container (veth bridge + iptables NAT + socket proxy) ở tốc độ >105k pps đòi hỏi kernel space liên tục xử lý ngắt mạng mềm (`irq` chiếm 15-20% CPU). Đây là tải trọng hoàn toàn tự nhiên của việc 80 điện thoại đang cày video TikTok đồng thời.
  - Bằng chứng hệ thống khỏe mạnh: Bộ nhớ RAM còn trống dồi dào (~4.8 GB / 8 GB), nhiệt độ mát và uptime duy trì liên tục nhiều tuần.
  - **Biện pháp giảm tải đã áp dụng:**
    1. Xóa sạch 524 NAT rule chết (packets = 0) giúp tinh gọn bảng NAT từ 712 về 188 rules.
    2. Tắt cờ `logging: true` trên các container Sing-box và 3proxy để không xả rác vào bộ đệm RouterOS.
    3. Giãn cách lịch trình polling Telegram Bot (`telegram-wol-bot`) lên 10-15s.
