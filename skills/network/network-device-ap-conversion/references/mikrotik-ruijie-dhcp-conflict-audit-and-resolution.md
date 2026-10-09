# MikroTik & Ruijie DHCP Conflict Audit and Resolution Guide

## 1. Bản Chất Sự Cố Xung Đột DHCP Kép (Dual DHCP Conflict)

Trên hệ thống Phone Farm kết hợp nhiều thiết bị mạng (MikroTik RouterOS làm Core Routing / Singbox Proxy, Ruijie Reyee EW3200GX-PRO làm Switch/Gateway LAN, và Aruba Instant AP phát Wi-Fi):

### Nguyên nhân gốc rễ (Root Cause)
- **Cùng 1 Broadcast Domain Layer 2:** Cổng `ether3` của MikroTik cắm trực tiếp vào switch/LAN của Ruijie mà không phân tách VLAN ở switch port (traffic untagged, `vlan10_kibe` có 0 rx-packet).
- **2 DHCP Server cùng phát:**
  1. MikroTik chạy DHCP Server `dhcp_vlan10_kibe` bind vào `ether3`, cấp dải `192.168.10.x/24` (gateway `192.168.10.254`).
  2. Ruijie EW3200GX-PRO chạy DHCP Server cấp dải `192.168.110.x/24` (gateway `192.168.110.1`).
  3. Aruba Instant Virtual Controller (AP3 `20:a6:c0:c7:6b:58`) cũng tham gia phản hồi DHCP Offer.
- **Hậu quả:** Race condition — thiết bị nào nhận gói Offer trước sẽ bind dải đó:
  - 54 điện thoại nhận `192.168.110.x` (Ruijie cấp).
  - 21 điện thoại nhận `192.168.10.x` (MikroTik cấp).
  - Bảng DHCP Lease trên MikroTik xuất hiện nhiều cờ `conflict`.

---

## 2. Kỹ Thuật Bắt Gói DHCP Discover Thực Nghiệm (Empirical DHCP Audit)

Để xác định chính xác mọi DHCP Server đang phát trên LAN trong vòng 3 giây mà không cần Wireshark hay đoán mò:

```python
import socket, struct

def create_dhcp_discover():
    xid = b'\x39\x03\xf3\x26'
    mac = b'\x00\x11\x22\x33\x44\x55'
    packet = b'\x01\x01\x06\x00' + xid + b'\x00\x00\x80\x00'
    packet += b'\x00'*16 + mac + b'\x00'*10 + b'\x00'*192 + b'\x63\x82\x53\x63'
    packet += b'\x35\x01\x01\xff' # Option 53: Discover
    return packet

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.settimeout(3.0)
s.bind(('', 68))
s.sendto(create_dhcp_discover(), ('255.255.255.255', 67))

while True:
    try:
        data, addr = s.recvfrom(2048)
        offered_ip = socket.inet_ntoa(data[16:20])
        # Parse options 54 (Server ID), 1 (Mask), 3 (Gateway)
        idx, server_id, gw = 240, None, None
        while idx < len(data):
            opt = data[idx]
            if opt == 255: break
            if opt == 0: idx += 1; continue
            opt_len = data[idx+1]
            val = data[idx+2:idx+2+opt_len]
            if opt == 54: server_id = socket.inet_ntoa(val)
            elif opt == 3: gw = socket.inet_ntoa(val[:4])
            idx += 2 + opt_len
        print(f"DHCP Offer from {addr[0]}: ServerID={server_id}, OfferedIP={offered_ip}, GW={gw}")
    except socket.timeout:
        break
s.close()
```

---

## 3. Đánh Giá Khả Thi Can Thiệp (MikroTik vs Ruijie)

