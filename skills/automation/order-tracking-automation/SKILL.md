---
name: order-tracking-automation
description: "Use for orders, mail codes, carrier scans, or dashboards."
version: 1.0.0
license: Proprietary
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [orders, tiktok-shop, outlook, hotmail, tracking, carrier-api, dashboard, cron]
    related_skills: [hotmail-outlook-automation, evidence-first-delivery, taadaa-farm-ops-rules]
---
# Order Tracking Automation

## Purpose

Use this class skill for order-management workflows where an order begins inside a shopping app/account, a mailbox may reveal the carrier tracking code, carrier systems provide route events, and a local dashboard presents canonical state.

The central design rule is a multi-channel discovery and tracking pipeline:

```text
[Discovery Channel A (Passive)] Webmail (Outlook GPM) -> parse dispatch email
[Discovery Channel B (Active)]   TikTok App (Farm Device) -> in-app order detail via atx-agent JSONRPC
                                     │ (tracking code + carrier)
                                     ▼
Carrier API/page (SPX/J&T/Ninja) -> monitor shipment scans and local-hub arrival
Dashboard/JSON/Excel             -> display the same canonical order state
```

Do not rely solely on mailbox polling as tracking code discovery. TikTok Shop and sellers frequently omit or delay tracking emails until after delivery; in-app order inspection on the farm device is the authoritative zero-delay source of truth. Carrier tracking remains the sole source for transit and hub events.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
> - `references/order-lifecycle-execution-order-and-timeout-budget.md`: Quy chuẩn đảo thứ tự thực thi Phase 2 Web-First, chặn nghẽn ADB bóc mã đơn mới (`max_app_syncs = 1`), bọc `TimeoutExpired` chống crash cron runner, và cơ chế dọn lock mồ côi không có trường machine.
> - `references/zero-token-cron-wrapper-and-guard-wiring.md`: Bẫy mất cờ `no_agent: true` khi update cronjob (Hermes runtime default False), quy trình 3 bước remediate, và lỗ hổng blind-spot `if "no_agent" in ti` trong `guard_cronjob_safety.py`.
> - `references/farm-voucher-order-logistics-and-jt-tracking.md`: Cú pháp mã bưu cục J&T viết tắt theo mã tỉnh `(ĐNG)Đống Đa`, tham số tra cứu `cellphone`, và cơ chế cảnh báo khi hàng về bưu cục phát giao về địa chỉ.
> - `references/order-lifecycle-state-machine-and-auto-retire.md`: Chuẩn hóa máy trạng thái 3 pha, chốt chặn kép 2 lớp (Layer 1 active_ids filter + Layer 2 in-script early exit) chống spam báo động đơn đã ký nhận/terminal, và bẫy lệch nhánh tiêu đề ký nhận.
