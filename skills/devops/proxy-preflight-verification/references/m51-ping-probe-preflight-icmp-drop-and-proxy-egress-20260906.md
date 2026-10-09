# Sự cố Ping Probe Preflight & MikroTik VLAN 10 ICMP Drop (Máy 51 - 2026-09-06)

## 1. Hiện trường sự cố

- **Thiết bị**: Máy 51 - Serial: `ce0616063df1094004` (Samsung S7 Android 8.0).
- **Quy trình**: `tiktok-follow` (tài khoản `duonguyen1202`).
- **Triệu chứng alert**:
  `BLOCKED: preflight device-lock/VPN fail-closed: required Android VPN is not connected: interface=wlan0 tun_up=False vpn_connected=True proxy_ip=116.107.127.192 error=ping probe failed (gateway and 8.8.8.8 unreachable)`

## 2. Thông số mạng tại hiện trường

- `wlan0`: `192.168.10.28/24` (thuộc pool DHCP VLAN 10 của router MikroTik).
- Default Route (`dumpsys connectivity`): `0.0.0.0/0 -> 192.168.10.254 wlan0`.
- Global HTTP Proxy (`settings get global http_proxy`): `192.168.110.2:20051`.
- Kết quả probe thực tế trên thiết bị:
  * `ping -c 1 -W 2 192.168.10.254`: **100% packet loss** (MikroTik cấu hình drop ICMP Echo Request trên interface VLAN 10).
  * `ping -c 1 -W 2 8.8.8.8`: **100% packet loss** (VLAN 10 không có route NAT/ICMP trực tiếp ra internet).
  * `ping -c 1 -W 2 192.168.110.2` (Máy chủ proxy): **0% packet loss** (7.55 ms — kết nối LAN hoàn toàn bình thường).
  * Egress HTTP check qua proxy (`atx-agent curl`): Trả về IP public `116.107.127.192` hợp lệ.

## 3. Phân tích nguyên nhân gốc rễ (Root Cause)

Trong `automation_core/preflight.py` (`check_android_vpn`):
1. **Thiếu mục tiêu ping proxy host**: Khi chạy chế độ Wi-Fi/router (`wlan0`), code trích xuất gateway động thành `gw_ip = "192.168.10.254"` và chỉ ping thử `(gw_ip, "8.8.8.8")`. Địa chỉ máy chủ proxy (`192.168.110.2`) trong `global_proxy` không được đưa vào danh sách kiểm tra.
2. **Đặc tính mạng HTTP Proxy**: HTTP proxy chỉ chuyển tiếp luồng TCP (HTTP/HTTPS). Gói tin ICMP (ping) không đi qua HTTP proxy. Do đó, ping `8.8.8.8` từ thiết bị trên subnet proxy-only luôn thất bại.
3. **Nghịch lý điều kiện Gate (`ping_ok AND ...`)**:
   ```python
   # Code cũ:
   if ping_ok and (wifi_validated or egress_ip_ok):
       ip_verified = True
   else:
       if not ping_ok:
           errors.append("ping probe failed (gateway and 8.8.8.8 unreachable)")
   ```
   Việc thiết bị thực hiện thành công HTTP request qua proxy ra ngoài internet và nhận về IP public `116.107.127.192` là bằng chứng mạnh mẽ nhất về kết nối mạng hoạt động. Yêu cầu bắt buộc `ping_ok` kể cả khi `egress_ip_ok == True` khiến các thiết bị trên mạng chặn ICMP bị fail-closed oan.

## 4. Giải pháp chuẩn hoá (Best Practice)

1. **Thêm proxy host vào danh sách ping probe**:
   Trích xuất host từ `global_proxy` trước khi probe ping:
   ```python
   proxy_host = _extract_proxy_host(global_proxy)
   targets = [ip for ip in (gw_ip, proxy_host, "8.8.8.8") if ip]
   ```
2. **Chống Single-Packet Ping Drop**:
   Tăng lên `ping -c 2 -W 2` và kiểm tra có ít nhất 1 gói phản hồi (`re.search(r"\b[1-9]\d*\s+received\b", ping_text)`).
3. **Ưu tiên Egress IP thành công**:
   Nếu `egress_ip_ok` đã trích xuất được public IP hợp lệ từ internet, công nhận `ip_verified = True` mà không bị chặn bởi ICMP ping:
   ```python
   if egress_ip_ok or (ping_ok and wifi_validated):
       ip_verified = True
   else:
       if not ping_ok and not egress_ip_ok:
           errors.append(f"ping probe failed ({gw_ip} and 8.8.8.8 unreachable)")
       if not (wifi_validated or egress_ip_ok):
           errors.append("Internet validation failed (Wi-Fi not VALIDATED and egress IP not valid global public IPv4)")
   ```

## 5. Cạm bẫy Unit Test & Mocking khi triển khai (Test Fixture Invariants)

1. **ADB Mock Prefix Match cho Ping (`args[:2] == ["ping", "-c"]`)**:
   - Tránh hardcode số lượng gói trong mock ADB `if args[:4] == ["ping", "-c", "1", "-W"]`. Khi code chính nâng lên `ping -c 2`, toàn bộ mock ADB trong test suite (`FakeAdb`, `OfflinePingAdb`, `NormalNetworkFailAdb`, v.v.) sẽ bị miss điều kiện và fall-through về kết quả lỗi mặc định.
   - Luôn dùng prefix `if args[:2] == ["ping", "-c"]:` và kiểm tra `ping_text` có `"1 received" in self.ping or "2 received" in self.ping or " 0% packet loss" in self.ping`.
2. **Cạm bẫy Mock Killswitch vs Egress IP Precedence**:
   - Trong các test kiểm tra killswitch router kích hoạt chặn mạng (vd `test_mapped_device_blocks_when_router_killswitch_drops_ping`), test double `FakeAdb` nếu không chỉ định `atx_curl` sẽ mặc định mang IP public (`42.114.218.81`).
   - Theo logic mới `egress_ip_ok or (ping_ok and wifi_validated)`, nếu `atx_curl` không được gán rỗng (`atx_curl=""`), thiết bị vẫn được tính là đã verify egress IP và không fail-closed. Do đó, các mock router killswitch bắt buộc phải explicit `atx_curl=""` để phản ánh đúng hiện trường killswitch ngắt toàn bộ traffic.
3. **Canary Runner Preemption (`-ForcePreempt`)**:
   - Khi chạy canary test trên máy đang bị giữ device-lock (vd job nuôi acc background), script `D:/Taadaa/tiktok-follow/scripts/run-follow.ps1` hỗ trợ tham số `-ForcePreempt` (tương ứng cờ `--force-preempt` của `follow_runner.run_follow`) để cho phép operator can thiệp có kiểm soát khi cần.
