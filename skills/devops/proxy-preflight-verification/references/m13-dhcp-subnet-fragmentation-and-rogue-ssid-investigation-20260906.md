# Case Study: Điều tra Máy 13 - Phân mảnh DHCP Subnet (192.168.10.x vs 192.168.110.x) & Rogue SSID (2026-09-06)

## 1. Hiện trường & Bối cảnh
- **Thiết bị**: Máy 13 (Serial: `988678543555413857`, Nick: `dangmwpcdnh`).
- **Proxy cấu hình**: `192.168.110.2:20013` (Sing-box container trên MikroTik).
- **Triệu chứng ban đầu**: Preflight fail-closed chặn máy không cho chạy TikTok. Host probe socket 20013 trả về OPEN và HTTP egress trả về IP `116.107.127.192`, nhưng thiết bị không thể kết nối ra internet qua proxy.

## 2. Root Cause Triage 3 tầng

1. **Tầng 2 (Upstream Proxy Box / Sing-box Port 20013)**:
   - Host probe TCP: `192.168.110.2:20013` -> `connect_ex = 0` (OPEN).
   - Máy 1 (`192.168.10.34`) probe TCP tới `192.168.110.2:20013` -> 0 (OPEN).
   - **Kết luận**: Cụm proxy Sing-box hoàn toàn sống và hoạt động bình thường.

2. **Tầng 1 (Wi-Fi / DHCP Subnet Mismatch & Rogue SSID)**:
   - **Phân mảnh Subnet Farm**:
     * Router MikroTik (`192.168.110.2` trên `ether3`) có cả IP `192.168.10.254/24` và chạy DHCP server `dhcp_vlan10_kibe` cấp dải `192.168.10.1-192.168.10.80`.
     * Switch Ruijie / AP (`192.168.110.1`) cấp dải `192.168.110.0/24`.
     * Máy 13 nhận IP `192.168.10.70/24` với Gateway `192.168.10.254`.
   - **Rogue SSID Scan Loop**:
     * Máy 13 có SSID rác `Dinh Khoi_5G` (ID 2) trong config Wi-Fi.
     * Android liên tục kích hoạt chu kỳ scan ngầm và báo `AUTHENTICATION_FAILURE` (`wlan0: CTRL-EVENT-SSID-TEMP-DISABLED id=0 ssid="Dinh Khoi_5G" auth_failures=1`).
     * Dù ICMP ping tới `192.168.110.2` vẫn pass (0% loss), nhưng các luồng TCP SYN sang port proxy 20013 bị timeout (`dial tcp 192.168.110.2:20013: i/o timeout`).

## 3. Cạm bẫy kỹ thuật rút ra

1. **Cạm bẫy `toybox nc -z`**:
   - Lệnh `toybox nc` trên Android không hỗ trợ flag `-z` (`nc: Unknown option z`).
   - Cú pháp chuẩn O(1) để probe TCP port: `adb shell "echo | toybox nc -w 2 <ip> <port>; echo \$?"` (0 = OPEN, 1 = TIMEOUT/REFUSED).

2. **ICMP Ping vs TCP Handshake**:
   - Ping gateway hoặc server thành công KHÔNG đồng nghĩa TCP socket tới proxy thông suốt.
   - Luôn dùng `echo | toybox nc -w 2` hoặc `atx-agent curl` để xác nhận TCP connection thực tế.

3. **Xử lý dứt điểm**:
   - **Xóa mạng rác**:
     * *Android 9/10+*: `adb shell "cmd wifi forget-network <id>"`.
     * *Samsung S7 Android 8.0 (Oreo)*: Lệnh `cmd wifi` sẽ báo lỗi `No shell command implementation.` và không có root/wpa_cli. Bắt buộc xóa mạng rác qua UI Settings:
       `adb shell "am start -a android.settings.WIFI_SETTINGS"` sau đó dùng UIAutomator / atx-agent (port 7912) bấm giữ SSID rác và chọn *Quên mạng* (*Forget network*).
   - `adb shell "svc wifi disable && sleep 2 && svc wifi enable"` (reset adapter để nhận lại IP sạch; nếu vẫn kẹt lease cũ, `adb reboot` để reset sạch radio driver và renew DHCP).
   - Chạy script `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py --machines <N>` để refresh proxy và captive portal settings.
