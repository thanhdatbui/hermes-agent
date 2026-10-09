# MikroTik Mini PC Hardware Audit & AI Agent Coexistence Architecture

## 1. Phương pháp Kiểm tra Cấu hình Phần cứng MikroTik O(1) từ Host Windows

Khi cần kiểm tra cấu hình phần cứng, tài nguyên và phiên bản RouterOS của Mini PC Soft Router mà không cần mở Winbox UI:

### Bước 1: Nhận diện IP và MAC O(1)
* Kiểm tra bảng định tuyến và ARP: `ipconfig` + `arp -a`.
* Soft Router MikroTik của farm thường nằm tại `192.168.110.2` (hoặc phân giải qua domain nội bộ `mirotik1.taadaa.click`).
* OUI MAC thường bắt đầu bằng `60:BE:B4` (Routerboard / OEM Soft Router Thâm Quyến).

### Bước 2: Trích xuất thông tin truy cập từ Winbox Cache
* Vị trí lưu cấu hình WinBox trên Windows: `C:\Users\<User>\AppData\Roaming\Mikrotik\WinBox\`.
* File `settings.cfg.viw2` và `sessions/*.viw` lưu thông tin IP, port, tên người dùng (`admin`), và các session trước đó.

### Bước 3: Đọc tài nguyên phần cứng qua SSH (Non-destructive Read-Only)
Sử dụng script Python với thư viện `paramiko` để kết nối vào port 22 (`SSH-2.0-ROSSSH`):
```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.110.2', username='admin', password='<PASSWORD>', timeout=5, look_for_keys=False, allow_agent=False)

stdin, stdout, stderr = client.exec_command('/system resource print')
print(stdout.read().decode())
client.close()
```

*Lưu ý bảo vệ RouterOS SSH:*
* Không mở nhiều kết nối SSH đồng thời hoặc loop liên tục vì RouterOS có trần `max-sessions=20` trên dịch vụ IP service. Kết nối dồn dập sẽ kích hoạt cơ chế khóa hoặc làm timeout socket.
* Thực thi các lệnh đọc thông tin trong 1 session duy nhất rồi đóng kết nối ngay.

---

## 2. Thông số Phần cứng Thực tế của Mini PC Farm Kibe (`192.168.110.2`)

* **CPU:** Intel Quad-core (4 cores, 4 threads), xung nhịp ~2.6 GHz (2595 MHz), kiến trúc `x86_64` (Intel Celeron J4125 Gemini Lake).
* **RAM:** 8 GB DDR4 (7.8 GiB total, 7.1 GiB free).
* **Ổ cứng lưu trữ:** 16 GB mSATA / SSD DOM (14.5 GiB total, 14.4 GiB free).
* **OS:** MikroTik RouterOS v7.18.2 (x86_64), Level 6.
* **Cổng mạng:** 4 cổng Intel I226-V 2.5GbE (`60:BE:B4:18:B6:66`..`69`).
* **Tải vận hành định tuyến:** CPU Load ~5-6%, RAM tiêu thụ <800MB.

---

## 3. Đánh giá: Có nên cài Hermes Agent / Code Worker lên Mini PC RouterOS?

### Rào cản Kỹ thuật (Tại sao KHÔNG THỂ cài trực tiếp lên RouterOS bare-metal):
1. **Thiếu môi trường Runtime:** RouterOS là nhân Linux chuyên biệt cho mạng, không có package manager (`apt`/`yum`), không có trình biên dịch, không hỗ trợ cài Python venv và các toolchain phát triển phần mềm (`git`, `pytest`, `playwright`, `adb`, `ast`).
2. **Dung lượng ổ cứng hạn hẹp (16 GB):** Ổ 16GB chỉ đủ cho RouterOS và container siêu nhẹ (Sing-box, 3proxy). Nếu kéo venv, models, logs, git objects và cache ảnh, ổ cứng sẽ đầy trong thời gian ngắn, gây crash hệ thống file RouterOS.
3. **Container trên RouterOS bị cô lập ngặt nghèo:** Container của RouterOS v7 không có PTY shell đầy đủ, không mount được thiết bị ngoài tự do, và xử lý IPC rất hạn chế.

### Rủi ro Vận hành (Cực kỳ nghiêm trọng đối với Farm):
* **Quy tắc cô lập mạng Farm:** Router là trái tim của farm điện thoại (gánh NAT, DHCP, 35-60 line PPPoE, 80 proxy inbound cho máy S7).
* Khi Agent thực thi task (đọc repo lớn, chạy test suite, parse AST, quét log), CPU và RAM sẽ bị spike giật cục 100%.
* RouterOS bị nghẽn CPU dù chỉ 1-2 giây sẽ làm drop packets, timeout PPPoE và sập đồng loạt 80 máy farm.

---

## 4. Kiến trúc Đồng tồn tại Chuẩn (Nâng cấp Mini PC làm Hypervisor nếu muốn)

Nếu muốn tận dụng phần cứng Mini PC (CPU 4 nhân, 8GB RAM) để vừa làm router vừa chạy Agent / Server nội bộ 24/7:

1. **Nâng cấp ổ cứng:** Cắm thêm SSD M.2 NVMe hoặc SATA (128GB - 256GB).
2. **Cài Proxmox VE (PVE) làm lớp ảo hóa gốc (Hypervisor):**
   * **VM 1 (Router):** Cài **MikroTik RouterOS CHR (Cloud Hosted Router)**.
     - Cấp 2 vCPU, 1.5GB RAM.
     - Passthrough các card mạng hoặc chia VLAN chuyên biệt cho WAN/LAN.
     - Đảm bảo tài nguyên mạng được cách ly phần cứng hoàn toàn.
   * **VM 2 (Worker / Agent Host):** Cài **Ubuntu Server 24.04 LTS**.
     - Cấp 2 vCPU, 6GB RAM, 100GB SSD.
     - Cài Python 3.12, Docker, Git, Tailscale, và Hermes Agent.
3. **Kết nối:** Nối Agent VM với PC Kibe qua Tailscale Mesh VPN để điều phối an toàn, độ trễ thấp và không làm ảnh hưởng đến đường truyền farm.

---

## 5. Kiến trúc Wake-on-LAN (WoL) & Kích hoạt Bật Nguồn PC từ Xa qua MikroTik

### Bẫy Phần cứng: RouterOS x86 KHÔNG hỗ trợ "MikroTik Cloud / Back to Home"
* Khi kiểm tra `/ip cloud print` trên RouterOS x86 (bare-metal hoặc CHR), hệ thống báo cờ: `;;; Cloud services not supported on x86`.
* Tính năng **Back to Home (BTH)** và quét mã QR trên app MikroTik Mobile chỉ dành riêng cho thiết bị phần cứng RouterBOARD chính hãng (ARM/MIPS/TILE). Do đó **không thể dùng app MikroTik quét QR Back-to-Home** để bật máy trên phần cứng x86.

### Giải pháp Bật Máy Từ Xa (WoL) Hoạt Động 100% trên MikroTik x86:
1. **Lệnh WoL Nội bộ RouterOS:**
   * Script chuẩn: `/tool wol mac=0C:EF:15:37:4C:20 interface=ether3` (cho PC Kibe).
   * Script chuẩn: `/tool wol mac=22:33:4D:06:4C:26 interface=ether3` (cho PC Admin).
2. **Kích hoạt từ xa qua WireGuard có sẵn (`wg-remote`):**
   * RouterOS v7 x86 hỗ trợ WireGuard đầy đủ (interface `wg-remote`, port `13231`).
   * DDNS cập nhật tự động qua Cloudflare: `mirotik1.taadaa.click`.
   * Điện thoại (iPhone `10.200.0.2`) bật WireGuard kết nối về router -> truy cập WebFig `http://10.200.0.1` -> chạy script `wol-kibe` để bật máy.
3. **Kích hoạt từ xa qua Telegram Bot Script chạy Native trên MikroTik (ĐÃ TRIỂN KHAI 100% - 08/10/2026):**
   * *Bản chất kỹ thuật:* RouterOS v7.13+ có hàm native `[:deserialize from=json ...]`. RouterOS dùng `/tool fetch` định kỳ gọi Telegram Bot API `getUpdates` mỗi 5s, bắt các lệnh điều khiển và phát WoL trực tiếp qua cổng `ether3`.
   * *Ưu điểm vượt trội:* Không cần bật VPN trên điện thoại, không cần mở port WAN, chạy 24/7 độc lập hoàn toàn với PC host và VPS.
   * *Bẫy RouterOS REST API khi nạp Script (Cực kỳ nguy hiểm):*
     - Khi gửi script source chứa ký tự `$` qua RouterOS REST API (`PUT /rest/system/script` hoặc `PATCH`), bộ parser JSON của RouterOS sẽ **tự động mở rộng (expand) các biến `$` thành chuỗi rỗng**, làm mất toàn bộ tên biến (ví dụ `$teleLastUpdateId` bị nuốt thành khoảng trắng trống).
     - **Giải pháp bắt buộc:** Bắt buộc escape dấu đô la thành `\$` trong chuỗi JSON gửi qua REST API (ví dụ: `\$teleLastUpdateId`, `\$botToken`, `\$res`).
   * *Gửi phản hồi Telegram an toàn:* Dùng phương thức HTTP POST JSON thay vì GET URL-encode để tránh vỡ chuỗi tiếng Việt/ký tự đặc biệt:
     ```routeros
     /tool fetch url="https://api.telegram.org/bot<TOKEN>/sendMessage" http-method=post http-header-field="Content-Type: application/json" http-data="{\"chat_id\":\"<ID>\",\"text\":\"<REPLY>\"}" check-certificate=no keep-result=no
     ```
   * *Cấu hình Live trên MikroTik (`192.168.110.2`):*
     - Script: `telegram-wol-bot` (`*8A`).
     - Scheduler: `telegram-wol-bot` (`*3`, interval `5s`, start-time `startup`).
     - Bot: `@vps_hermes_Taadaa_bot` (`8486676966:AAGn2rCIUxEEWIfhRj5b8EqNq32Co9huYaQ`).
     - **Quy tắc Giao tiếp Tự nhiên (User Invariant 08/10/2026 — Chống bắt User nhớ lệnh gạch chéo `/`):**
       + Người dùng phản ánh rõ: *"ủa gì mệt v, t ra lệnh trực tiếp cho nó bật máy kibe k đc à, còn phải nhớ lệnh nữa à"*.
       + CẤM TUYỆT ĐỐI thiết kế bot chỉ nhận lệnh slash (`/bat_kibe`, `/status`). Script bắt buộc parse từ khóa ngôn ngữ tự nhiên:
         * `hasBat`: chứa `bat`, `bật`, `mo`, `mở`, `on`, `ON`.
         * `hasKibe`: chứa `kibe`, `Kibe`, `KIBE`.
         * `hasAdmin`: chứa `admin`, `Admin`, `ADMIN`.
         * `hasPing`: chứa `ping`, `Ping`, `kiem tra`, `check`, `status`, `trang thai`.
       + Phản hồi tự nhiên thân thiện tiếng Việt khi nhận lệnh ("bật máy kibe", "mở máy kibe", "kiểm tra máy", "ping kibe", "bật máy admin").

---

## 6. Cấu hình Wake-on-LAN cho PC Admin Farm (`192.168.110.119` - Huananzhi X99-F8D)

Khi cấu hình WoL cho PC Admin (dùng bo mạch chủ dual CPU Huananzhi X99-F8D, 2 cổng mạng Realtek RTL8168/8111, MAC cổng chính `22:33:4D:06:4C:26` cắm ether3):

### 1. Kiểm tra trạng thái Windows (Host OS):
* **Fast Startup:** Bắt buộc tắt (`HiberbootEnabled = 0` tại `HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power`).
* **Device Manager (Card Realtek PCIe GbE Family Controller):**
  - Tab *Power Management*: Tích chọn `Allow this device to wake the computer` và `Only allow a magic packet to wake the computer`.
  - Tab *Advanced*:
    + `Wake on Magic Packet` -> `Enabled`.
    + `Shutdown Wake-On-Lan` (hoặc `WOL & Shutdown Link Speed`) -> `Enabled` (hoặc `10 Mbps First`).

### 2. Thiết lập BIOS / UEFI Bo mạch Huananzhi X99-F8D (Cực kỳ quan trọng):
Bo mạch Huananzhi mặc định thường ngắt toàn bộ nguồn phụ khi về trạng thái S5 Shutdown để tiết kiệm điện:
1. Khi máy khởi động, nhấn **Delete** liên tục vào BIOS.
2. Vào tab **Advanced** -> **ACPI Settings** (hoặc **PCI/PCIe Subsystem Settings**):
   * `Resume By PCI/PCI-E Device` (hoặc `Power On By PCIE`) -> Đổi thành **[Enabled]**.
   * `ErP Ready` (hoặc `Deep Sleep` / `EuP`) -> BẮT BUỘC đổi thành **[Disabled]**.
     *(Bẫy chí mạng: Nếu ErP ở trạng thái Enabled, bo mạch sẽ ngắt sạch điện 5VSB cấp cho chip LAN Realtek, đèn cổng mạng tắt ngúm và card mạng không thể nhận Magic Packet).*
3. Nhấn **F10** -> **Yes** để lưu.

### 3. Dấu hiệu nhận biết cổng LAN sẵn sàng nhận lệnh WoL:
* Sau khi shutdown máy tính, nhìn phía sau cổng mạng LAN: **Đèn LED cổng LAN vẫn sáng hoặc nhấp nháy cam nhẹ** chứng tỏ card mạng đang nhận nguồn stand-by và lắng nghe gói tin Magic Packet.
* Khi đó, chỉ cần nhắn tin Telegram cho bot: *"bật máy admin"* là máy tự động khởi động.

### Điều kiện Tiên quyết Bắt buộc trên PC Host Windows (Chống Bẫy WoL Không Nhận Gói):
1. **BIOS / UEFI:** Bật **Power On By PCIE Device** (hoặc *Resume by PCI-E Device* / *Wake-on-LAN*).
2. **Windows Fast Startup (CỰC KỲ QUAN TRỌNG):** Tắt hoàn toàn **Fast Startup** trong Control Panel (*Power Options -> Choose what the power buttons do -> Bỏ tích Turn on fast startup*). Nếu bật Fast Startup, khi Shutdown Windows sẽ ngắt điện hoàn toàn card mạng Realtek, khiến NIC không nhận được Magic Packet.
3. **Card Mạng Device Manager:** Thuộc tính card LAN Realtek (`Slot04 x16`) -> Tab *Power Management* -> Tích chọn: *Allow this device to wake the computer* và *Only allow a magic packet to wake the computer*.
