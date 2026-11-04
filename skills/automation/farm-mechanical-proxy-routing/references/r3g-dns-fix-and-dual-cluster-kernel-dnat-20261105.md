# R3G Multi-PPPoE DNS Fix & Dual-Farm Kernel DNAT Offload (MobiProxy + R3G)

## 1. Hiện tượng & Vấn đề gốc rễ
- **MobiProxy 60 ports:**
  - Nút "Áp dụng cho tất cả proxy" trong tab `#security` là stub/dummy trên bản Web v3.0.67 (không thực sự nạp lại cấu hình 3proxy trong RAM).
  - Để set `none` (không password) từng port: Bắt buộc mở thẻ `<details>` của hàng đó, click `button[data-action="proxy-access"]` để bung HTML5 Dialog, set `select[name="mode"].value = 'none'` và kích hoạt trực tiếp `document.querySelector('#access-save').click()`.
  - Khi port đã thành `none`, MikroTik có thể dùng Kernel DNAT (`action=dst-nat`) chuyển tiếp thẳng cổng `200xx -> 51xx` theo tốc độ wire-speed.
- **R3G OpenWrt 16 PPPoE:**
  - Bản thân R3G Tinyproxy `5141-5158` KHÔNG CÓ password (chỉ dùng `Allow <MikroTik_IP>`).
  - Tuy nhiên, khi MikroTik Kernel DNAT sang R3G bị timeout: Nguyên nhân gốc rễ là file `/etc/resolv.conf` bị Tailscale chèn `nameserver 100.100.100.100` (DNS ma không phản hồi do Tailscale daemon bị treo). Tinyproxy khi nhận request CONNECT không phân giải được DNS (`Could not retrieve info / no entity`).
  - Khắc phục: Ghi đè `/etc/resolv.conf` thành `nameserver 8.8.8.8` và `nameserver 1.1.1.1`. Lập tức 16 port Tinyproxy thông suốt 100%.

## 2. Kết quả nghiệm thu thực tế (Ground Truth)
- Đã chuyển thành công cả **MobiProxy (38 ports)** và **R3G (32 mappings Admin)** sang **MikroTik Kernel DNAT**.
- **CPU MikroTik:** Rơi thẳng từ `97.6%` về mức tĩnh `1.6%` (thậm chí `0.4%`).
- **Throughput & PPS trên card ảo `veth-singbox`:** Rơi từ `127.114 pps` xuống còn dưới `300 pps`.
- **Độ trễ phản hồi proxy:** Rút ngắn từ `~1.5s` xuống `0.45s – 0.5s`.
- **Cơ chế Fail-Closed:** Khi SIM/line chết, S7 hiện chấm than mất mạng ngay, tuyệt đối không leak IP gốc Đà Nẵng nhờ Killswitch Firewall `*D`, `*8`, `*9`.
