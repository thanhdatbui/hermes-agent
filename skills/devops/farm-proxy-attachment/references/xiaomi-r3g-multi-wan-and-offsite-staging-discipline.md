# Xiaomi R3G Multi-WAN Architecture & Offsite Staging Discipline

## Incident & Context (2026-10-08)
Chuẩn bị router Xiaomi Mi Router 3G V1 (ImmortalWrt / OpenWrt MT7621A, 256MB RAM) làm Edge Egress Proxy gửi đi Thái Bình để quay 16 IP PPPoE (2 đường mạng x 8 IP/line) và cấp proxy từ xa cho farm S7 ở nhà.
Quá trình cấu hình thực tế, xử lý trực tiếp trên thiết bị và audit độc lập 2 vòng qua Claude CLI Senior Network Auditor đã đúc kết bộ quy tắc hoàn chỉnh:
1. **Kiến trúc phân bổ cổng thực dụng (User Directive):** 2 Cổng Trắng PPPoE + 1 Cổng Xanh Cứu Hộ / Tailscale.
2. **Quy trình 2 bước đổi cổng sống (Zero-Lockout Migration):** Không bao giờ bị mất kết nối SSH khi cấu hình cáp mạng nối tiếp máy tính.
3. **Kỷ luật Staging Offsite Router & Tailscale trên OpenWrt 32MB Flash:** Cài bản IPK tối ưu, ghim firewall, tắt key expiry 180 ngày.
4. **Bẫy mwan3, Watchcat, Alist, và NTP:** Các lỗi cấu hình ngầm làm tê liệt failover và treo router từ xa.

---

## 1. Kiến trúc Cổng Vật Lý Thực Dụng (User Mandate)

### 1.1. Bối cảnh & Yêu cầu
- Router Xiaomi R3G chỉ có **3 cổng RJ45 Gigabit**: 1 cổng WAN xanh dương (cạnh nguồn tròn) và 2 cổng LAN trắng (`lan1` ở giữa, `lan2` ở ngoài cùng cạnh USB).
- Yêu cầu vận hành:
  - Cần cắm 2 đường mạng mới kéo để quay số PPPoE 2 line riêng biệt (mỗi line 8 session = 16 IP).
  - Router đặt ở xa (Thái Bình), không có máy tính phụ cắm LAN để cấu hình.
  - S7 ở nhà (Đà Nẵng) sẽ trỏ proxy về domain/IP Thái Bình, nên **không cần cổng LAN phát mạng nội bộ tại chỗ**.

### 1.2. Sơ đồ 3 cổng vật lý chuẩn 100%
Thay vì chia 1 WAN + 1 WAN2 + 1 LAN phát DHCP phức tạp, quy hoạch trực quan nhất:

| Vị trí & Màu sắc | Interface OpenWrt | Cấu hình & Vai trò | Vận hành tại hiện trường |
|---|---|---|---|
| **CỔNG XANH DƯƠNG** *(cạnh nguồn)* | `rescue` (trong `br-lan`) | **CỔNG CỨU HỘ & TAILSCALE:** DHCP Client (metric 200), IP tĩnh `192.168.5.1`, **DHCP Server tắt (`ignore=1`)** | **Bình thường: ĐỂ TRỐNG.** Chỉ cắm dây mạng nhà vào đây khi 2 đường PPPoE gặp sự cố để cứu hộ từ xa qua Tailscale. |
| **CỔNG TRẮNG Ở GIỮA** | `wan` (`lan1`) | **PPPoE Line 1:** Interface `wan`, proto `pppoe`, metric 10 | Cắm dây mạng từ Modem Bridge 1 |
| **CỔNG TRẮNG NGOÀI CÙNG** | `wan2` (`lan2`) | **PPPoE Line 2:** Interface `wan2`, proto `pppoe`, metric 20 | Cắm dây mạng từ Modem Bridge 2 |

*Ưu điểm thực tế:* Người ở xa không biết kỹ thuật chỉ cần cắm 2 modem mới vào 2 cổng trắng giống hệt nhau. Cổng xanh (trên vỏ in WAN) chỉ dùng khi cần mượn mạng nhà để cứu hộ.

---

## 2. Quy Trình 2 Bước Đổi Cổng Sống (Zero-Lockout Migration)

Khi đang cắm trực tiếp cáp mạng từ máy tính (Admin PC) vào cổng `lan1` của router để SSH cấu hình, nếu gõ lệnh đổi `lan1` sang PPPoE thì kết nối SSH bị ngắt ngay lập tức (`connection reset` / lockout).

