# Chẩn đoán Sự cố MikroTik "Tự Reset / Reboot" & Khóa Bảo mật Quản trị WAN (SSH/Winbox)

## 1. Bản chất Hiện tượng "MikroTik Tự Reset Hoài"

Khi người dùng báo *"MikroTik bị gì tự reset hoài thế"*, cần phân biệt ngay 2 lớp nguyên nhân hoàn toàn khác nhau:

### Lớp 1: Reboot Phần cứng / Bo Mạch Thật Sự (Dấu hiệu Tiếng "Tíc")
- **Dấu hiệu âm thanh ("Tiếng tíc"):**
  1. Khi bo mạch PC x86 (Intel J4125) hoàn tất chu kỳ POST hoặc BIOS reset, **còi chip (buzzer) trên mainboard sẽ phát ra 1 tiếng "tíc" (beep)**.
  2. Đồng thời, **rơ-le bảo vệ nguồn (Power Relay)** trong adapter nguồn hoặc bộ ngắt điện có thể nhảy "tạch/tíc" khi sụt áp hoặc ngắt tải.
  $\rightarrow$ Nếu người dùng ở gần nghe thấy tiếng "tíc" và mạng đứt, **100% là máy đã bị REBOOT CỨNG PHẦN CỨNG**, không phải reset mềm các line PPPoE.

- **Thủ phạm Kích hoạt Reboot Phần cứng:**
  1. **RouterOS Watchdog Timer (`/system watchdog`):**
     RouterOS x86 có cấu hình mặc định của hãng là `watchdog-timer: yes` và `ping-timeout: 1m` (**ĐÂY LÀ TÍNH NĂNG GỐC CỦA ROUTEROS TRONG KERNEL, KHÔNG PHẢI DO NGƯỜI DÙNG TỰ THIẾT KẾ**). Khác hoàn toàn với script phần mềm `/system script watchdog-pppoe` (script 3m chỉ disable/enable line PPPoE dính CGNAT chứ không reboot máy). Khi router bị tấn công mạng dồn dập (SYN Flood trên port 8729 hoặc SSH/Winbox flood), kernel hoặc network subsystem bị nghẽn (hang/stall), chip watchdog không nhận được tín hiệu heartbeat nên **tự động ngắt rơ-le / hard-reboot lại toàn bộ PC x86** (kêu tiếng "tíc").
     * **Lưu ý quan trọng về watchdog-timer:** Chỉ tắt tạm (`watchdog-timer=no`) trong lúc xử lý ngắt vòng lặp reset do flood. Sau khi đã khóa bảo mật và router ổn định, **BẮT BUỘC BẬT LẠI** (`/system watchdog set watchdog-timer=yes`) để làm phao cứu sinh cuối nếu kernel bị đơ cứng thật sự, tránh trường hợp router chết đứng mà không ai can thiệp được từ xa.
  2. **Nghẽn Socket & Resource Starvation dù CPU không tăng cao (Giải thích nghịch lý CPU 2%):**
     * Chip Intel J4125 4 core trên Mini PC x86 có năng lực chuyển tiếp gói tin rất lớn, do đó khi bị quét scan/flood brute-force, CPU tổng vẫn hiển thị **2 - 3%** chứ không tăng vọt.
     * Nghẽn không nằm ở tính toán CPU, mà nằm ở **tầng Socket & Mutex Lock**: RouterOS giới hạn `max-sessions=20` trên các dịch vụ SSH/Winbox/API. Khi botnet chiếm hết 20 socket đang chờ timeout (30-60s), toàn bộ request quản trị và heartbeat nội bộ bị drop/timeout khiến watchdog tưởng router đã chết và ngắt nguồn.
     * Log router ghi nhận rõ: `system,warning possible SYN flooding on tcp port 8729` và liên tục `denied winbox/dude connect`, `login failure for user root`.
     * **Xử lý:** Tắt vĩnh viễn các service thừa: `api`, `api-ssl`, `telnet`, `ftp`, `www-ssl`. Tắt `bandwidth-server` (`set enabled=no`), tắt `mac-server` và `mac-winbox` (`set allowed-interface-list=none`). Giới hạn IP chặt chẽ cho `ssh`, `winbox`, `www`.
     * Rule firewall port `8090` (Web Manager - Phone Access) bắt buộc gán `src-address-list=FPT_LAN` (phát hiện và audit bởi Claude Code CLI).
  3. **Quá tải I/O từ Docker Container:**
     Container `sing-box` chạy trong RouterOS ghi log từng kết nối của 80 điện thoại farm vào memory làm nghẽn RAM và tràn I/O, cộng hưởng với đợt flood từ WAN.
  4. **Nguồn điện Adapter / Nhiệt độ:**
     Cần lưu ý nguồn cấp 12V cho Mini PC x86 nếu cắm chung ổ điện với các hub sạc của dàn 80 máy S7 có thể bị sụt áp đột ngột khi dàn sạc farm tải nặng.

