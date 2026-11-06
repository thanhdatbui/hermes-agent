---
name: mikrotik-kernel-dnat-and-multiwan-proxy-ops
description: "Vận hành Kernel DNAT trên MikroTik, cấu hình MobiProxy No-Auth, xử lý Asymmetric Routing R3G Multi-PPPoE và cơ chế Dead Lock Reap cho pipeline."
---
# MikroTik Kernel DNAT & Multi-WAN Proxy Operations (MobiProxy & R3G)

> Core Reference: `references/mobiproxy-dnat-timeout-and-fail-closed-preflight-20261106.md` — Hiện trường lỗi MobiProxy WAN timeout gây liệt dải DNAT 20001-20038 và cơ chế Fail-Closed của ConsumerPreflightError.

## 1. Bản chất hạ tầng: MobiProxy vs Xiaomi R3G
- **MobiProxy:** Cắm 4 line mạng cáp quang vật lý (Lan1..Lan4), mỗi line quay đa phiên 8 PPPoE chia ra các port proxy 5101..5138.
  - Trên web quản trị v3.0.67, bảng danh sách `#proxies` có menu dấu 3 chấm `•••` -> `Cấu hình truy cập` -> modal HTML5 Dialog với nút `#access-save` để đổi chế độ xác thực từng port sang `none` (Không xác thực).
  - Tắt pass trên MobiProxy an toàn 100% nhờ lớp tường lửa Chống scan proxy (Scan Guard Whitelist IP) tại mục `#security`.
- **Xiaomi R3G:** Cắm 2 line mạng cáp quang vật lý, quay đa phiên 16 đường PPPoE con:
  - Line 1 (LAN2): Cổng 5141-5148 (`pppoe-WAN2`, `wan_sub2..sub8`).
  - Line 0 (LAN1): Cổng 5151-5158 (`pppoe-wan`, `wan_sub11..sub17`).
  - 16 port Tinyproxy trên R3G vốn dĩ **không hề cài mật khẩu** (`BasicAuth` = none), bảo vệ bằng whitelist `Allow <mikrotik_ip>`.

## 2. Kỷ luật vận hành Kernel DNAT trên MikroTik
- **Giải phóng CPU tuyệt đối:** Kernel DNAT xử lý gói tin wire-speed ở tầng L3/L4 của chip MikroTik mà không cần chuyển ngữ cảnh L7 sang user-space Singbox container, giúp CPU router rơi thẳng từ ~97% về ~1.6%.
- **Thứ tự Rule NAT:** Các rule Kernel DNAT per-device (`chain=dstnat dst-port=2000X to-addresses=<proxy_ip> to-ports=510X`) BẮT BUỘC phải đặt trước rule gom Singbox (`*30E`).
- **Đồng bộ DDNS 1 phút / lần:** Khi MobiProxy đổi IP WAN qua PPPoE quay số, script `scripts/update_mikrotik_scan_guard.py` tự động phân giải `test.taadaa.click` và cập nhật tức thời `to-addresses` cho 38 rule DNAT. Cronjob phải chạy mỗi 1 phút (`* * * * *`).
- **Fail-Closed & Chống lộ IP:** Khi proxy sập / mất kết nối, máy S7 bị ngắt kết nối (TCP drop/timeout) tự nhiên và hiện dấu chấm than trên Wi-Fi. Rule tường lửa `*D` (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`) cùng khóa UDP 443/53 đảm bảo 100% không bao giờ rò rỉ IP gốc Đà Nẵng ra ngoài.
- **CẤM Cron tự đổi proxy gây mất mạng:** Tuyệt đối không bật các cronjob tự động heal/reset cổng MobiProxy ngoài giờ kiểm soát (như `cron_mobiproxy_healer.py`) làm rớt phiên nuôi của farm.
- **Dọn sạch VPS hết hạn:** Xóa vĩnh viễn mọi WireGuard peer/route/firewall của VPS đã hết hạn (như VPS Doravo Sentinel) để đóng sập hoàn toàn cửa ngõ vào mạng LAN farm.
- **Chuyên đề sâu Fail-Closed vs App Fallback Leak & Screen Off Verification:** Tra cứu `references/fail-closed-vs-app-fallback-leak-and-screen-off-discipline-20261106.md` về kỷ luật kiểm tra màn hình điện thoại trước khi screencap (tránh ảnh đen kịt RGB=0), cạm bẫy App TikTok tự lách proxy qua QUIC UDP 443 khi HTTP Proxy chết làm lộ IP gốc Đà Nẵng, và rule Mangle Bypass `prerouting dst-port=20201-20280 action=accept` đặt đầu bảng.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
