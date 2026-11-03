# Phân Tích Lựa Chọn Node Host Cho Singbox & Giải Pháp Bỏ Hẳn Singbox Bằng Kernel DNAT

## 1. So Sánh Node Host Khi Tách Singbox Khỏi MikroTik (Kibe vs. Admin PC)
Khi tách container Singbox ra khỏi con Mini PC MikroTik x86 để giải phóng ngắt mạng veth (kéo CPU từ 96% xuống < 15%), việc chọn node máy chủ Windows trong mạng LAN là quyết định then chốt:

### A. Rủi Ro Nghiêm Trọng Khi Đặt Singbox Lên PC Kibe (`192.168.110.123`)
- **Tải hỗn hợp:** PC Kibe đang gánh đồng thời các tiến trình automation nặng nhất của farm:
  - Playwright / CDP Automation (nhiều nhân Chromium v8 ngốn RAM và CPU).
  - ADB Server (kết nối USB & TCP liên tục với 80 điện thoại).
  - Hermes Agent Messaging Gateway & OmniRoute LLM Proxy.
- **Nghẽn cổng mạng (Ephemeral Port Exhaustion):**
  - 80-160 điện thoại S7 streaming video TikTok đồng thời mở từ 3.000 đến 8.000 TCP sockets liên tục.
  - Khi dồn lượng socket khổng lồ này vào Windows Kernel của PC Kibe, tình trạng cạn kiệt ephemeral ports và nghẽn context-switch sẽ xảy ra.
  - **Hậu quả:** ADB server bị drop kết nối (`device offline`, `connection reset`), Playwright bị timeout, và toàn bộ pipeline điều phối trên Kibe bị đơ lag.

### B. Ưu Thế Khi Đặt Singbox Lên PC Admin (`192.168.110.119`)
- Tách rời hoàn toàn khỏi node điều khiển cốt lõi (PC Kibe).
- PC Admin chỉ chạy tác vụ cào/render và feed phụ, có headroom tài nguyên mạng dồi dào hơn.
- Không gây nghẽn bus I/O hoặc cạn kiệt socket cho cụm Playwright / ADB của Kibe.

---

## 2. Giải Pháp Triệt Tiêu 100% Singbox Bằng MikroTik Kernel DNAT (Tối Thượng)
User đặt câu hỏi cốt lõi: *"Ý là vẫn BẮT BUỘC xài Singbox à? Có giải pháp nào KHÔNG DÙNG SINGBOX NỮA MÀ VẪN GIẢI QUYẾT ĐƯỢC KHÔNG?"*

### A. Bản Chất Kỹ Thuật: Tại Sao Singbox Thực Chất Là Thừa Thãi?
- Trên điện thoại Samsung S7: Cài đặt Wi-Fi Proxy gửi ra gói tin chuẩn **HTTP Proxy (`HTTP CONNECT`)**.
- Trên đầu ra Thái Bình (MobiProxy & R3G): Các port 51xx (`Tinyproxy` / `3proxy`) nhận vào **CŨNG LÀ HTTP Proxy (`HTTP CONNECT`)**.
- **Cả hai đầu đều nói cùng một thứ tiếng.** Việc dựng Singbox ở giữa chỉ để nhận HTTP proxy rồi forward sang một HTTP proxy khác là kiến trúc thừa thãi do tư duy rập khuôn gây ra.

### B. Cơ Chế Chuyển Tiếp Tầng Mạng (Port Forwarding / Kernel DNAT)
MikroTik RouterOS có thể đóng vai trò chuyển tiếp thuần túy ở tầng L3/L4 ở tốc độ dây (wire-speed):
```routeros
# Chuyển tiếp cổng trực tiếp ở tầng kernel (FastPath):
/ip firewall nat add chain=dstnat protocol=tcp dst-port=20001 action=dst-nat to-addresses=[IP_THAI_BINH] to-ports=5101 comment="DNAT_M1_TO_MOBIPROXY_5101"
/ip firewall nat add chain=dstnat protocol=tcp dst-port=20203 action=dst-nat to-addresses=[IP_R3G_THAI_BINH] to-ports=5141 comment="DNAT_M203_TO_R3G_5141"
```
- **Ưu điểm tuyệt đối:**
  1. Triệt tiêu hoàn toàn Singbox (không cần container trên MikroTik, không cần cài đặt lên PC Kibe hay PC Admin).
  2. CPU Mini PC MikroTik rơi thẳng từ **96% xuống dưới 5%** vì chỉ đổi địa chỉ header TCP ở tầng phần cứng, không tốn tài nguyên bóc tách L7.
  3. Giữ nguyên 100% cấu hình trên 80-160 máy S7 (vẫn trỏ proxy `192.168.110.2:200xx`).
  4. Proxy Thái Bình chết thì kết nối TCP bị đứt, Android lập tức hiện dấu chấm than ngắt mạng $\rightarrow$ An toàn 100% không lộ IP.
- **Điều kiện tiên quyết:** Cụm proxy Thái Bình phải hỗ trợ xác thực bằng Whitelist IP (bỏ auth user/pass nếu có) để gói tin HTTP CONNECT từ S7 đi thẳng vào proxy mà không bị vướng auth intermediate.
