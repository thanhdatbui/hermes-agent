# MobiProxy vs OpenWrt R3G: Anti-Scan (Scan Guard) Architecture & Direct WAN Implementation

## 1. Cơ Chế Chống Scan (Scan Guard) Của MobiProxy (`test.taadaa.click`)
- **Bản chất kỹ thuật:** 
  * Scan Guard trên box MobiProxy là cơ chế **Whitelisting ở tầng Tường lửa (Kernel Firewall - iptables / nftables)**, hoàn toàn không phải phần mềm quét hành vi tầng ứng dụng.
  * Khi mở các cổng proxy (`5101..5138`) ra Internet công cộng (Public WAN), hàng ngàn botnet toàn cầu (Shodan, Censys, bot quét proxy tự động) liên tục gửi gói tin probe/scan. Nếu để traffic này chạm vào tiến trình proxy (`3proxy`, `tinyproxy`) hoặc web server PHP-FPM, CPU và RAM của box sẽ bị quá tải, dẫn đến hiện tượng treo cứng hoặc văng mã lỗi `502 Bad Gateway`.
- **Cơ chế hoạt động thực tế (Trích xuất từ Dashboard & API):**
  * **API endpoint:** `api.php?action=proxy.scan_guard.get` / `proxy.scan_guard.save`.
  * **Payload cấu hình:**
    ```json
    {
      "enabled": true,
      "allowed_ips": "116.110.212.30\n1.52.184.202\n",
      "available": true,
      "max_ips": 256
    }
    ```
  * **Hành vi Firewall:**
    1. Thiết lập rule mặc định: `DROP` toàn bộ traffic đến từ Internet nhắm vào dải port proxy `5101..5138`.
    2. Thiết lập exception `ACCEPT`: Chỉ chấp nhận các gói tin có IP nguồn nằm trong danh sách `allowed_ips` (IP WAN của Router MikroTik Đà Nẵng và IP Host Kibe).
    3. Cập nhật tức thì vào kernel iptables (O(1)) mà không cần khởi động lại dịch vụ proxy, không làm rớt kết nối đang chạy.
- **Cơ chế đồng bộ IP động (Dynamic IP Sync):**
  * Do Router MikroTik ở Đà Nẵng dùng đường truyền PPPoE IP động, mỗi khi quay PPPoE đổi IP mới thì IP cũ sẽ bị Scan Guard chặn.
  * Cron job `mobiproxy-scan-guard-auto-ip` (Job ID: `3a92a822ace9`, chạy `*/5 * * * *`) thực thi script `update_mikrotik_scan_guard.py` để tự động phát hiện IP WAN MikroTik mới và gọi API cập nhật whitelist lên box MobiProxy.

---

## 2. So Sánh Mô Hình Mạng: MobiProxy vs Xiaomi R3G

| Tiêu chí | Cụm MobiProxy (`test.taadaa.click`) | Cụm Xiaomi R3G (`tb.taadaa.click`) |
| :--- | :--- | :--- |
| **Bản chất đường truyền** | **Direct WAN (Internet công cộng)** | **Mạng riêng ảo Tailscale (WireGuard)** |
| **Cổng mở ra ngoài** | Mở cổng `5101..5138` ra Public IP WAN | Đóng toàn bộ WAN (`DROP`), chỉ mở trên `tailscale0` |
| **Nguy cơ bị scan** | Rất cao (bắt buộc phải có Scan Guard) | Bằng 0 (Hacker/botnet bên ngoài không thấy port) |
| **Tải phần cứng (CPU/RAM)** | Nhẹ (dùng Hardware NAT của SoC, iptables O(1)) | Nặng (vừa giải mã VPN WireGuard vừa chạy proxy) |
| **Khả năng tương thích S7** | Thông qua Sing-box MikroTik forward ra WAN | Cần PC Admin làm relay bridge hoặc mở WAN thật |

---

## 3. Quy Trình Chuyển Đổi R3G Sang Chế Độ Direct WAN + Scan Guard (Chuẩn MobiProxy)
Nếu muốn giải phóng CPU cho R3G, tận dụng Hardware NAT và bỏ hoàn toàn VPN Tailscale, bắt buộc phải thi công đúng 4 bước theo thứ tự sau (TUYỆT ĐỐI KHÔNG làm tắt):

