---
name: mikrotik-kernel-dnat-and-multiwan-proxy-ops
description: "Vận hành Kernel DNAT trên MikroTik, cấu hình MobiProxy No-Auth, xử lý Asymmetric Routing R3G Multi-PPPoE và cơ chế Dead Lock Reap cho pipeline."
---
# MikroTik Kernel DNAT & Multi-WAN Proxy Operations (MobiProxy & R3G)

- `references/fail-closed-vs-app-fallback-leak-and-screen-off-discipline-20261106.md`: Kỷ luật kiểm chứng màn hình sáng trước khi screencap, kiến trúc Trio Killswitch L3/L4 (Drop WAN direct, Drop QUIC UDP 443, Drop DNS UDP 53), bypass Mangle cho Kernel DNAT cả 2 cụm Kibe + Admin, quy trình dập tắt app TikTok khi pause cron và cơ chế sync dynamic DDNS cho RouterOS NAT rules.
- `references/mobiproxy-dnat-timeout-and-fail-closed-preflight-20261106.md`: Hiện trường lỗi MobiProxy WAN timeout gây liệt dải DNAT 20001-20038 và cơ chế Fail-Closed của ConsumerPreflightError.

## 1. Bản chất hạ tầng: MobiProxy vs Xiaomi R3G
- **MobiProxy:** Cắm 4 line mạng cáp quang vật lý (Lan1..Lan4), mỗi line quay đa phiên 8 PPPoE chia ra các port proxy 5101..5138.
  - Trên web quản trị v3.0.67, bảng danh sách `#proxies` có menu dấu 3 chấm `•••` -> `Cấu hình truy cập` -> modal HTML5 Dialog với nút `#access-save` để đổi chế độ xác thực từng port sang `none` (Không xác thực).
  - Tắt pass trên MobiProxy an toàn 100% nhờ lớp tường lửa Chống scan proxy (Scan Guard Whitelist IP) tại mục `#security`.
- **Xiaomi R3G:** Cắm 2 line mạng cáp quang vật lý, quay đa phiên 16 đường PPPoE con:
  - Line 1 (LAN2): Cổng 5141-5148 (`pppoe-WAN2`, `wan_sub2..sub8`).
  - Line 0 (LAN1): Cổng 5151-5158 (`pppoe-wan`, `wan_sub11..sub17`).
  - 16 port Tinyproxy trên R3G vốn dĩ **không hề cài mật khẩu** (`BasicAuth` = none), bảo vệ bằng whitelist `Allow <mikrotik_ip>`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
