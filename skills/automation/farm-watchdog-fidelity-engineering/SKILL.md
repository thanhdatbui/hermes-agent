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
- **4-Way Multi-Tier Cron Sync Parity (Anti-Ghost Revert / Stale Runtime):** Khi sửa bất kỳ cron script hoặc wrapper runner nào, bắt buộc đồng bộ đồng nhất và đối soát SHA-256 trên cả 4 tầng (Repo, Runtime `%LOCALAPPDATA%`, Deploy `Hermes/deploy`, và OneDrive Sync Shared) kèm chạy `cron_sync_watchdog.py --force`. Cấm tuyệt đối đặt script tại `~/.hermes/scripts` vì Windows Scheduler chỉ đọc `%LOCALAPPDATA%\hermes\scripts`. Tạo/sửa cronjob bắt buộc `cronjob(action='run')` test ngay tại chỗ. Chi tiết: [`references/four-way-cron-sync-parity-and-runtime-drift.md`](references/four-way-cron-sync-parity-and-runtime-drift.md).
