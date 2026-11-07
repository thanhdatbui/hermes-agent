# R3G OpenWrt Tinyproxy Restoration & Recovery SOP

## 1. Triệu chứng sự cố
- Client, GPM profile hoặc MikroTik DNAT tới các port `5141..5158` (domain `tb.taadaa.click`) bị `i/o timeout`, `HTTP 502 Bad Gateway`, hoặc `Connection Refused`.
- Kiểm tra script đồng bộ whitelist `update_mikrotik_scan_guard.py` văng lỗi:
  ```text
  [WARN] R3G whitelist sync via 100.115.94.49 failed: killall: tinyproxy: no process killed
  ```
- **Bản chất kỹ thuật:** Router R3G phần cứng vẫn hoạt động bình thường, 16 line PPPoE vẫn online trong `ubus call network.interface dump`, nhưng các tiến trình `tinyproxy` trên các port bị crash/dừng ngầm, dẫn đến cổng TCP bị đóng hoặc drop request.

## 2. Quy trình phục hồi chuẩn O(1) qua Tailscale SSH
Truy cập vào R3G qua Tailscale IP `100.115.94.49:22` (username `root`, password `password`):

### Bước 1: Khởi động lại toàn bộ 16 instances Tinyproxy
Chạy script tự động hóa gốc đã cấu hình sẵn trên OpenWrt:
```sh
/bin/sh /root/generate_all_proxies.sh
```
Script này thực hiện:
1. Kill sạch tiến trình tinyproxy cũ tồn đọng.
2. Xóa các file PID và config cũ bị kẹt trong `/var/run/` và `/etc/tinyproxy/instances/`.
3. Quét IP thực tế của từng interface PPPoE (`pppoe-WAN2`, `pppoe-wan_sub2..8`, `pppoe-wan`, `pppoe-wan_sub11..17`).
4. Gán rule định tuyến `ip rule add from <ip> table <tbl>` và tạo config bind tương ứng cho 16 port `5141..5148` & `5151..5158`.
5. Nạp firewall allow zone `tailscale` cho dải port.

### Bước 2: Kiểm tra trạng thái Listen trên R3G
```sh
netstat -tulpn | grep tinyproxy
```
Xác nhận có đủ 16 dòng `0.0.0.0:5141..5158` ở trạng thái `LISTEN`.

### Bước 3: Đo kiểm Egress thực tế 2 chiều (Ground Truth)
1. **Kiểm tra trực tiếp từ R3G:**
   ```sh
   curl -x http://127.0.0.1:5141 https://api.ipify.org?format=json
   ```
   Phải trả về đúng IP Viettel Thái Bình tương ứng của line `WAN2`.
2. **Kiểm tra từ PC / MikroTik qua domain `tb.taadaa.click`:**
   ```python
   import urllib.request
   opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': 'http://tb.taadaa.click:5141'}))
   print(opener.open('https://api.ipify.org?format=json', timeout=5).read().decode())
   ```
3. **Kiểm tra cổng DNAT trên MikroTik (`192.168.110.2:202xx`):**
   ```python
   opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': 'http://192.168.110.2:20203'}))
   print(opener.open('https://api.ipify.org?format=json', timeout=5).read().decode())
   ```
