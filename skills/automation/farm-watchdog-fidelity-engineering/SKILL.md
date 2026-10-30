---
name: farm-watchdog-fidelity-engineering
description: "Use when designing or fixing watchdogs and cron reports."
---
# Farm Watchdog & Reporting Fidelity Engineering

## 1. When to Use
Use when creating, auditing, modifying, or troubleshooting background watchdogs, scheduled cron reports, and alert aggregators on automation farms.
Applies whenever reports fail to reflect actual fleet health, mask dropped machines, report false aggregate metrics, or omit actionable failure details.
Also applies when compliance reports trigger high failure counts and agents enter a block death spiral due to misaligned guidance or false-positive subfolder blocks.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

## 2. Core Invariants Summary & Deep References
- **Fleet Bulkhead Isolation (Anti-Blanket Crash):** Khi lọc máy qua host guard, máy ngoài phạm vi chỉ bị loại bỏ kèm warning; tuyệt đối cấm ném exception làm crash cả batch. Chi tiết: [`references/fleet-bulkhead-isolation-and-watchdog-cluster-blindspot.md`](references/fleet-bulkhead-isolation-and-watchdog-cluster-blindspot.md).
- **Zero Reporting Blindspots:** Mọi cluster bắt buộc phải hiển thị trạng thái (kể cả khi chưa chạy hoặc thư mục date_live chưa tồn tại). Chi tiết: [`references/zero-reporting-blindspots-and-watchdog-fidelity.md`](references/zero-reporting-blindspots-and-watchdog-fidelity.md).
- **4-Way Multi-Tier Cron Sync Parity (Anti-Ghost Revert / Stale Runtime):** Khi sửa bất kỳ cron script hoặc wrapper runner nào, bắt buộc đồng bộ đồng nhất và đối soát SHA-256 trên cả 4 tầng (Repo, Runtime `%LOCALAPPDATA%`, Deploy `Hermes/deploy`, và OneDrive Sync Shared) kèm chạy `cron_sync_watchdog.py --force`. Chi tiết: [`references/four-way-cron-sync-parity-and-runtime-drift.md`](references/four-way-cron-sync-parity-and-runtime-drift.md).
- **Row-Based Follow Audit & Cooldown Breakdown:** Khi đối soát follow phiên ca, bắt buộc bóc tách trạng thái theo từng Row (Row đang nuôi, số máy dính nhả `FOLLOW_FAILED`, số máy dính cooldown 24h, số máy dính điều kiện tuổi/video). Chi tiết: [`references/row-based-follow-status-and-cooldown-audit.md`](references/row-based-follow-status-and-cooldown-audit.md).
- **Pre-Session Scrape T0 Parity (Anti-UNPROVEN in Session 1):** Bắt buộc cào snapshot T0 cho cả Session 1 (Feed-only) thay vì chỉ Session 2, vì Session 1 vẫn phát sinh follow tự nhiên/chéo; thiếu T0 khiến khoảng cách baseline > 4h bị Max Age Guard dán nhãn `UNPROVEN`. Chi tiết: [`references/watchdog-follow-reconcile-session1-t0-scrape-blindspot.md`](references/watchdog-follow-reconcile-session1-t0-scrape-blindspot.md).
- **Pre-Session Scrape Timeout & Dynamic Pool Budget:** Khi cào pre-session T0 cho dynamic pool (80+ nick), timeout 90s dễ làm kill ngầm dẫn đến stale baseline >4h và nhãn UNPROVEN ảo; bắt buộc >=25 workers và timeout >=180s. Chi tiết: [`references/pre-session-scrape-timeout-and-stale-baseline-unproven.md`](references/pre-session-scrape-timeout-and-stale-baseline-unproven.md).
- **Zero-Friction Morning Priority Auto-Dispatch:** CẤM bắt user nhớ set tay topic Linh Dương cuối ngày. Tự động hoá 100% bằng script cron `no_agent: true` quét SQLite `state.db` của Hermes, dùng Gemini AG Pool (:20129) suy luận và bắn tin nhắn kèm Direct Link 1-click `t.me/c/...` về DM điều phối lúc 06:00 sáng (chống lỗi xoá topic). Chi tiết: [`references/zero-friction-morning-linh-duong-auto-dispatch.md`](references/zero-friction-morning-linh-duong-auto-dispatch.md).

