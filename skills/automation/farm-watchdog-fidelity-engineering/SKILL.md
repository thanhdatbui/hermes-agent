---
name: farm-watchdog-fidelity-engineering
description: "Use when designing or fixing watchdogs and cron reports."
---
# Farm Watchdog & Reporting Fidelity Engineering

## 1. When to Use
Use when creating, auditing, modifying, or troubleshooting background watchdogs, scheduled cron reports, and alert aggregators on automation farms.
Applies whenever reports fail to reflect actual fleet health, mask dropped machines, report false aggregate metrics, or omit actionable failure details.
Applies when patch pipelines suffer paralysis from repository-wide baseline hashing, false-positive scope violations from receipt logs, or guard self-protection traps. BẮT BUỘC áp dụng Scoped Transaction Architecture (chỉ hash target files, cách ly runtime artifacts). See `references/baseline-hash-traps-and-scoped-transaction-architecture.md` and `references/pipeline-overengineering-paralysis-and-scoped-transaction.md`.
Also applies when transient security checkpoints (Google Phone Checkpoint `challenge/iap`, SMS rate limit) are mishandled by dumping into permanent blacklists, bricking candidates forever ("ngọng luôn"). BẮT BUỘC dùng cơ chế Dynamic Cooldown kèm `retry_after` tự động hạ nhiệt và tự động bốc lại khi hết hạn (Zero-Touch Self-Healing). See `references/transient-checkpoint-cooldown-vs-permanent-blacklist-trap.md`.
Also applies when multi-shift watchdogs (sáng/chiều/tối) confuse daily accumulated metrics with per-shift results, reporting phantom failures on empty shifts. BẮT BUỘC cô lập shift metrics khỏi daily metrics và kích hoạt Zero-Noise Watchdog khi ca trống. See `references/multi-shift-watchdog-metric-isolation-and-zero-noise.md`.
Also applies when TikTok Farm Dashboard shows discrepancy between Bot Following and Web Following delta ("Bot +X vs Web +Y"). BẮT BUỘC dùng quy trình Triage O(1) bóc tách `session_action_stats` vs `snapshots` vs `follow_state_*.json`, và khử follow ảo khi `follow_failed is True` (bị TikTok nhả sau vuốt). See `references/dashboard-web-vs-bot-following-reconciliation-triage.md`.
Also applies when 24H Heartbeat aggregator reports false STALE/ANOMALY due to static JSON state files or `None.endswith(".py")` parsing crashes on LLM cron jobs. BẮT BUỘC fallback scheduler ledger (`jobs.json`) an toàn bằng `(j.get("script") or "").endswith(".py")` và reconcile anomalies khi `last_status == "ok"`. See `references/scheduler-ledger-fallback-and-heartbeat-stale-reconciliation.md`.
Also applies when watchdogs wrap `CronRun` with premature context manager exit (`with run_ctx as run:` closed before audit logic), leaving `stdout` completely empty and silencing Telegram delivery on `no_agent: True` jobs. BẮT BUỘC bọc trọn vẹn toàn bộ vòng đời tác vụ trong `with run_ctx as run:`. See `references/cronrun-context-manager-premature-exit-and-watchdog-mute.md`.
Also applies when Coordinator claims affirmative execution ("Đã dispatch thành công", "Đã giao việc") but only triggered a background cronjob (`cronjob(action='run')`) without an active worker `task_id`, triggering the Gateway Receipt Enforcer warning banner (`⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`). BẮT BUỘC phân biệt rạch ròi Worker Execution vs Scheduler Trigger. See `references/receipt-enforcer-hook-and-phantom-dispatch-flagging.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