### Bước 1: Khởi động & Cấp phát DDNS Cloudflare
- Cắm nguồn router R3G, đảm bảo kết nối mạng ra Internet ổn định.
- Cấu hình Cloudflare DDNS trên OpenWrt (`ddns-scripts`) cập nhật IP WAN thật của R3G về subdomain `tb.taadaa.click`.

### Bước 2: Cấu hình Tường Lửa Whitelist (Scan Guard) trên OpenWrt
- Tạo ipset chứa danh sách IP được phép kết nối (IP MikroTik Đà Nẵng):
  ```sh
  ipset create ALLOWED_FARMS hash:ip
  ipset add ALLOWED_FARMS 116.110.212.30
  ```
- Thêm rule firewall vào `/etc/firewall.user` (hoặc fw3/fw4):
  ```sh
  # Chặn toàn bộ IP ngoài dải whitelist kết nối vào port proxy 5101-5116
  iptables -I INPUT -p tcp -m multiport --dports 5101:5116 -m set --match-set ALLOWED_FARMS src -j ACCEPT
  iptables -A INPUT -p tcp -m multiport --dports 5101:5116 -j DROP
  ```
- **Lưu ý sống còn:** TUYỆT ĐỐI KHÔNG sửa lung tung zone firewall mặc định của OpenWrt (`src='tailscale'` hay drop all INPUT) kẻo bị khóa cổng SSH/quản trị.

### Bước 3: Đồng bộ IP Tự Động
- Cập nhật script `update_mikrotik_scan_guard.py` để khi MikroTik đổi IP, script sẽ SSH hoặc gọi API cập nhật IP mới vào ipset `ALLOWED_FARMS` trên R3G song song với MobiProxy.

### Bước 4: Chuyển Cấu Hình Sing-box & Nghiệm Thu
- Sau khi kiểm tra từ máy ngoài (PC Kibe / MikroTik) cURL thành công tới `tb.taadaa.click:5101` ra đúng IP Viettel Thái Bình, mới được phép trỏ outbound của Sing-box MikroTik sang `tb.taadaa.click`.
- Dàn S7 vẫn giữ nguyên proxy LAN `192.168.110.2:202xx` (không đụng vào cài đặt trên điện thoại).

---

## 4. Phục Hồi Khẩn Cấp R3G Khi Bị Treo / Mất Liên Lạc (Reboot Protocol)
- **Bản chất khi R3G offline:** R3G chạy OpenWrt lưu cấu hình mạng trong flash (`/etc/config/`). Khi bot cấu hình sai firewall hoặc tinyproxy fork quá tải gây OOM kill tailscaled, R3G chỉ bị treo tạm thời trong RAM.
- **Thao tác vật lý duy nhất cần thiết:** Rút nguồn cắm lại (Power Cycle). KHÔNG reset nút cứng, KHÔNG cần cài lại ROM, KHÔNG cần cắm cáp cứu hộ phức tạp.
- **Tiến trình khởi động tự phục hồi:** Sau khi cắm lại nguồn (2-3 phút), `/etc/rc.local` tự chạy:
  1. Khởi động daemon `tailscaled` (port 41641) và kết nối lại Tailnet (`100.115.94.49`).
  2. Chờ 16 line PPPoE (`pppoe-wan`, `pppoe-wan_sub2..17`) nhận đủ IPv4.
  3. Kích hoạt `/root/generate_all_proxies.sh` spawn lại 16 port proxy (`5141..5148`, `5151..5158`).
- **Hậu kiểm O(1) sau khi router online:**
  * Socket probe port 22, 5141 qua Tailscale IP `100.115.94.49`.
  * Quét nhanh danh sách proxy 5141-5158 bằng `urllib.request` để kiểm chứng IP public.
  * Khóa máy bằng `with_device_lock.py` và cURL kiểm chứng qua `atx-agent` từ chính điện thoại thật M203/M208.
