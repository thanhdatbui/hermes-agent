# Xiaomi R3G Multi-WAN Architecture & Offsite Staging Discipline

## Incident & Context (2026-10-08)
Chuẩn bị router Xiaomi Mi Router 3G V1 (ImmortalWrt / OpenWrt MT7621A, 256MB RAM) làm Edge Egress Proxy gửi đi Thái Bình để quay 16 IP PPPoE (2 đường mạng x 8 IP/line).
Quá trình cấu hình và thảo luận với User đã làm rõ 2 bài học sống còn:
1. **Kiến trúc Multi-WAN trên router ít cổng vật lý** (3 cổng Gigabit: 1 WAN + 2 LAN).
2. **Kỷ luật Staging Offsite Router** (chống brick / mất liên lạc từ xa khi gửi thiết bị headless đi tỉnh).

---

## 1. Kiến trúc Multi-WAN trên Xiaomi R3G (2 Line -> 16 IP)

### 1.1. Bối cảnh hạ tầng Thái Bình
- Mỗi đường mạng Viettel/VNPT tại dân cư Thái Bình bị BRAS giới hạn tối đa **8 session PPPoE** (8 IP Public đồng thời).
- Yêu cầu farm: Cần tối thiểu 16 IP proxy xoay vòng $\rightarrow$ Bắt buộc cắm **2 đường mạng vật lý riêng biệt**.

### 1.2. Phân bổ 3 cổng vật lý Gigabit trên R3G
Con Xiaomi R3G chỉ có 3 cổng mạng RJ45:
- 1 cổng WAN (Xanh dương, cạnh cổng nguồn DC).
- 2 cổng LAN (Trắng/xám: `lan1` ở giữa, `lan2` ở ngoài cùng cạnh USB).

**Sơ đồ phân bổ chuẩn:**
* **Cổng WAN (Xanh):** Cắm dây mạng từ **Line 1 (Modem 1)**.
* **Cổng LAN 2 (Trắng ngoài cùng):** Bẻ thành **WAN 2**, cắm dây mạng từ **Line 2 (Modem 2)**.
* **Cổng LAN 1 (Trắng ở giữa):** Giữ làm **cổng LAN nội bộ**, cắm 1 sợi dây mạng ra Switch Farm (chia mạng cho 80 máy Samsung S7).

### 1.3. Lệnh cấu hình bẻ cổng LAN 2 thành WAN 2 trên OpenWrt
```bash
# 1. Gỡ lan2 khỏi bridge mạng nội bộ br-lan
uci del_list network.@device[0].ports='lan2'

# 2. Tạo interface wan2 gán trực tiếp vào cổng vật lý lan2
uci set network.wan2=interface
uci set network.wan2.device='lan2'
uci set network.wan2.proto='dhcp'

# 3. Gán wan2 vào firewall zone wan (để NAT và masquerade đúng chuẩn)
uci add_list firewall.@zone[1].network='wan2'

# 4. Commit lưu bền vào /etc/config/ và reload
uci commit network
uci commit firewall
/etc/init.d/firewall reload
/etc/init.d/network reload
```

### 1.4. Mở rộng khi có 3+ đường mạng
Nếu sau này cần cắm 3 đường mạng trở lên (ví dụ 4 line x 8 session = 32 IP):
- **Giải pháp 1 (Chuẩn Farm - Smart Switch 802.1Q):** Mua Switch 5 port có VLAN (như TP-Link TL-SG105E ~250k). Cắm các modem vào các port trên Switch (gán VLAN 10, 20, 30...). Từ Switch cắm 1 sợi dây Trunk duy nhất vào cổng WAN xanh của R3G. Trên R3G tạo các interface `wan.10`, `wan.20`, `wan.30`...
- **Giải pháp 2 (USB to LAN Gigabit):** Mua củ USB 3.0 to LAN Gigabit (chip RTL8153 ~120k) cắm vào cổng USB 3.0 xanh của R3G, nhận thêm cổng vật lý `eth1` làm WAN 3.

---

## 2. Kỷ luật Staging Offsite Router (Anti-Remote Bricking)

### 2.1. Cạm bẫy "Set cứng PPPoE trước khi gửi"
- **Sai lầm thường gặp:** Nạp sẵn tài khoản PPPoE (hoặc tài khoản test ở nhà) vào cổng WAN rồi đóng gói gửi đi.
- **Hậu quả:** Khi đến nơi, người nhận cắm router vào modem gia đình thông thường (vốn đang phát mạng qua DHCP, chưa bật Bridge mode hoặc chưa active hợp đồng mạng mới). Cổng WAN không thể quay PPPoE $\rightarrow$ Router **hoàn toàn không có internet** $\rightarrow$ Mọi dịch vụ remote (WireGuard, Tailscale, SSH) đều không thể gọi về nhà $\rightarrow$ Router bị cô lập ("bricked" từ xa).
- **Cái giá phải trả:** Bắt buộc người ở xa phải lấy laptop cắm dây LAN vào router, bật UltraViewer/TeamViewer cho kỹ thuật viên ở nhà cứu hộ.

