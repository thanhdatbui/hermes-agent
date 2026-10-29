---
name: farm-watchdog-fidelity-engineering
description: "Use when designing or fixing watchdogs and cron reports."
---
# Farm Watchdog & Reporting Fidelity Engineering

## 1. When to Use
Use when creating, auditing, modifying, or troubleshooting background watchdogs, scheduled cron reports, and alert aggregators on automation farms.
Applies whenever reports fail to reflect actual fleet health, mask dropped machines, report false aggregate metrics, or omit actionable failure details.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

## 2. Core Invariants Summary & Deep References
- **Fleet Bulkhead Isolation (Anti-Blanket Crash):** Khi lọc máy qua host guard, máy ngoài phạm vi chỉ bị loại bỏ kèm warning; tuyệt đối cấm ném exception làm crash cả batch. Chi tiết: [`references/fleet-bulkhead-isolation-and-watchdog-cluster-blindspot.md`](references/fleet-bulkhead-isolation-and-watchdog-cluster-blindspot.md).
- **Zero Reporting Blindspots:** Mọi cluster bắt buộc phải hiển thị trạng thái (kể cả khi chưa chạy hoặc thư mục date_live chưa tồn tại). Chi tiết: [`references/zero-reporting-blindspots-and-watchdog-fidelity.md`](references/zero-reporting-blindspots-and-watchdog-fidelity.md).

