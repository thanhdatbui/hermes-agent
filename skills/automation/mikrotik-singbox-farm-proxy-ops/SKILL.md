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

## 1. Bài học về Inbound Port Mapping (Sing-box 20000 + M vs Sequential)
- **Cạm bẫy:** Khi sinh Inbound cho dàn Admin S7 (M201..M280), tuyệt đối KHÔNG gán sequential như `20201..20218` cho 32 máy rồi ghi đè vào Excel/SQLite, vì:
  1. Công cụ gán ADB và các script audit (`verify_farm_proxy_routing.py`, `set_proxy_farm_admin_adb.py`) định danh máy theo công thức bất biến:
     $$\text{Inbound Port} = 20000 + M$$
     Ví dụ: M203 bắt buộc trỏ `192.168.110.2:20203`, M272 bắt buộc trỏ `192.168.110.2:20272`.
  2. Nếu cấu hình Inbound `20201..20218` trên Sing-box nhưng máy lại nghe theo `20000 + M` (như M243 nghe `20243`), gói tin gửi vào port `20243` sẽ bị đóng kết nối ngay tại socket (`network is unreachable` hoặc `connection refused`) $\rightarrow$ Preflight kích hoạt kill-switch báo `blocked-proxy-vpn`.
- **Quy chuẩn bất biến:** 
  - Mỗi máy $M$ có Inbound duy nhất `mixed-mM` tại port `20000 + M`.
  - Hai máy dùng chung 1 Outbound R3G (ví dụ M203 và M204 dùng chung port 5141) thì cả 2 Inbound `mixed-m203` (port 20203) và `mixed-m204` (port 20204) đều trỏ về rule `proxy_m203` (hoặc outbound tương ứng tới `tb.taadaa.click:5141`).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