### 2.2. Sai lầm cắm dây vào cổng LAN để cấp mạng
- Người không chuyên thường nghĩ "cắm tạm dây mạng vào cổng LAN 1 để router có mạng mà remote".
- **Thực tế:** Cổng LAN đang chạy DHCP Server (cấp dải `192.168.5.x`). Cắm vào modem nhà sẽ đụng 2 DHCP Server trên cùng broadcast domain, gây loạn mạng toàn nhà và bản thân router OpenWrt cũng không định tuyến Default Gateway qua LAN được.

### 2.3. Quy trình Staging Offsite chuẩn 5 bước (Bắt buộc tuân thủ)

1. **Bước 1 — Đặt cổng WAN ở chế độ DHCP:**
   Trước khi đóng gói, cấu hình cổng WAN:
   ```bash
   uci set network.wan.proto='dhcp'
   uci commit network
   ```
2. **Bước 2 — Cài đặt Reverse Overlay Tunnel ngầm (Tailscale / ZeroTier / WireGuard):**
   - **Bẫy bộ nhớ Flash Tailscale trên OpenWrt MT7621 (32MB Flash):**
     * Bản binary chính thức từ Tailscale Go (`tailscale_x.x.x_mipsle.tgz`) nặng tới **34.5MB nén, >70MB giải nén** $\rightarrow$ Cài vào sẽ **tràn sạch 35MB bộ nhớ flash `/overlay` và treo cứng router**.
     * **Giải pháp chuẩn:** Dùng bản package tối ưu cho OpenWrt (`mipsel_24kc`) từ `downloads.openwrt.org`:
       - `tailscaled_1.24.2-1_mipsel_24kc.ipk` (5.6MB)
       - `tailscale_1.24.2-1_mipsel_24kc.ipk` (3.3MB)
       - Tổng dung lượng sau cài đặt chỉ **~9.1MB**, để lại **16.6MB flash trống an toàn (55% used)**.
     * **Cách nạp & cài đặt nhanh O(1) qua `curl` trực tiếp trên router:**
       ```bash
       curl -Lo /tmp/tailscaled.ipk https://downloads.openwrt.org/releases/21.02.7/packages/mipsel_24kc/packages/tailscaled_1.24.2-1_mipsel_24kc.ipk
       curl -Lo /tmp/tailscale.ipk https://downloads.openwrt.org/releases/21.02.7/packages/mipsel_24kc/packages/tailscale_1.24.2-1_mipsel_24kc.ipk
       opkg install /tmp/tailscaled.ipk /tmp/tailscale.ipk
       rm -f /tmp/tailscale*.ipk
       /etc/init.d/tailscale enable
       /etc/init.d/tailscale start
       ```
     * *Lưu ý truyền file:* Dropbear trên OpenWrt không có `sftp-server` và Windows Firewall trên máy Admin thường chặn port 8000; cách an toàn và nhanh nhất là để R3G tự dùng `curl` tải trực tiếp từ internet.
   - **Bẫy treo terminal khi chạy `tailscale up` trên thiết bị Headless:**
     * Lệnh `tailscale up --hostname=<name>` sẽ block tiến trình SSH để chờ người dùng duyệt web, khiến subagent/terminal bị timeout.
     * **Cách xử lý chuẩn:** Chạy ngầm và trích xuất Auth URL:
       `tailscale up --hostname=r3g-thaibinh --reset > /tmp/ts.log 2>&1 &`
       Đọc link duyệt web qua: `tailscale status` hoặc `logread | grep "AuthURL is"`. Link có dạng `https://login.tailscale.com/a/<id>`, người dùng bấm duyệt trên browser là router tự động kết nối vào mạng Tailscale cá nhân.
   - Tunnel này có đặc tính: Chỉ cần router có bất kỳ kết nối internet outbound nào (dù nằm sau bao nhiêu lớp NAT/firewall), nó sẽ tự động đâm đường hầm về máy chủ/PC điều khiển ở Farm.
3. **Bước 3 — Bàn giao & Cắm dây đơn giản tại chỗ:**
   - Dặn người nhận ở xa: Cắm nguồn $\rightarrow$ Cắm 1 sợi dây mạng từ cổng LAN modem nhà vào **cổng WAN xanh** của router.
   - Không cần cắm máy tính, không cần cấu hình gì cả.
4. **Bước 4 — Tiếp quản từ xa qua Tunnel:**
   - Ngồi tại Farm kiểm tra thấy router online trên Tunnel.
   - SSH vào IP đường hầm nội bộ, nạp sẵn 16 session PPPoE, cấu hình MACVLAN và mwan3.
5. **Bước 5 — Kích hoạt Bridge Mode & Chuyển sang PPPoE:**
   - Bảo thợ nhà mạng hoặc người nhận gạt Bridge mode trên modem nhà mạng.
   - Từ xa qua SSH/Tunnel, chuyển cấu hình WAN sang PPPoE và khởi động lại interface. Router nổ phiên PPPoE nhận IP Public mà không bị gián đoạn quyền điều khiển.