- **Kiểm tra Uptime O(1):**
  `/system resource print` $\rightarrow$ Đọc `uptime`, `cpu-load`, `free-memory`.
  Lấy giờ hiện tại trừ `uptime` ra chính xác thời điểm reboot (ví dụ: `23:49:09`).

- **Dấu vết Đổi IP Cổng 1 (pppoe-out1):**
  Mỗi lần PC reboot:
  * Tất cả 35 line PPPoE bị ngắt và quay số lại từ đầu.
  * Line 1 (`pppoe-out1` — cổng trỏ DDNS Cloudflare `mirotik1.taadaa.click`) nhận IP WAN mới từ Viettel (ví dụ: `116.99.172.246` $\rightarrow$ đổi sang `171.243.151.125`).
  * File state `mobiproxy_scan_guard_ips.json` (do cronjob `update_mikrotik_scan_guard.py` ghi) lưu vết IP cũ, giúp đối chiếu chứng minh router đã đổi IP bao nhiêu lần.

- **Bẫy Trôi Log Khởi động trong Memory:**
  RouterOS mặc định lưu log vào `memory` với giới hạn 1.000 dòng (`memory-lines=1000`).
  Container `sing-box` đẩy ra hàng chục dòng log mỗi giây $\rightarrow$ **Chỉ sau 2-3 phút, log khởi động hệ thống bị đè sạch**.
  **Giải pháp giữ log bền vững:** Cấu hình log ra đĩa SSD:
  ```routeros
  /system logging add action=disk topics=system
  /system logging add action=disk topics=critical
  /system logging add action=disk topics=warning
  /system logging add action=disk topics=error
  ```
  File log sẽ được ghi tại `log.0.txt` và `log.1.txt` trong `/file`.
  Đồng thời tắt log spam của container:
  ```routeros
  /system logging set [find topics~"container"] disabled=yes
  ```

---

### Lớp 2: PPPoE Line Flapping (Nguyên nhân chính gây cảm giác "tự reset hoài")
- **Thực tế:** Router KHÔNG hề reboot, nhưng các cổng proxy và mạng internet bị rớt/chập chờn liên tục.
- **Thủ phạm:** Script watchdog nội bộ `/system script watchdog-pppoe` chạy định kỳ mỗi 3 phút (`interval=3m` qua scheduler).
- **Cơ chế:**
  Loop qua 35 line PPPoE (`pppoe-out1..35`). Nếu line nào:
  1. Chưa chạy (`running = false`), hoặc
  2. Chưa nhận IP (`addrList = 0`), hoặc
  3. Bị nhà mạng Viettel cấp dải IP Private/CGNAT (`100.64.x`, `10.x`, `172.16..31.x`),
  $\rightarrow$ Watchdog lập tức phát lệnh:
  ```routeros
  /interface pppoe-client disable $ppp
  :delay 3s
  /interface pppoe-client enable $ppp
  ```
  Khi nhà mạng xoay phiên hoặc cấp IP CGNAT cho nhiều line, watchdog sẽ giật reset hàng loạt line (mỗi line delay 3s). Người dùng ở ngoài thấy proxy hoặc line PPPoE nhảy liên tục và tưởng router bị reset.
- **Kiểm tra lịch sử thay đổi cấu hình:**
  Lệnh `/system history print` sẽ ghi nhận chuỗi hành động `device changed` lặp lại cách nhau đúng 3 giây do script tự disable/enable PPPoE.

---

## 2. Lỗ hổng Mở Cổng Quản trị WAN & Bão Brute-force Gây Nghẽn Socket (SSH / Winbox)

### Triệu chứng
- Kết nối SSH vào IP WAN (`171.243.x.x`) hoặc domain `mirotik1.taadaa.click` bị `TimeoutError` hoặc `packet size too big: 0xd0000090`.
- Ping WAN vẫn thông (22ms), Winbox chập chờn lúc vào được lúc văng.
- Người dùng tưởng router bị treo cứng hoặc reset.

### Nguyên nhân gốc rễ
- Cổng SSH (`22`), Winbox (`8291`), Webfig (`9090`) mở ra toàn bộ Internet (`0.0.0.0/0` hoặc `address=""`).
- Hàng loạt botnet quốc tế quét IP Viettel và spam brute-force tài khoản `root`, `admin` với tần suất nhiều request mỗi giây (`system,error,critical login failure for user root from 89.117.104.46 via ssh`).
- Giới hạn phiên của RouterOS IP service là `max-sessions=20`. Khi botnet chiếm hết 20 socket đang chờ auth timeout (30-60s), mọi kết nối hợp lệ từ máy Kibe đều bị DROP/Timeout.

