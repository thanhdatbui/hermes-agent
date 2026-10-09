# Android Active Default Network: None & Policy Routing Unreachable Trap (2026-10-09)

## 1. Hiện Tượng & Triệu Chứng
Sau khi thực hiện chu kỳ toggle Wi-Fi (`svc wifi disable && sleep 1 && svc wifi enable`) hoặc khi thiết bị Android (Samsung S7) vừa tái kết nối Wi-Fi:
1. `ip addr show wlan0`: Thấy interface đã có IP hợp lệ từ DHCP Ruijie (`inet 192.168.110.23/24`).
2. `ping 192.168.110.1` hoặc `ping 192.168.110.2`: Phản hồi tức thì, 0% packet loss (ICMP hoạt động).
3. **Tuy nhiên, lệnh socket TCP/HTTP (như `toybox nc` hoặc `/data/local/tmp/atx-agent curl`) tới proxy LAN `192.168.110.2:20016` bị ném lỗi ngay lập tức:**
   ```
   curl.go:114: Get "http://ifconfig.me/ip": proxyconnect tcp: dial tcp 192.168.110.2:20016: connect: network is unreachable
   ```
   hoặc
   ```
   nc: connect: Network is unreachable
   ```
4. Runner automation đọc thấy lỗi này lập tức fail-closed: `global proxy (192.168.110.2:20016) egress IP verification failed: connect: network is unreachable`.

---

## 2. Phân Tích Bản Chất: Android Policy Routing & ConnectivityService Delay

### Tách Biệt 2 Tầng Mạng:
1. **Tầng Linux Kernel & Driver Wi-Fi (Lớp 1-3):**
   - Wpa_supplicant hoàn tất 4-way handshake (`COMPLETED`).
   - DHCP client nhận IP `192.168.110.23`.
   - Routing table `1014` có route cục bộ `192.168.110.0/24 dev wlan0`.
2. **Tầng Android Framework ConnectivityService (Lớp Chính Sách):**
   - Sau khi driver báo kết nối, `ConnectivityService` tạo `NetworkAgentInfo` và chạy ngầm kiểm tra captive portal probe (`connectivitycheck.gstatic.com`).
   - **Khoảng trễ 3–8 giây:** Trong khi probe đang chạy, hệ thống chưa chính thức bầu `wlan0` làm default network.
   - Khi chạy lệnh:
     ```bash
     dumpsys connectivity | grep "Active default network"
     ```
     kết quả trả về:
     ```
     Active default network: none
     ```

### Bẫy Luật Định Tuyến (`ip rule`):
Kiểm tra `ip rule` trên Samsung S7:
```
0:      from all lookup local
10000:  from all fwmark 0x0/0x10000 lookup 99
10500:  from all oif wlan0 uidrange 0-0 lookup 1014
...
22000:  from all fwmark 0x0/0xffff lookup 1014
23000:  from all fwmark 0x0/0xffff uidrange 0-0 lookup main
32000:  from all unreachable
```
- Khi tiến trình shell không có `fwmark` và không chỉ định rõ outgoing interface (`oif`), và `Active default network: none`, kernel không tìm thấy routing table nào khớp cho socket TCP khởi tạo.
- Gói tin rơi thẳng vào rule cuối cùng: `32000: from all unreachable`.
- Kernel trả ngay mã lỗi `ENETUNREACH` (`Network is unreachable`) cho syscall `connect()`.

---

## 3. Quy Trình Chẩn Đoán & Khắc Phục O(1)

1. **Kiểm tra trạng thái default network:**
   ```bash
   adb -s <serial> shell "dumpsys connectivity | grep -E 'Active default network|NetworkAgentInfo.*WIFI'"
   ```
   - Nếu thấy `Active default network: none` nhưng `wlan0` đã có IP $\to$ Đây là trạng thái **đang chuyển tiếp (transitioning)**, không phải lỗi mạng hỏng.
2. **Thời gian chờ tự ổn định:**
   - Chỉ cần sleep chờ **5–8 giây**.
   - Khi ConnectivityService ghi nhận `Active default network: 1131` (gán network ID), luật định tuyến tự động kích hoạt và socket TCP sẽ kết nối bình thường (`exit: 0`).
3. **Quy tắc an toàn cho preflight runner:**
   - Khi gặp `connect: network is unreachable` ngay sau khi toggle Wi-Fi, không phát alert giả mạo hay reboot máy/router.
   - Bổ sung retry ngắn 5 giây kiểm tra lại `dumpsys connectivity` trước khi đưa ra kết luận fail-closed.
