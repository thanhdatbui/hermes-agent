# DHCP Dual-Server Race Condition & MikroTik VLAN10 Remediation (Taadaa Farm Kibe)

## 1. Bối cảnh & Hiện tượng (Sự cố 06/09/2026)
- **Triệu chứng trên farm**:
  - Máy farm (ví dụ Máy 13) phát cảnh báo Telegram:
    `BLOCKED: preflight device-lock/VPN fail-closed: required Android VPN is not connected: interface=wlan0 tun_up=False vpn_connected=True error=global proxy (192.168.110.2:20013) egress IP verification failed: ... dial tcp 192.168.110.2:20013: i/o timeout`.
  - Kiểm tra ADB: Thiết bị vẫn kết nối Wi-Fi AP `kibe 1`, sóng khỏe (RSSI -64 dBm, 433 Mbps).
  - Kiểm tra IP: Máy 13 nhận IP `192.168.10.70/24` (Gateway: `192.168.10.254`), trong khi phần lớn farm nhận `192.168.110.x/24` (Gateway: `192.168.110.1`).
  - Thống kê toàn farm: 54 máy nhận `192.168.110.x`, 21 máy nhận `192.168.10.x`, dù tất cả cùng bắt một SSID `kibe 1` (BSSID `b0:b8:67:5b:f8:b0`).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Xung đột 2 DHCP Server trên 1 Broadcast Domain L2**:
   - **Router Ruijie Reyee RG-EW3200GX PRO (`192.168.110.1`)**: Bật DHCP Server cấp dải `192.168.110.x`.
   - **Router MikroTik RouterOS v7.18.2 (`192.168.110.2` & `192.168.10.254`)**: Bật DHCP Server `dhcp_vlan10_kibe` cấp dải `pool_vlan10_kibe` (`192.168.10.1 - 192.168.10.80`).
   - **Lỗi gán interface trên MikroTik**: `dhcp_vlan10_kibe` bị gán trực tiếp lên cổng vật lý **`ether3`** (Untagged) thay vì sub-interface `vlan10_kibe`. Do switch/AP Ruijie không tag VLAN 10, cả 2 DHCP Server cùng phát broadcast DHCP Offer trên cùng mạng Wi-Fi.
   - Khi điện thoại xin IP, router nào phản hồi trước thì máy nhận dải đó (DHCP Race Condition).
2. **Tại sao gây rớt TCP Socket / Preflight Fail-Closed?**:
   - Cụm proxy Sing-box (port 20001..20080) nằm trên host MikroTik `192.168.110.2`.
   - Khi MikroTik khởi động lại (hoặc bảng định tuyến/ARP/NAT giữa 2 dải `192.168.10.x` và `192.168.110.x` bị trễ), các gói tin TCP từ dải `192.168.10.x` gửi tới `192.168.110.2:200xx` bị drop hoặc timeout.
   - Preflight fail-closed phát hiện không kết nối được proxy nên dừng phiên bảo vệ nick.
3. **Quy tắc giao tiếp**:
   - **TUYỆT ĐỐI KHÔNG** dùng từ ngữ gây hiểu lầm như "dải khách" để giải thích cho user khi nói về dải `192.168.10.x`. Đây là VLAN 10 của MikroTik bị gán nhầm untagged, không phải mạng Guest Wi-Fi.

## 3. Quy trình xử lý triệt để (Remediation Workflow)

### Bước 1: Vô hiệu hóa DHCP Server trên MikroTik qua REST API
Không cần can thiệp Ruijie (do Ruijie không có SSH và Web UI mã hóa client-side có rate-limit). Vô hiệu hóa DHCP Server của MikroTik để Ruijie làm DHCP Master duy nhất cho farm:

```bash
# Gửi PATCH request tới MikroTik REST API (port 9090)
curl -s -X PATCH "http://192.168.110.2:9090/rest/ip/dhcp-server/*1" \
  -u "admin:N0spam@@" \
  -H "Content-Type: application/json" \
  -d '{"disabled": "true"}'
```

Xác nhận lại trạng thái:
```bash
curl -s "http://192.168.110.2:9090/rest/ip/dhcp-server" -u "admin:N0spam@@"
# Phải trả về "disabled": "true" cho server dhcp_vlan10_kibe
```

### Bước 2: Rolling Cycle Wi-Fi đưa toàn bộ máy về dải 192.168.110.x
Dùng ADB thực hiện rolling cycle Wi-Fi theo từng lô 5 máy (stagger 2-3s) để không gây nghẽn AP:
```bash
adb -s <serial> shell "svc wifi disable && sleep 2 && svc wifi enable"
```

### Bước 3: Hậu kiểm kết nối & Egress Proxy
1. Kiểm tra IP trên máy: `adb -s <serial> shell "ip addr show wlan0"` -> Phải là `192.168.110.x` (Gateway `192.168.110.1`).
2. Kiểm tra TCP socket tới proxy: `adb -s <serial> shell "echo | toybox nc -w 3 192.168.110.2 <port>"` -> Trả về `0`.
3. Kiểm tra egress IP:
   `adb -s <serial> shell "/data/local/tmp/atx-agent curl --timeout=5s http://icanhazip.com"`
   -> Trả về đúng public IP của line proxy gán cho máy.

## 4. Codebase Invariant (Case 87 — 06/09/2026)
Trong `automation_core/preflight.py` (`check_android_vpn`):
- **Trích xuất Proxy Host trước khi Ping**: Đọc `global_proxy` từ `settings get global http_proxy` trước khi chạy vòng lặp ping, đưa `proxy_host` vào đầu danh sách target (`proxy_host`, `gw_ip`, `8.8.8.8`) với `ping -c 2` chịu trễ tốt hơn.
- **Egress IP Precedence over ICMP**: HTTP Proxy chỉ chuyển tiếp TCP, không chuyển tiếp ICMP. Nếu `atx-agent curl` đã chứng minh kết nối internet public thành công (`egress_ip_ok == True`), điều kiện nghiệm thu chấp nhận:
  `if egress_ip_ok or (ping_ok and wifi_validated): ip_verified = True`
  tránh việc router hoặc firewall chặn ICMP Echo Request làm fail-closed giả mạo.

## 5. Lưu ý Aruba IAP-315 Virtual Controller DHCP (Máy ngoại lệ)
- Khi vô hiệu hóa DHCP trên MikroTik, 96% farm (72/75 máy) lập tức nhận lease Ruijie `192.168.110.x`.
- Một số ít máy (như M31, M39, M55) gần AP Aruba IAP-315 (`192.168.110.208`) có thể bắt lease từ Virtual Controller nội bộ của Aruba (`172.31.98.1` cấp dải `192.168.10.x` với thời hạn 86400s). Dù ở dải 10.x này, các máy vẫn kết nối TCP thông suốt tới Singbox proxy `192.168.110.2` do routing nội bộ của MikroTik đã nạp đầy đủ. Khi hết hạn lease, các máy sẽ tự chuyển về dải `192.168.110.x`.

