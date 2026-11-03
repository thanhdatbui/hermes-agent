# R3G OpenWrt & MikroTik Proxy Integration Sop

## 1. Bản Chất Kiến Trúc R3G OpenWrt (Thái Bình)
- **16 port Tinyproxy:** `5141..5148` (nhánh LAN2) và `5151..5158` (nhánh LAN1).
- **Elite Anonymous Configuration:**
  - Trong `/root/generate_all_proxies.sh` và `/etc/tinyproxy/instances/tp_51*.conf`, BẮT BUỘC thay `ViaProxyName "..."` bằng:
    ```text
    DisableViaHeader Yes
    ```
  - Kiểm tra qua `httpbin.org/headers`: Header `Via` và `X-Forwarded-For` hoàn toàn biến mất (100% Elite).
- **Chống Router Tự Reboot / Sập Nguồn:**
  - Vô hiệu hóa `watchcat ping_reboot` trong `/etc/config/watchcat` (chống tự sát khi mạng rớt ping quốc tế).
  - Gỡ bỏ vĩnh viễn cronjob `killall tinyproxy` mỗi 60 giây trong crontab.
  - Xóa sạch file rác và binary lạ khỏi `/overlay` để đảm bảo dung lượng trống luôn $\ge 10\text{ MB}$.
- **Cơ Chế Kết Nối Dự Phòng SSH:**
  - Luôn thử IP Tailscale `100.115.94.49` trước (timeout 2s).
  - Nếu timeout, fallback ngay sang domain WAN `tb.taadaa.click` (timeout 5s).

## 2. Đồng Bộ Tự Động Whitelist MikroTik -> R3G
- Khi MikroTik Đà Nẵng đổi IP WAN (`pppoe-out1`), script `update_mikrotik_scan_guard.py` (chạy mỗi 5 phút) BẮT BUỘC đồng thời:
  1. Cập nhật Whitelist trên **MobiProxy** qua API `proxy.scan_guard.save`.
  2. SSH vào **R3G Thái Bình** nạp dòng `Allow <IP_mới>` vào 16 file config Tinyproxy và gửi tín hiệu `killall -HUP tinyproxy`.

## 3. Kiến Trúc DNAT vs Singbox Container
- **Singbox Container trên MikroTik:**
  - Gánh 160 port video TikTok đẩy CPU x86 lên 90–95% do nghẽn card mạng ảo `veth`.
  - Tối ưu bước 1: Đổi log Singbox từ `info` về `warn` để giảm tải I/O.
- **Kernel DNAT (Tương lai khi bỏ Singbox):**
  - MikroTik RouterOS NAT rule `to-addresses` chỉ nhận IP số, KHÔNG nhận domain name.
  - Muốn dùng Kernel DNAT cần: (a) Gỡ bỏ mật khẩu User/Pass trên MobiProxy; (b) Cấu hình định tuyến đối xứng (Symmetric Routing) trên OpenWrt R3G.
