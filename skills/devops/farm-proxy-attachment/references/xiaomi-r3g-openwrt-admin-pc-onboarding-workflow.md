# Quy trình Onboarding & Cấu hình Xiaomi R3G V1 (OpenWrt) qua Admin PC

## 1. Bối cảnh & Mô hình Hạ tầng (Kibe ↔ Admin PC ↔ R3G)
- **Hermes Coordinator:** Đang chạy tại máy **Kibe PC** (`192.168.110.123`).
- **Hiện trường Thiết bị Vật lý:** Thiết bị mạng (Xiaomi R3G V1) được cắm vật lý trực tiếp vào **Admin PC** (`192.168.110.119`, alias `admin-farm`).
- **Cổng kết nối:** Cổng card mạng phụ của Admin PC là **`Ethernet 2`** (`Realtek PCIe GbE Family Controller #2`, ifIndex 8).
- **Cơ chế Điều khiển:** Kibe SSH sang Admin PC qua SSH key `~/.ssh/id_ed25519_kibe_admin` (`ssh admin-farm ...`), sau đó từ Admin PC SSH tiếp vào router R3G.

## 2. Bẫy Stale IP trên Ethernet 2 & Quy trình Bắt tay DHCP
- **Hiện tượng bẫy:** Ban đầu `Ethernet 2` trên Admin PC bị cấu hình IP tĩnh cũ (ví dụ `192.168.88.2` không gateway/DNS của dải MikroTik cũ). Dù router đã cấp link và IPv6 neighbor (`40-31-3C-03-84-54`, MAC Xiaomi) đã `Reachable`, nhưng probe IPv4 `192.168.5.1` và `192.168.88.1` đều timeout hoàn toàn.
- **Khắc phục O(1):**
  1. Chuyển `Ethernet 2` của Admin PC sang nhận DHCP từ Xiaomi:
     `netsh interface ipv4 set address "Ethernet 2" dhcp`
     `ipconfig /renew "Ethernet 2"`
  2. Router Xiaomi lập tức cấp IP cho Admin PC: `192.168.5.127`, Subnet mask `255.255.255.0`, Default Gateway `192.168.5.1`.
  3. Kiểm tra thông cổng 22/80:
     `ping 192.168.5.1` (phản hồi <1ms).
     `powershell "Test-NetConnection -ComputerName 192.168.5.1 -Port 22"` (TcpTestSucceeded: True).

## 3. SSH vào Xiaomi R3G từ Admin PC
- **Thông số đăng nhập gốc OpenWrt:**
  - IP: `192.168.5.1`
  - User: `root`
  - Password: `password`
- **Môi trường thực thi lệnh trên Admin PC:**
  - Sử dụng Python virtualenv có sẵn thư viện `paramiko`:
    `C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
  - Đẩy script cấu hình qua `scp` vào `C:/Users/Admin/` và kích hoạt lệnh từ xa.

## 4. Đặc tả Phần cứng & Tối ưu Hệ thống (MT7621A ImmortalWrt)
- **Hệ điều hành:** ImmortalWrt 21.02-SNAPSHOT (Linux Kernel 5.4.182, kiến trúc `mipsel_24kc`).
- **CPU & RAM:** MediaTek MT7621 (2 nhân 4 luồng 880MHz), RAM 256MB DDR3.
- **Tối ưu bắt buộc (Kỷ luật Sol):**
  1. **Tắt sạch 2 băng tần WiFi:**
     `uci set wireless.radio0.disabled='1'`
     `uci set wireless.radio1.disabled='1'`
     `uci commit wireless && wifi reload`
     *(Giúp hạ nhiệt router, giảm CPU interrupt và giải phóng bộ nhớ)*.
  2. **Dùng WireGuard kernel module:** Có sẵn `kmod-wireguard` và `wireguard-tools` (<15MB RAM). Tránh chạy Xray/Singbox Go runtime nặng nề dễ gây OOM sập box.
  3. **Khóa cổng WAN:** Đóng toàn bộ inbound cổng WAN từ ngoài Internet, chỉ giữ tunnel nội bộ đâm về Farm.

## 5. Quy trình Vận hành Chuẩn: Triển khai Điểm Egress từ xa (Thái Bình)
1. **Bắt mạng trước tại địa điểm đích:**
   - Yêu cầu người ở nhà/ông anh đăng ký đường mạng mới (Viettel/VNPT).
   - Khi thợ tới kéo cáp, yêu cầu thợ:
     - Gạt modem chính sang chế độ **Bridge Mode**.
     - Xin đầy đủ **Username** và **Password PPPoE**.
2. **Cấu hình & Test thông tại Farm trước khi gửi:**
   - Nhập User/Pass PPPoE vào cổng WAN của R3G.
   - Thiết lập WireGuard client đâm thẳng về MikroTik / Mini PC ở Farm (`192.168.110.2`).
   - Test kết nối tunnel sống và kiểm tra leak IP.
3. **Chuyển phát thiết bị Plug-and-Play:**
   - Đóng gói gửi router ra Thái Bình.
   - Người nhận chỉ cần cắm 2 dây: (1) Nguồn điện, (2) Dây LAN từ modem vào cổng **WAN (màu xanh)** của R3G.
   - Thiết bị tự động quay số PPPoE và thiết lập proxy, không cần bất kỳ thao tác IT phức tạp nào tại chỗ.
