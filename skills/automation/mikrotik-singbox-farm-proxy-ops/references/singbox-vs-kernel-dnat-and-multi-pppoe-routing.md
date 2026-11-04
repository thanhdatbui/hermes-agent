# Vận hành Singbox vs Kernel DNAT & Xử lý Asymmetric Routing trên Farm Multi-PPPoE

## 1. Bản chất cốt lõi: L3/L4 Firewall/DNAT vs L7 Application Proxy (Singbox)
- **MikroTik RouterOS Kernel DNAT (Layer 3/4):**
  - Chỉ nhìn thấy IP nguồn/đích và Port nguồn/đích (chuyển tiếp ở tầng packet wire-speed, CPU < 2-5%).
  - **MÙ HOÀN TOÀN** đối với payload ứng dụng: Không thể tự động chèn User/Password authentication (`mobi1:TaadaaMobi#2026!`).
  - Khi upstream proxy (MobiProxy) bắt buộc User/Pass, nếu dùng Kernel DNAT thuần túy từ điện thoại gửi sang, client sẽ lập tức nhận lỗi `HTTP Error 407: Proxy Authentication Required`.
- **Singbox Container (Layer 7 Proxy):**
  - Hoạt động ở tầng User-space: Đóng vai trò là Protocol Gateway, tự động nạp User/Pass và thiết lập đường hầm `HTTP CONNECT` sang upstream.
  - **Điểm nghẽn phần cứng:** Chạy Singbox trong Docker Container trên RouterOS x86 làm toàn bộ gói tin phải đi qua card mạng ảo `veth-singbox` (phải chịu 2 lần netfilter conntrack + context-switching liên tục giữa kernel và userspace). Với 80-160 điện thoại cày TikTok sinh ra 60.000 - 120.000 pps, CPU 4 core của Mini PC x86 sẽ bị vắt kiệt ở mức 90-98%.

## 2. Bài toán Asymmetric Routing trên Router OpenWrt Multi-PPPoE (Xiaomi R3G)
- **Hiện trường vật lý:**
  - Xiaomi R3G cắm 2 line mạng vật lý (LAN1, LAN2), quay đa phiên thành 16 session PPPoE con (`pppoe-WAN2`, `wan_sub2..8` trên Line 1; `pppoe-wan`, `wan_sub11..17` trên Line 0).
  - Tên miền DDNS (`tb.taadaa.click`) chỉ trỏ về IP Public của 1 trong 16 line PPPoE (ví dụ `pppoe-WAN2`).
  - Mỗi instance Tinyproxy được bind vào IP nội bộ của interface PPPoE tương ứng (`Bind 100.123.x.x`).
- **Nguyên nhân Timeout khi DNAT từ xa vào R3G:**
  - Gói tin DNAT từ MikroTik Đà Nẵng gửi vào IP của card `pppoe-WAN2`.
  - Tinyproxy nhận và xử lý, nhưng khi gửi câu trả lời ra ngoài, hệ thống Policy Routing (16 table độc lập) lại đẩy gói tin ra một card PPPoE con khác (ví dụ `wan_sub3`) thay vì trả ngược lại đúng đường mà nó vừa đi vào.
  - Kết quả: Client hoặc router gửi ở đầu Đà Nẵng bị `Connection timed out` (lệch đường phản hồi).
- **Giải pháp kỹ thuật:**
  1. Trên MikroTik: Bắt buộc kết hợp **DNAT + SNAT (Masquerade)** để ép IP nguồn thành IP của MikroTik.
  2. Trên OpenWrt R3G: Cần có cơ chế `CONNMARK` (đánh dấu gói tin theo interface đi vào) trong iptables mangle để ép gói tin phản hồi đi ra đúng interface PPPoE mà nó đã đi vào:
     ```bash
     iptables -t mangle -A PREROUTING -m state --state NEW -j CONNMARK --save-mark
     iptables -t mangle -A OUTPUT -m state --state ESTABLISHED,RELATED -j CONNMARK --restore-mark
     ```

## 3. Tối ưu Conntrack Timeout trên MikroTik để giải phóng Zombie Connections
- Khi 160 máy cày video TikTok, mặc định `tcp-established-timeout = 1d (24 giờ)` làm MikroTik tích tụ hơn 100.000 kết nối ma (zombie connections) ngay cả khi điện thoại đã về màn hình Home.
- **Bộ thông số chuẩn công nghiệp (Best Practice):**
  ```routeros
  /ip firewall connection tracking set tcp-established-timeout=1h generic-timeout=2m udp-stream-timeout=1m udp-timeout=10s
  ```
  - Giải phóng ngay lập tức hàng chục nghìn kết nối rác mà không gây rớt mạng hay gián đoạn các luồng live của ca sau.

## 4. Tách biệt kiến trúc chuẩn cho Farm TikTok lớn (Decoupled 3-Tier)
1. **Tier 1 (Edge Router - MikroTik x86):** Chỉ làm định tuyến L3/L4, DHCP, NAT cơ bản, và Kill-Switch tường lửa (chặn lọt IP gốc). CPU duy trì < 5-10%.
2. **Tier 2 (Proxy Gateway - Host Linux/PC riêng biệt):** Chạy Singbox/Gost trên một máy tính độc lập (ví dụ PC Core i5-8400) để gánh toàn bộ việc đóng gói User/Pass và forward L7. Tuyệt đối không nhét vào máy tính đang gánh nặng Playwright/ADB (như PC Kibe/Admin) để tránh port exhaustion và giật lag ADB.
3. **Tier 3 (Upstream Proxies):** Cụm MobiProxy 4G và R3G Multi-PPPoE tại Thái Bình.
