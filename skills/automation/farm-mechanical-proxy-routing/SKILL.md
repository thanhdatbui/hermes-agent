---
name: farm-mechanical-proxy-routing
description: "Kiến trúc và quy chuẩn khóa cơ học (Mechanical Enforcement) định tuyến proxy và Direct IP trên toàn Farm, chống ảo tưởng memory."
version: 1.0.0
category: automation
tags: [farm, proxy, mechanical-enforcement, direct-ip, ssot, sqlite, fail-closed]
---
# Farm Mechanical Proxy Routing & Direct IP Enforcement

Use this skill when designing, maintaining, or auditing proxy routing across farm accounts (Phone Farm S7, GPM profiles, AGY CLI pools, or automation scripts).

## 1. Core Invariant: Anti-Memory Illusion (Chống Ảo Tưởng Memory)
- **Bẫy Ảo Tưởng Memory:** Khi Operator yêu cầu phân định mạng (ví dụ: tài khoản chính Direct IP, tài khoản farm 1:1 theo S7 proxy), TUYỆT ĐỐI KHÔNG ỷ lại vào text prompt, guideline Markdown hay persistent memory. Prompt không có tính cưỡng chế tại runtime và chắc chắn sẽ bị vi phạm khi chuyển ca hoặc đổi mô hình.
- **Nguyên Tắc Cơ Học Tối Cao:** Mọi chính sách phân định mạng bắt buộc phải được mã hóa cứng thành **Khóa cơ học (Mechanical Enforcement)** ở cả 3 tầng: Cơ sở dữ liệu, Module điều phối và Môi trường thực thi subprocess.

## 2. Kernel DNAT vs L7 Proxy (Singbox) & IP Whitelist Bypass Architecture
- **Bản chất Kernel DNAT:** Thay vì bắt RouterOS chạy máy ảo Docker gánh L7 Singbox gây 95% CPU, dùng MikroTik Kernel DNAT (`action=dst-nat`) chuyển tiếp thẳng gói tin ở tầng phần cứng dây cáp (wire-speed, CPU < 5%).
- **Điều kiện tiên quyết của Kernel DNAT:** Upstream proxy (MobiProxy/R3G) bắt buộc phải bỏ Password (chuyển sang `No-Auth` hoặc IP Whitelist). Nếu upstream còn password (`auth strong`), Kernel DNAT không thể can thiệp payload để điền User/Pass, kết nối sẽ văng `407 Proxy Authentication Required`.
- **MobiProxy Web v3 Modal Access Automation:** Nút "Áp dụng cho tất cả proxy" trên web MobiProxy có thể bị stub/không nạp lại tiến trình. Phải mở từng port qua menu 3 chấm `•••` -> `Cấu hình truy cập` -> chọn `Không xác thực` (`mode=none`) -> click chính xác `button#access-save` trong HTML5 dialog.
- **Fail-Closed Killswitch Invariant:** Khi proxy sập, điện thoại S7 bị timeout và hiện dấu chấm than mất mạng an toàn. MikroTik bắt buộc duy trì bộ 3 rule Killswitch: drop Direct WAN (`src-address=192.168.10.0/24`), drop UDP 53 (DNS leak), drop UDP 443 (QUIC bypass của TikTok Cronet engine).
- **R3G Multi-PPPoE Asymmetric Routing Traps:** Chi tiết kiến trúc 2 line 16 PPPoE trên R3G OpenWrt và quy trình thao tác `button#access-save` trên MobiProxy xem tại `references/r3g-multipppoe-asymmetric-routing-and-mobiproxy-dnat.md`.
- **MobiProxy HTML5 Dialog Automation & Kernel DNAT Canary:** Quy chuẩn tự động hóa click `button#access-save` trong `<form method="dialog">` của MobiProxy Web v3 và phương thức nạp rule Kernel DNAT lên trước rule Singbox trên MikroTik x86 xem tại `references/mobiproxy-html5-dialog-access-save-and-kernel-dnat-20261104.md`.
- **MobiProxy 32 Ports No-Auth Full Offload & Conntrack Tuning:** Chi tiết tự động hóa mở khóa No-Auth toàn bộ 32 port MobiProxy, tối ưu bộ thông số Conntrack (`tcp-established: 1h`) dọn bão kết nối ma và giải phóng CPU MikroTik x86 từ 97.6% về 1.8% xem tại `references/mobiproxy-full-dnat-offload-conntrack-tuning-20261105.md`.
- **MobiProxy 38 Ports Full DNAT Offload & Conntrack Tuning Protocol:** Toàn văn quy chuẩn kỹ thuật mở khóa No-Auth 38 port MobiProxy qua `#access-save`, nạp 38 rule Kernel DNAT lên trước Singbox, dọn bão kết nối ma Conntrack ép CPU MikroTik từ 97.6% về 0.4%, xác thực trạng thái mạng S7 `VALIDATED` qua ADB xem tại `references/mobiproxy-38ports-dnat-offload-conntrack-tuning.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
