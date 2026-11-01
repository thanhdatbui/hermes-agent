---
name: farm-network-gate-contract
description: "Use when designing farm Wi-Fi/proxy safety gates."
version: 1.0.0
category: automation
tags: [farm, wifi, proxy, ssot, fail-closed, device-lock, evidence]
---
# Farm Network Gate Contract

Use this skill when a multi-device Android farm needs reliable Wi-Fi assignment, proxy mapping, recovery, or a guard against ad-hoc network changes. The goal is not merely to reconnect a phone: it is to make a wrong SSID/PSK/proxy mapping mechanically difficult or impossible.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
> - `references/ssot-proxy-identity-vs-mechanical-hop-and-isp-ceilings.md`: Quy chuẩn phân lập SSOT Proxy Identity vs Mechanical Hop L3/L4, cấm gán IP WAN động/Tailscale lên S7.
> - `references/mobiproxy-scan-guard-and-r3g-direct-wan-architecture.md`: Cấu trúc Anti-Scan (Scan Guard) Whitelist, Direct WAN OpenWrt, định tuyến chuẩn Farm (S7 -> 192.168.110.2:202xx -> Sing-box -> R3G), bảng đối soát 83 proxy toàn farm (160 phone + 4 port Hot Standby dự phòng), phạm vi line proxy ông anh cho (khoalee), kiến trúc Inbound Singbox `20000 + M` (cấm cạm bẫy sequential 20201..20216 gây đè IP Đà Nẵng), điểm mù của Preflight Check đơn lẻ (Single-Device Preflight Blind Spot), công cụ thẩm định tự động `verify_farm_proxy_routing.py`, nguyên nhân gốc rễ dồn 1 IP R3G (Tinyproxy comment `#Bind`), đặc tính dải CGNAT Viettel quay số lại và Invariant bảo vệ Tailscale daemon trên router nhúng R3G.
> - `references/mechanical-interceptor-gap-and-network-device-lockdown.md`: Phân tích nguyên nhân Prompt-based Gates thất bại trước Shortcut Bias của Coordinator, cơ chế Hard Interceptor chặn sửa tay khi có intent fix lỗi, và vùng cấm tuyệt đối khi thao tác hạ tầng mạng nhúng (chống drop Tailscale trên router R3G).
> - `references/farm-proxy-quarantine-and-batch-isolation.md`: Quy trình cách ly 4 tầng (Excel -> SQLite -> Safe Run Workbook -> ADB :0) khi cụm proxy sập hoặc dồn 1 IP Egress, kỷ luật cấm báo cáo cổng LIVE lấp liếm khi chưa đối soát IP collision.
> - `references/anti-hallucination-and-network-collision-audit.md`: Căn bệnh đánh đồng HTTP 200 với Mục tiêu hoàn thành, lỗ hổng của Regex Completion Claims, Math Assert bắt buộc đối soát tập hợp Egress IP, và quy tắc khôi phục router nhúng R3G (rút cắm nguồn 10s, không cần cắm PC).
> - `references/evidence-driven-execution-and-anti-gate-bloat-20261101.md`: Nguyên lý Evidence-Driven Execution chống Completion Bias, phân tích vì sao không đẻ thêm Gate rác ngọn gây bại liệt, và tiêu chuẩn đối soát bằng chứng cứng (Hard Proof) trên mọi lĩnh vực.
> - `references/anti-hallucination-proxy-math-assert-and-quarantine-protocol.md`: Invariant Math Assert (len(set(IPs)) == N) chống báo cáo láo proxy LIVE khi bị chùm IP, kèm quy trình cách ly Quarantine ADB :0 an toàn.
> - `references/r3g-direct-wan-and-anti-fake-telemetry-discipline-20

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
