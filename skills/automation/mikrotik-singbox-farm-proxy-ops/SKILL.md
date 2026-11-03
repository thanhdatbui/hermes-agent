---
name: mikrotik-singbox-farm-proxy-ops
description: "Vận hành, đồng bộ config Sing-box và quản trị proxy Farm MikroTik REST API."
version: 1.0.0
category: automation
tags: [mikrotik, singbox, proxy, rest-api, farm, payload-patching]
---
# MikroTik Sing-box Farm Proxy Operations & Inbound Parity

Use this skill when configuring or maintaining the Sing-box transparent/mixed container proxy on MikroTik RouterOS for multi-device Android farms (Kibe & Admin).

- OmniRoute ChatGPT-Web Turnstile 403 Burst RCA, Subnet Taint vs 4G/R3G & 3-Way Proxy Sync (2026-11-03): xem `references/omniroute-chatgpt-web-turnstile-subnets-and-r3g-mapping-20261103.md`. Khắc phục bão 403 Sentinel do dải IP MikroTik bị Cloudflare cắm cờ; tối ưu combo round-robin (`retryDelayMs: 1500`, `maxGlobalAttempts: 4`); đồng bộ 3 mắt xích GPM Profile <-> S7 Singbox <-> OmniRoute qua 16 port R3G (`tb.taadaa.click:5141-5158`) và reset PPPoE MikroTik kèm auto-update whitelist.
- Kiến trúc Sing-box Container vs. L3/L4 Hardware Kill-Switch & Anti-Leak Governance: xem `references/tiktok-farm-proxy-architecture-and-killswitch-governance.md`. Bài học bản chất rò rỉ IP qua QUIC/HTTP3 (UDP 443) & DNS leak (UDP 53) trên app TikTok; nguyên nhân bão gói tin 105k pps làm nghẽn 95% CPU MikroTik; bộ tứ phòng thủ L3/L4 Quad-Lock và chuẩn hóa Elite Anonymous trên Tinyproxy R3G.
- Tự Động Đồng Bộ 2 Chiều R3G & MobiProxy, Cơ Chế Captive Portal Chấm Than vs. Sing-box 1.12+ Migration: xem `references/r3g-mobiproxy-autosync-and-captive-portal-killswitch-lessons.md`. Khắc phục bẫy orphan script bằng auto-sync IP sang cả R3G và MobiProxy qua cron 5m; giải mã hiện tượng Wi-Fi dấu chấm than Android khi proxy sập; fix lỗi crash `route.default_domain_resolver` trên Sing-box 1.12+ và hạ log level về `warn` gộp đủ 160 máy.
- Giải Pháp Tách Sing-box Sang PC Host Để Giải Phóng CPU MikroTik & Kỷ Luật Thuyết Trình: xem `references/singbox-host-offload-architecture-and-coordinator-discipline.md`. Phân tích bản chất ngắt mạng veth làm nghẽn 95% CPU RouterOS; thiết kế tàng hình DNAT cổng 20001-20280 từ MikroTik sang PC Kibe (giữ nguyên IP/port trên S7, CPU RouterOS <15%); kỷ luật Coordinator trả lời trực diện, cấm để Advisor lải nhải lý thuyết dài dòng gây ức chế cho User.
- Phân Tích Lựa Chọn Node Host Cho Singbox & Giải Pháp Bỏ Hẳn Singbox Bằng Kernel DNAT: xem `references/singbox-elimination-and-host-node-tradeoffs.md`. Rủi ro cạn kiệt ephemeral ports làm đơ Playwright/ADB khi đặt Singbox lên PC Kibe vs. giải pháp đặt lên PC Admin; giải pháp triệt tiêu 100% Singbox bằng MikroTik Kernel DNAT chuyển thẳng HTTP CONNECT ra cổng 51xx Thái Bình (CPU MikroTik < 5%, zero host burden).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
