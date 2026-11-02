---
name: windows-service-watchdog
description: Patterns and verification checklist for building resilient Windows watchdog and auto-healing scripts (PowerShell, Python, Batch) that supervise long-running services or hardware pools — single-instance enforcement, anti-flapping cooldowns, rate limits, child process cleanup, consecutive failure thresholds, and live verification.
category: devops
tags: [watchdog, process-supervision, powershell, python, windows, mutex, msvcrt, auto-healer, cooldown, rate-limit, health-checks, restart-thresholds]
---
# Windows Service Watchdog / Process Supervision

**Trigger**: Any task involving managing a long-running Windows service/process via a watchdog script (PowerShell/Batch) that must:
- Enforce single-instance execution (no duplicate watchdogs)
- Track and clean up child processes to prevent accumulation
- Implement consecutive failure thresholds before restart
- Provide clean process termination with grace periods before restart
- Log structured evidence for verification

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