### Quy trình di chuyển cáp an toàn (Zero Lockout):
1. **Bước 1 (Gộp cổng xanh vào bridge mạng hiện tại):**
   ```bash
   uci -q delete network.wan
   uci -q delete network.wan6
   uci add_list network.@device[0].ports='wan'
   uci commit network
   /etc/init.d/network reload
   ```
   *Kết quả:* Cả cổng xanh (WAN) và cổng trắng giữa (LAN1) cùng chia sẻ bridge `br-lan` (`192.168.5.1`).
2. **Bảo User chuyển dây cáp:** Rút cáp mạng từ cổng trắng ở giữa cắm sang **CỔNG XANH**.
3. **Bước 2 (Giải phóng 2 cổng trắng sang PPPoE):**
   Khi máy tính đã nối với cổng xanh an toàn, thực thi cấu hình chính thức:
   ```bash
   # Gỡ lan1 và lan2 khỏi br-lan, chỉ giữ lại cổng wan xanh
   uci -q delete network.@device[0].ports
   uci add_list network.@device[0].ports='wan'

   # Cổng trắng giữa: PPPoE Line 1
   uci set network.wan=interface
   uci set network.wan.device='lan1'
   uci set network.wan.proto='pppoe'
   uci set network.wan.username='<user_line1>'
   uci set network.wan.password='<pass_line1>'
   uci set network.wan.metric='10'

   # Cổng trắng ngoài: PPPoE Line 2
   uci set network.wan2=interface
   uci set network.wan2.device='lan2'
   uci set network.wan2.proto='pppoe'
   uci set network.wan2.username='<user_line2>'
   uci set network.wan2.password='<pass_line2>'
   uci set network.wan2.metric='20'

   # Cổng xanh: Cổng cứu hộ DHCP client + giữ IP tĩnh quản trị
   uci set network.rescue=interface
   uci set network.rescue.device='br-lan'
   uci set network.rescue.proto='dhcp'
   uci set network.rescue.metric='200'
   uci set dhcp.lan.ignore='1'   # Tắt DHCP server chống xung đột mạng nhà

   # Firewall: Gán wan, wan2, rescue vào zone wan (masq=1, input=REJECT)
   uci add_list firewall.@zone[1].network='wan'
   uci add_list firewall.@zone[1].network='wan2'
   uci add_list firewall.@zone[1].network='rescue'

   uci commit network
   uci commit dhcp
   uci commit firewall
   /etc/init.d/firewall reload
   /etc/init.d/network reload
   ```

---

## 3. Cài Đặt Tailscale Trên OpenWrt 32MB Flash & Hardening

### 3.1. Tránh bẫy tràn Flash (/overlay)
- Bản binary chính thức từ Tailscale Go (`tailscale_x.x.x_mipsle.tgz`) nặng tới **34.5MB nén, >70MB giải nén**, cài vào sẽ tràn sạch flash 35MB `/overlay` và treo cứng router.
- **Giải pháp:** Cài bản OpenWrt IPK tối ưu (`mipsel_24kc`):
  - `tailscaled_1.24.2-1_mipsel_24kc.ipk` (~5.6MB)
  - `tailscale_1.24.2-1_mipsel_24kc.ipk` (~3.3MB)
  - Tổng dung lượng sau cài chỉ **~9.1MB**, để lại **~21.6MB flash trống an toàn (41% used)**.
  - Tải trực tiếp bằng `curl` trên R3G:
    ```bash
    curl -Lo /tmp/tailscaled.ipk https://downloads.openwrt.org/releases/21.02.7/packages/mipsel_24kc/packages/tailscaled_1.24.2-1_mipsel_24kc.ipk
    curl -Lo /tmp/tailscale.ipk https://downloads.openwrt.org/releases/21.02.7/packages/mipsel_24kc/packages/tailscale_1.24.2-1_mipsel_24kc.ipk
    opkg install /tmp/tailscaled.ipk /tmp/tailscale.ipk
    rm -f /tmp/tailscale*.ipk
    /etc/init.d/tailscale enable
    /etc/init.d/tailscale start
    ```

### 3.2. Đăng ký Headless & Cố định Firewall
- Chạy ngầm tránh treo SSH:
  `tailscale up --hostname=r3g-thaibinh --reset > /tmp/ts.log 2>&1 &`
- Đọc link auth qua `tailscale status` hoặc `logread | grep "AuthURL is"`. Gửi link cho User duyệt trên trình duyệt.
- Ghim rule iptables vào `/etc/firewall.user` để tồn tại qua các lần reboot:
  ```bash
  grep -q 'tailscale0' /etc/firewall.user || echo 'iptables -I INPUT -i tailscale0 -j ACCEPT' >> /etc/firewall.user
  ```
