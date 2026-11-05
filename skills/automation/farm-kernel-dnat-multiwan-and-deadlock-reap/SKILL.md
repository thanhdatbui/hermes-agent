---
name: farm-kernel-dnat-multiwan-and-deadlock-reap
description: "Kỷ luật vận hành Kernel DNAT trên MikroTik, cơ chế Dead Lock Reap cho pipeline, và xử lý Asymmetric Routing trên Multi-WAN OpenWrt (R3G & MobiProxy)."
version: 1.0.0
category: automation
tags: [mikrotik, routeros, kernel-dnat, mobiproxy, openwrt, r3g, pipeline-lock, dead-lock-reap, farm-safety]
---
# Farm Kernel DNAT, Multi-WAN Routing & Pipeline Lock Governance

## 1. Bản Chất Hạ Tầng Vật Lý Proxy Farm
- **MobiProxy:** Cắm 4 line mạng cáp quang vật lý (Lan1..Lan4), mỗi line quay đa phiên 8 PPPoE chia ra các port proxy 5101..5138.
  - Trên web quản trị v3.0.67, bảng danh sách `#proxies` có menu dấu 3 chấm `•••` -> `Cấu hình truy cập` -> modal HTML5 Dialog với nút `#access-save` để đổi chế độ xác thực từng port sang `none` (Không xác thực).
  - Tắt pass trên MobiProxy an toàn 100% nhờ lớp tường lửa Chống scan proxy (Scan Guard Whitelist IP) tại mục `#security`.
- **Xiaomi R3G:** Cắm 2 line mạng cáp quang vật lý, quay đa phiên 16 đường PPPoE con:
  - Line 1 (LAN2): Cổng 5141-5148 (`pppoe-WAN2`, `wan_sub2..sub8`).
  - Line 0 (LAN1): Cổng 5151-5158 (`pppoe-wan`, `wan_sub11..sub17`).
  - 16 port Tinyproxy trên R3G vốn dĩ **không hề cài mật khẩu** (`BasicAuth` = none), bảo vệ bằng whitelist `Allow <mikrotik_ip>`.
- **CẤM NHỚ NHẦM BẢN CHẤT PHẦN CỨNG:** MobiProxy cắm 4 line cáp quang quay PPPoE, KHÔNG PHẢI cắm SIM 4G. R3G cắm 2 line cáp quang quay 16 PPPoE.

## 2. Kernel DNAT trên MikroTik & Cơ chế Chống Nghẽn CPU
- Thay vì để gói tin proxy của farm chui vào container Singbox (L7) gây nghẽn CPU 96-98%, sử dụng trực tiếp rule Kernel DNAT phần cứng (`dstnat` -> `to-addresses` IP WAN đại diện proxy, `to-ports` tương ứng).
- Đẩy toàn bộ rule Kernel DNAT lên đứng trước rule Singbox `*30E` để bắt trọn gói tin, giảm tải CPU MikroTik từ 97.6% về 0.4% - 1.6% (wire-speed 0.4s).
- **Tự động hóa đồng bộ DDNS khi ISP đổi IP:** Khi nhà mạng Viettel tự động nhả lease và đổi IP WAN của MobiProxy/R3G, cronjob (`update_mikrotik_scan_guard.py` chạy 1 phút/lần) tự phân giải DNS và cập nhật `to-addresses` cho toàn bộ các rule DNAT tương ứng, chống rớt mạng toàn farm.
- **Xóa Cronjob Tự Reset Proxy:** Tuyệt đối không để các watchdog cũ tự động gọi API reset cổng/reboot MobiProxy (như `cron_mobiproxy_healer.py`) làm rớt kết nối đột ngột của farm.

## 3. Asymmetric Routing & Whitelist trên Farm Multi-WAN (R3G OpenWrt)
- **Cạm bẫy:** Mangle của router chính (MikroTik) ép các IP máy con (ví dụ M203 ở `192.168.10.221`) đi ra các line WAN phụ (`pppoe-out8`), trong khi router proxy đích (R3G) lại chỉ mở Whitelist hoặc route phản hồi về WAN chính (`pppoe-out1`).
- **Khắc phục:** Khi mở Whitelist trên R3G, bắt buộc mở theo dải CIDR (`171.231.0.0/16` và `116.110.0.0/16`) thay vì 1 IP tĩnh đơn lẻ, tránh tình trạng thiết bị Android bị drop gói tin và dính dấu chấm than Wi-Fi (`ERR_CONNECTION_REFUSED`).
- **DNS Ma trên OpenWrt R3G:** Tailscale bị treo trên chip yếu có thể chèn `nameserver 100.100.100.100` vào `/etc/resolv.conf` làm Tinyproxy nghẽn phân giải tên miền. Bắt buộc đưa về `8.8.8.8` và `1.1.1.1`.

## 4. Pipeline Stale Lock Auto-Reap & Kỷ Luật Điều Phối
- **Cơ chế Dọn Lock Rác Pipeline (Dead Lock Reap):** Khi tiến trình cũ bị ngắt đột ngột hoặc reboot, file lock `pipeline_repo_*.lock` sót lại làm nghẽn pipeline với lỗi `PRECHECK ERROR`. Hàm `RepoLock.acquire()` bắt buộc kiểm tra `psutil.pid_exists(pid)`. Nếu PID đã chết, tự động unlink file lock trước khi báo lỗi.
- **Kỷ luật Pipeline:** Cấu hình router hay thiết bị mạng không được viện cớ "lock nhảm" để tự ý bỏ qua pipeline sửa code bắt buộc (`unified_patch_pipeline.py`).
