---
name: consumer-scheduler-orchestration
description: Build per-consumer-repo schedulers that call existing scripts at fixed daily slots, share a base from a central library, respect device-lock pre-flight, and expose a unified tray. Covers dry-run semantics, optional-dep imports, lock policy, ad-hoc verification, and fleet stop/start operations (Scheduled Task wrappers, PYTHONPATH shadow, proxy watcher keep-alive).
tags:
  - scheduler
  - device-lock
  - consumer-repos
  - tray-icon
  - orchestration
  - time-windows
  - pystray
  - fleet-operations
  - scheduled-task
triggers:
  - "scheduler cho nhieu consumer repo"
  - "unified tray quan ly nhieu scheduler"
  - "time windows voi device lock"
  - "copy gmail_scheduler pattern sang TikTok"
  - "build scheduler with slot times + reserved blocks"
  - "dung toan bo scheduler automation"
  - "bat lai scheduler automation"
  - "stop/start scheduler fleet"
  - "schtasks /run TikTokScheduler"
  - "migrate scheduling sang hermes cron"
  - "bo window schedule"
  - "lich ngau nhien per account"
  - "hermes cron orchestration farm"
---
# Consumer Scheduler Orchestration

Pattern cho viec xay dung nhieu scheduler moi cai trong 1 consumer repo, chung 1 base module tu central library (`automation_core.scheduler`), voi device lock pre-flight, lock policy, va unified tray.

## Khi nao dung

- Co nhieu consumer repo moi cai co 1 script chay, can gioi lich chay theo slot (09:30, 14:00, ...)
- Can 1 shared library de tranh duplicate state/log/device-lock code
- Can unified system tray de start/stop/status tat ca schedulers
- Can lock policy ro rang: success → release, crash/timeout → handoff

## Architecture

```
automation-core/src/automation_core/scheduler/
├── __init__.py              # exports
├── time_windows.py          # AVAILABLE_SLOTS, RESERVED_BLOCKS, WORK_START/END, is_available(), get_slot_time()
├── base.py                  # SchedulerConfig dataclass + serve() + run_consumer() + state/log helpers
└── tray.py                  # SchedulerManager + pystray icon (deps optional)

<consumer-repo>/scheduler.py # thin wrapper: 1 config, calls existing script
```

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