- **CRITICAL TRAP (Key Expiry):** Mặc định Tailscale node key hết hạn sau 180 ngày (6 tháng). Đối với thiết bị headless ở xa, **BẮT BUỘC vào Tailscale Admin Console (`https://login.tailscale.com/admin/machines`) -> bấm `...` cạnh node -> chọn "Disable key expiry"** để chống mất kết nối vĩnh viễn.

---

## 4. Các Bẫy Kỹ Thuật Ngầm Cần Vô Hiệu Hóa Trước Khi Gửi Đi

Qua 2 vòng audit độc lập từ Claude CLI Senior Network Auditor, phát hiện 4 cạm bẫy nguy hiểm:

### 4.1. Bẫy mwan3 làm tê liệt Failover và Blackhole Traffic
- Trong các firmware OpenWrt tùy biến, `mwan3` thường được bật sẵn ở cấu hình mặc định chỉ chứa `wan`.
- Khi `wan` rớt hoặc chưa cắm, policy mặc định của mwan3 đánh dấu traffic ra ngoài là `unreachable` (hook vào iptables mangle).
- Hậu quả: Toàn bộ traffic ra ngoài bị blackhole, **Line 2 (`wan2`) và cổng cứu hộ (`rescue`) bị chặn đứng hoàn toàn**, `tailscaled` không thể kết nối ra internet dù các đường mạng khác vẫn có mạng!
- **Khắc phục:** Tắt và vô hiệu hóa hoàn toàn mwan3:
  ```bash
  /etc/init.d/mwan3 stop
  /etc/init.d/mwan3 disable
  ```
  Để Linux kernel xử lý failover tự nhiên theo `metric`: `wan` (metric 10) $\rightarrow$ `wan2` (metric 20) $\rightarrow$ `rescue` (metric 200).

### 4.2. Bẫy Watchcat tự Reboot liên tục
- `watchcat` cài sẵn với cấu hình `mode='ping_reboot'`, ping `8.8.8.8` chu kỳ 6h.
- Trong quá trình vận chuyển đóng hộp hoặc khi cúp mạng internet, watchcat đếm ngược và tự cưỡng chế reboot router liên tục.
- **Khắc phục:** Tắt watchcat trước khi ship:
  ```bash
  /etc/init.d/watchcat stop
  /etc/init.d/watchcat disable
  ```

### 4.3. Bẫy hở cổng WAN từ các dịch vụ rác (Alist, OpenVPN)
- Firmware cài sẵn file manager `alist` (port 5244) và `openvpn` (port 1194) kèm rule `ACCEPT` trên zone WAN. Khi quay PPPoE có IP Public, web admin file manager bị lộ hoàn toàn ra internet cho botnet quét.
- **Khắc phục:** Tắt alist và xóa rule:
  ```bash
  /etc/init.d/alist stop
  /etc/init.d/alist disable
  uci -q delete firewall.alist
  uci -q delete firewall.openvpn
  uci commit firewall
  /etc/init.d/firewall reload
  ```

### 4.4. Bẫy lệch giờ hệ thống (NTP Server Trung Quốc)
- Router Xiaomi R3G không có chip pin RTC lưu giờ. Khi tắt nguồn, đồng hồ hệ thống tụt về mốc xuất xưởng.
- Firmware gốc thường chỉ trỏ NTP về các server Trung Quốc (`ntp1.aliyun.com`, `time1.cloud.tencent.com`). Nếu mạng chặn hoặc trễ, đồng hồ không đồng bộ được $\rightarrow$ TLS handshake của Tailscale bị từ chối (`CertificateNotYetValid` / SSL failure).
- **Khắc phục:** Thêm NTP quốc tế và Việt Nam:
  ```bash
  uci add_list system.ntp.server='time.cloudflare.com'
  uci add_list system.ntp.server='time.google.com'
  uci add_list system.ntp.server='pool.ntp.org'
  uci add_list system.ntp.server='vn.pool.ntp.org'
  uci commit system
  /etc/init.d/sysntpd restart
  ```

---

## 5. Sao Lưu Cấu Hình Dự Phòng (Pre-Ship Backup)
Trước khi rút nguồn đóng gói:
```bash
# Tạo file backup sysupgrade
sysupgrade -b /tmp/pre-ship-backup.tar.gz

# Kéo về máy trạm lưu trữ
cat /tmp/pre-ship-backup.tar.gz  # stream hoặc SCP về PC điều khiển
```
Lưu file backup (`pre-ship-backup.tar.gz`) an toàn tại máy host của kỹ thuật viên (`C:/Users/Kibe/pre-ship-backup.tar.gz`) để có thể khôi phục toàn bộ cấu hình 1 chạm nếu cần.
