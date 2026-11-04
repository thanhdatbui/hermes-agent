---
name: mikrotik-singbox-farm-proxy-ops
description: "Vận hành, đồng bộ config Sing-box và quản trị proxy Farm MikroTik REST API."
version: 1.0.0
category: automation
tags: [mikrotik, singbox, proxy, rest-api, farm, payload-patching]
---
# MikroTik Sing-box Farm Proxy Operations & Inbound Parity

Use this skill when configuring or maintaining the Sing-box transparent/mixed container proxy on MikroTik RouterOS for multi-device Android farms (Kibe & Admin).

- Khắc phục Singbox Loopback 16 Máy Kibe & Chuẩn Hóa Cấu Hình Gộp 112 Máy (2026-11-04): xem `references/kibe-16machines-singbox-loopback-and-pppoe-mapping-20261104.md`. Bóc tách lỗi loopback khi outbound bị điền nhầm thành cổng inbound 200xx gây cạn socket OS và timeout `ifconfig.me/ip`; quy chuẩn khóa mapping cứng cho 14 máy MikroTik PPPoE (10001..10007, admin@1) và 2 máy KhoaLee (16002); quy trình nạp cấu hình minified qua REST API `/rest/file/*8072575` và restart container an toàn.
- OmniRoute ChatGPT-Web Turnstile 403 Burst RCA, Subnet Taint vs 4G/R3G & 3-Way Proxy Sync (2026-11-03): xem `references/omniroute-chatgpt-web-turnstile-subnets-and-r3g-mapping-20261103.md`. Khắc phục bão 403 Sentinel do dải IP MikroTik bị Cloudflare cắm cờ; tối ưu combo round-robin (`retryDelayMs: 1500`, `maxGlobalAttempts: 4`); đồng bộ 3 mắt xích GPM Profile <-> S7 Singbox <-> OmniRoute qua 16 port R3G (`tb.taadaa.click:5141-5158`) và reset PPPoE MikroTik kèm auto-update whitelist.
- Triệt Tiêu Loopback Proxy Singbox & Preflight Invariant Auto-Wiring (2026-11-04): xem `references/singbox-loopback-and-guardgate-autowiring-20261104.md`. Bóc tách bão timeout do 16 máy Kibe (M33-M38, M71-M80) bị trỏ nhầm outbound về chính cổng inbound 200xx; chuẩn hóa mapping sang 7 cổng MikroTik 10001-10007 và KhoaLee 16002; bài học kiến trúc Auto-wire GuardGate guidance O(1) từ rules.json cho Worker.
- Kiến trúc Sing-box Container vs. L3/L4 Hardware Kill-Switch & Anti-Leak Governance: xem `references/tiktok-farm-proxy-architecture-and-killswitch-governance.md`. Bài học bản chất rò rỉ IP qua QUIC/HTTP3 (UDP 443) & DNS leak (UDP 53) trên app TikTok; nguyên nhân bão gói tin 105k pps làm nghẽn 95% CPU MikroTik; bộ tứ phòng thủ L3/L4 Quad-Lock và chuẩn hóa Elite Anonymous trên Tinyproxy R3G.
- Tự Động Đồng Bộ 2 Chiều R3G & MobiProxy, Cơ Chế Captive Portal Chấm Than vs. Sing-box 1.12+ Migration: xem `references/r3g-mobiproxy-autosync-and-captive-portal-killswitch-lessons.md`. Khắc phục bẫy orphan script bằng auto-sync IP sang cả R3G và MobiProxy qua cron 5m; giải mã hiện tượng Wi-Fi dấu chấm than Android khi proxy sập; fix lỗi crash `route.default_domain_resolver` trên Sing-box 1.12+ và hạ log level về `warn` gộp đủ 160 máy.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