| Tiêu chí | MikroTik RouterOS (192.168.110.2) | Ruijie Reyee (192.168.110.1) |
| :--- | :--- | :--- |
| **Giao tiếp quản trị** | REST API (`:9090/rest`), WinBox (`:8291`) | Web UI (`:80`, `:443`). **SSH / Telnet ĐÓNG**. |
| **Xác thực tự động** | Basic Auth chuẩn qua API, scriptable 100% | Mã hóa client-side GibberishAES qua JS. |
| **Bảo vệ chống Brute-force** | Configurable | **Cực đoan:** Sai 3 lần khóa 60s, sai 10 lần khóa 10 phút. |
| **Rủi ro khi script can thiệp** | Rất thấp (có thể rollback tức thì qua REST API) | Cao (dễ lock Web UI, mất quyền truy cập). |
| **Kết luận lựa chọn** | **Tắt DHCP trên MikroTik** | **Không đụng cấu hình Ruijie bằng script** |

---

## 4. Phân Tích An Toàn Dịch Vụ Farm Khi Chuyển Sang 192.168.110.x

1. **Proxy Singbox:**
   - Cụm proxy Singbox chạy container trên MikroTik listen tại `192.168.110.2:20001..20080`.
   - Điện thoại gán `settings put global http_proxy 192.168.110.2:200xx`.
   - Khi điện thoại mang IP `192.168.110.x`, nó nằm cùng broadcast domain L2 với `192.168.110.2` $\rightarrow$ Kết nối proxy là direct L2 ARP/TCP, hoàn toàn không cần routing qua default gateway.
2. **Kibe PC & Admin PC:**
   - Đang có DHCP reservation trên MikroTik (`192.168.110.123` và `192.168.110.119`).
   - BẮT BUỘC đặt Static IP trực tiếp trong card mạng Windows trước khi tắt DHCP MikroTik để tránh bị Ruijie cấp IP lạ làm đứt SSH/RDP/ADB.
3. **Rolling Reconnection điện thoại:**
   - Không reboot điện thoại đồng loạt.
   - Dùng lệnh ADB mềm: `adb -s <serial> shell "svc wifi disable && sleep 2 && svc wifi enable"`.
   - ADB qua USB/TCP vẫn duy trì, điện thoại tự renew IP mới từ Ruijie.

---

## 5. Chẩn Đoán Máy Kẹt Dải 192.168.10.x Do Aruba VC & Logcat DhcpClient

Khi một số máy sau khi cycle Wi-Fi vẫn không đổi sang `192.168.110.x` mà giữ nguyên `192.168.10.x`:

### 1. Trích xuất DHCP Server ID & thời hạn lease qua ADB
```bash
adb -s <serial> logcat -d -s DhcpClient:V | grep -E "Got pending lease|Confirmed lease" | tail -2
```
- **Khuôn mẫu Aruba VC (kẹt dải 10.x):**
  `Got pending lease: IP address 192.168.10.x/24 Gateway 192.168.10.254 ... DHCP server /192.168.110.208 ... lease 86400 seconds`
  $\rightarrow$ Server cấp là Aruba Virtual Controller AP3 (`192.168.110.208`, MAC `20:a6:c0:c7:6b:58`) giữ lease 24 tiếng (86400s).
- **Khuôn mẫu Ruijie chuẩn (dải 110.x):**
  `Got pending lease: IP address 192.168.110.x/24 Gateway 192.168.110.1 ... DHCP server /192.168.110.1 ... lease 7200 seconds`

### 2. Pitfall & Đánh giá ảnh hưởng vận hành
- **Lý do cycle Wi-Fi không đổi dải:** Khi tắt/bật Wi-Fi, điện thoại gửi `DHCPREQUEST` với `request=192.168.10.x serverid=192.168.110.208`, Aruba VC lập tức renew lease 86400s nhanh hơn Ruijie phản hồi. Do đó lặp lại lệnh cycle Wi-Fi mềm sẽ không kéo được máy về `192.168.110.x` nếu chưa clear lease/tắt DHCP trên Aruba VC.
- **An toàn dịch vụ (Proxy Singbox):** Dù mang IP `192.168.10.x`, thiết bị vẫn ping và kết nối bình thường tới proxy Singbox `192.168.110.2:200xx` thông qua gateway `192.168.10.254` (0% packet loss, RTT 5-11ms), không gây nghẽn hay đứt gãy tức thì các flow automation.
