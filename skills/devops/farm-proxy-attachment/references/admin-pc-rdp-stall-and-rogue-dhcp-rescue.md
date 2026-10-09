# Cứu Hộ Lỗi RDP Admin Treo Do Rogue DHCP & Nghẽn Định Tuyến Bất Đối Xứng (2026-10-09)

## 1. Bối cảnh & Hiện tượng (Incident Context)
- **Triệu chứng:** Người dùng mở Remote Desktop (`mstsc.exe`) trên máy Admin để kết nối vào máy Kibe (`192.168.110.123`) nhưng bị treo vĩnh viễn ở hộp thoại:
  `Connecting to: 192.168.110.123`
  `Initiating remote connection...`
- **Hiện trường mạng từ PC Kibe:**
  - Ping sang máy Admin (`192.168.110.119`): `Destination host unreachable` / 100% packet loss.
  - SSH trực tiếp sang `192.168.110.119`: Connection timed out.
  - Tuy nhiên, MikroTik (`192.168.110.2`) và toàn bộ mạng farm Wi-Fi vẫn hoạt động bình thường.

---

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause Analysis)
1. **Rogue DHCP Lease (Aruba AP Virtual Controller):**
   - Trên hạ tầng farm có Access Point Aruba IAP-315 (`192.168.110.251`, MAC `20:A6:C0:C7:6B:58`).
   - Khi card mạng máy Admin xin renew lease DHCP lúc sáng sớm, Aruba AP phát gói `DHCP Offer` dải `192.168.10.x` nhanh hơn router Ruijie (`192.168.110.1`).
   - Card mạng Ethernet của Admin PC (`22:33:4D:06:4C:26`) bị gán IP **`192.168.10.77`** với Default Gateway `192.168.10.254` (MikroTik).
2. **Nghẽn Định Tuyến Bất Đối Xứng (Asymmetric Routing Stall):**
   - **Chiều đi:** Admin PC (`192.168.10.77`) gửi gói tin RDP SYN đến Kibe PC (`192.168.110.123`) qua Default Gateway của nó là MikroTik (`192.168.10.254`). Vì MikroTik có cả 2 subnet trên `ether3`, MikroTik chuyển gói tin thẳng sang Kibe PC thành công.
   - **Chiều về:** Kibe PC (`192.168.110.123`) nhận được gói SYN và gửi gói trả lời SYN-ACK về IP nguồn `192.168.10.77`. Do Kibe PC có Default Gateway là Ruijie (`192.168.110.1`), gói tin được đẩy về Ruijie.
   - **Điểm chết:** Router Ruijie không có định tuyến (static route) cho subnet `192.168.10.0/24` của MikroTik $\rightarrow$ Ruijie drop gói tin.
   - **Hệ quả:** Bắt tay 3 bước TCP (3-way handshake) cổng 3389 không bao giờ hoàn tất $\rightarrow$ RDP client trên Admin PC bị treo cứng tại *"Initiating remote connection..."*.

---

## 3. Quy trình Cứu Hộ O(1) Qua MikroTik Jump-Host Tunnel (Zero-Touch Rescue)

Khi máy Admin bị đổi IP lạ khiến SSH trực tiếp từ Kibe PC bị đứt đoạn, sử dụng quy trình cứu hộ 4 bước sau:

### Bước 1: Định vị IP Thất lạc Trên MikroTik O(1)
Truy vấn bảng ARP của MikroTik qua REST API (`192.168.110.2:9090`) tìm theo MAC của card mạng Admin (`22:33:4D:06:4C:26`):
```python
import urllib.request, base64, json

req = urllib.request.Request('http://192.168.110.2:9090/rest/ip/arp')
req.add_header('Authorization', 'Basic ' + base64.b64encode(b'admin:N0spam@@').decode())
with urllib.request.urlopen(req, timeout=5) as resp:
    arp = json.loads(resp.read().decode())
admin_entries = [x for x in arp if '22:33:4D:06:4C:26' in x.get('mac-address', '')]
print(admin_entries)
# Kết quả: [{..., 'address': '192.168.10.77', 'status': 'reachable'}]
```

### Bước 2: Tạo Cầu Nối SSH Tạm Thời Bằng NAT Port Forward
Do Kibe PC không ping trực tiếp được `192.168.10.77`, tạo tạm 1 cặp rule `dstnat` + `srcnat` trên MikroTik chuyển tiếp cổng 2222 sang Admin PC:
```python
# 1. Port Forward dst-nat
req1 = urllib.request.Request(
    'http://192.168.110.2:9090/rest/ip/firewall/nat',
    data=json.dumps({
        'chain': 'dstnat',
        'dst-address': '192.168.110.2',
        'protocol': 'tcp',
        'dst-port': '2222',
        'action': 'dst-nat',
        'to-addresses': '192.168.10.77',
        'to-ports': '22',
        'comment': 'TEMP_SSH_ADMIN_PORT_FORWARD'
    }).encode(),
    headers={'Content-Type': 'application/json'},
    method='PUT'
)
# 2. Masquerade src-nat để Admin PC trả gói lời về thẳng MikroTik
req2 = urllib.request.Request(
    'http://192.168.110.2:9090/rest/ip/firewall/nat',
    data=json.dumps({
        'chain': 'srcnat',
        'dst-address': '192.168.10.77',
        'protocol': 'tcp',
        'dst-port': '22',
        'action': 'masquerade',
        'comment': 'TEMP_SSH_ADMIN_MASQ'
    }).encode(),
    headers={'Content-Type': 'application/json'},
    method='PUT'
)
```

### Bước 3: SSH Khóa IP Tĩnh Bất Đồng Bộ (Non-Blocking Set Static IP)
Kết nối qua cầu nối: `ssh -p 2222 -i ~/.ssh/id_ed25519_kibe_admin Admin@192.168.110.2`.
Để tránh việc đổi IP làm rớt socket SSH gây treo lệnh, ghi file `.bat` và thực thi bất đồng bộ qua `wmic process call create`:
```cmd
@echo off
timeout /t 2 /nobreak > nul
netsh interface ipv4 set address name="Ethernet" static 192.168.110.119 255.255.255.0 192.168.110.1
netsh interface ipv4 set dns name="Ethernet" static 8.8.8.8
netsh interface ipv4 add dns name="Ethernet" 1.1.1.1 index=2
route -p add 192.168.10.0 mask 255.255.255.0 192.168.110.2
```
Lệnh thực thi tách rời:
```bash
ssh -p 2222 ... Admin@192.168.110.2 "wmic process call create \"cmd.exe /c C:\\Users\\Admin\\set_static_ip.bat\""
```

### Bước 4: Hậu Kiểm, Dọn Dẹp & Hồi Phục RDP
1. **Xóa rule NAT tạm:** Gọi HTTP `DELETE` trên MikroTik REST API cho 2 rule `*33A` và `*33B`.
2. **Xóa file tạm trên Admin:** `ssh admin-farm "del C:\Users\Admin\set_static_ip.bat"`.
3. **Diệt tiến trình mstsc.exe kẹt cũ:**
   `ssh admin-farm "taskkill /f /im mstsc.exe"`
4. **Kiểm tra thông luồng 2 chiều:**
   - Từ Kibe: `ping -n 3 192.168.110.119` (<1ms, 0% loss).
   - Từ Admin: `ssh admin-farm "powershell -Command \"Test-NetConnection -ComputerName 192.168.110.123 -Port 3389\""` $\to$ `TcpTestSucceeded : True`.
   - Kết nối Internet từ Admin: Ping `8.8.8.8` và ping gateway `192.168.110.1` đều thông suốt.