### Giải pháp Khóa Cổng Triệt Để O(1) qua IP Service Whitelist (Tránh Bẫy Firewall Filter)
- **BẪY CHẾT NGƯỜI KHI DÙNG FIREWALL FILTER TRÊN CHAIN INPUT:**
  Nếu tạo rule firewall filter `chain=input action=drop protocol=tcp dst-port=22,8291,9090` mà rule ACCEPT whitelist bị lỗi cú pháp hoặc đặt sai thứ tự (`place-before`), **RouterOS sẽ chặn toàn bộ truy cập SSH/Winbox kể cả từ LAN/Localhost!**
  Khi lỡ dính bẫy này, chỉ có cổng REST API (9090 nếu đã được whitelist `FPT_LAN`) mới có thể cứu được bằng cách gửi request DELETE xóa rule drop (`DELETE http://192.168.110.2:9090/rest/ip/firewall/filter/*<ID>`).
- **GIẢI PHÁP CHUẨN & AN TOÀN NHẤT:** Không cần tạo rule filter, chỉ cần giới hạn trường `address` trực tiếp trong `/ip service`:

```routeros
/ip service set ssh address=192.168.110.0/24,192.168.10.0/24,100.64.0.0/10,42.112.229.255/32,42.118.214.93/32
/ip service set winbox address=192.168.110.0/24,192.168.10.0/24,100.64.0.0/10,42.112.229.255/32,42.118.214.93/32
/ip service set www address=192.168.110.0/24,192.168.10.0/24,100.64.0.0/10,42.112.229.255/32,42.118.214.93/32
/ip service disable api-ssl
/ip service disable api
```

### 🚨 QUY TẮC BACKUP LÊN REPO CÁ NHÂN (User Rule 2026-09-13):
- Khi export file backup cấu hình RouterOS (`.rsc`) để đẩy lên Git repository (`thanhdatbui/AI-Tools`):
  + **TUYỆT ĐỐI KHÔNG ĐƯỢC TỰ Ý LỌC (SANITIZE) HAY THAY THẾ BẰNG `***` CÁC MẬT KHẨU, TOKEN, HOẶC CREDENTIALS.**
  + **Lý do kỹ thuật & Vận hành:** Repository này là repo riêng tư/cá nhân của user. Nếu script tự ý sanitize mật khẩu và token Cloudflare/DuckDNS, các máy trạm khác của hệ thống (như máy Admin) hoặc các script restore tự động khi kéo file về sẽ không thể phục hồi trọn vẹn cấu hình hoạt động của router.
  + **Hành động bắt buộc:** Luôn commit và push **100% nguyên trạng bản export gốc (full raw config)** lên Git.
- **192.168.110.0/24:** Mạng LAN máy tính Kibe.
- **192.168.10.0/24:** Mạng phone farm S7.
- **100.64.0.0/10:** Mạng VPN Tailscale truy cập từ xa.
- **42.112.229.255/32 & 42.118.214.93/32:** IP Public của Kibe khi truy cập qua WAN.
- **Tắt hẳn API/API-SSL:** Ngăn chặn triệt để nguy cơ SYN flooding trên port 8728/8729.

Ngay sau khi áp dụng, RouterOS sẽ tự động drop mọi gói tin SSH/Winbox từ IP lạ ở tầng socket, `uptime` duy trì vững vàng, CPU load trở về 1-2%, chấm dứt hoàn toàn hiện tượng nghẽn SSH.

---

## 3. Quy trình Truy vết Thống kê Số lần Rớt Mạng / Reset trong Ngày

1. **Uptime & Khởi động gần nhất:**
   `python -c "import paramiko; ...; run('/system resource print')"`
   $\rightarrow$ Lấy `uptime`. Lấy thời gian hiện tại trừ uptime ra chính xác thời điểm reboot (ví dụ: `23:49:09`).
2. **Thống kê lỗi Proxy MikroTik qua Cơ sở Dữ liệu OmniRoute:**
   OmniRoute lưu toàn bộ request qua MikroTik tại `~/.omniroute/storage.sqlite`.
   Chạy truy vấn SQL:
   ```sql
   SELECT timestamp, proxy_port, error
   FROM proxy_logs
   WHERE (proxy_host LIKE '%mirotik%' OR proxy_host LIKE '%192.168.110.2%')
     AND timestamp >= 'YYYY-MM-DD'
     AND (error LIKE '%fetch failed%' OR error LIKE '%timeout%' OR error LIKE '%hang up%')
   ```
   $\rightarrow$ Giúp báo cáo chính xác cho người dùng: Có bao nhiêu request thành công, tỷ lệ rớt mạng thực sự là bao nhiêu % (thường < 0.05%), và phân biệt rõ lỗi do mạng PPPoE hay do tài khoản upstream hết quota.
