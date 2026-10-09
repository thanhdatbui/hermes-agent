# Samsung S7 Android 8.0 DHCP VLAN Mismatch, Rogue SSID & Proxy TCP Timeout (2026-09-06)

## 1. Hiện tượng & Triệu chứng Cảnh báo (Farm Alert)
* **Quy trình bị dừng**: `tiktok-follow` / `tiktok-feed` / preflight chung.
* **Thông báo lỗi**:
  ```text
  BLOCKED: preflight device-lock/VPN fail-closed: required Android VPN is not connected:
  interface=wlan0 tun_up=False vpn_connected=True error=global proxy (192.168.110.2:20013) egress IP verification failed:
  dial tcp 192.168.110.2:20013: i/o timeout; direct/wlan0 egress IP verification failed
  ```
* **Bản chất**: Preflight fail-closed chặn đứng 100% việc rò rỉ Direct IP, bảo vệ an toàn tài khoản khi proxy không thể kết nối.

---

## 2. Phân tích Hiện trường Đa tầng (Triage 3 Tầng)

### Tầng 2: Proxy Container Sing-box (Host)
* Khi probe từ Host (`socket.connect_ex` tới `192.168.110.2:20013`): `0` (PORT OPEN).
* Egress IP qua proxy từ Host trả về bình thường (ví dụ: `116.107.127.192`).
* $\rightarrow$ Upstream Proxy Box và Sing-box container hoàn toàn bình thường, lỗi không nằm ở server proxy.

### Tầng 1: Wi-Fi / DHCP Subnet Mismatch & Rogue SSID (Thiết bị)
1. **DHCP Subnet Mismatch (VLAN 10 vs Farm Subnet 110)**:
   - Thiết bị nhận IP dải `192.168.10.x/24` (Gateway `192.168.10.254` do DHCP server MikroTik `dhcp_vlan10_kibe` cấp lease 24h), trong khi toàn bộ dàn máy farm và Sing-box proxy container nằm tại dải `192.168.110.x/24`.
   - Khi firewall/routing giữa VLAN 10 và subnet 110 bị drop hoặc nghẽn, ping ICMP có thể vẫn thông nhưng kết nối TCP socket (`toybox nc`, `atx-agent curl`) tới `192.168.110.2:20013` bị `i/o timeout`.
2. **Cạm bẫy lệnh `cmd wifi` trên Samsung S7 (Android 8.0.0 Oreo)**:
   - Chạy `cmd wifi forget-network <id>` trên Android 8 trả về `No shell command implementation` (do command framework này chỉ xuất hiện từ Android 9/10+).
   - Tuyệt đối không dùng `cmd wifi` trong script automation cho dàn S7 Android 8.
3. **Xung đột Rogue SSID ngầm (Background Scan Interference)**:
   - Trong `dumpsys wifi`, thiết bị lưu các SSID lạ/cũ (`Dinh Khoi_5G`, `Dat-1`, `BOX 2`).
   - Radio Wi-Fi liên tục quét ngầm và nhận `AUTHENTICATION_FAILURE` từ các SSID này, gây drop gói tin tức thời và làm timeout lệnh probe `atx-agent curl` (vốn có timeout ngắn 3–5s).

---

## 3. Quy trình Phục hồi Chuẩn (Zero-Risk Recovery)

1. **Khởi động lại Thiết bị (Hardware Radio Reset)**:
   - Trên Samsung S7, khi driver Wi-Fi hoặc DHCP client bị kẹt lease cũ, lệnh mềm `svc wifi enable` đôi khi không xin lại được IP mới.
   - Reboot thiết bị: `adb -s <serial> reboot`. Chờ ~40s cho máy online và `sys.boot_completed=1`.
2. **Làm mới kết nối Wi-Fi AP Chuẩn**:
   - `adb -s <serial> shell "svc wifi disable && sleep 3 && svc wifi enable"`
   - Đảm bảo máy kết nối vào đúng SSID theo zone:
     * Máy 01–40: `kibe 1` (Aruba AP 1).
     * Máy 41–80: `kibe 2` (Aruba AP 2).
3. **Gán lại Cấu hình Proxy Farm ADB**:
   - `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py --machines <N>`
   - Script tự động tắt captive portal và gán global proxy `192.168.110.2:200XX`.
4. **Kiểm tra Thông luồng TCP & Preflight O(1)**:
   - Kiểm tra TCP socket từ máy:
     `adb -s <serial> shell "echo | toybox nc -w 3 192.168.110.2 200XX"` $\rightarrow$ Trả về `0`.
   - Kiểm tra preflight bằng Python:
     ```python
     from automation_core.adb import AdbClient
     from automation_core.preflight import check_android_vpn
     adb = AdbClient(serial="<serial>")
     res = check_android_vpn(adb, required=True, interface="wlan0", timeout=8.0)
     print(res.allowed, res.proxy_ip)
     ```
   - Chạy canary test theo đúng quy trình trước khi mở lại cho cron batch.
