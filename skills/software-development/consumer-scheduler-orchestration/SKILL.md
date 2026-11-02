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

## Steps

### 1. Central base module (automation_core/scheduler/base.py)

Dung `SchedulerConfig` dataclass de moi consumer chi can khai bao:
- `name` — slug (e.g. "tiktok_reg")
- `project` — device-lock project label
- `slot_hour` / `slot_minute` — thoi diem chay
- `command_builder` — callable(root) -> list[str] goi script co san
- `project_root` — duong dan consumer repo

Shared helpers tu base.py:
- `read_state()` / `write_state()` — atomic via tmp+rename
- `append_log()` — JSONL voi timestamp/event/host
- `choose_run_at()` / `next_plan()` — schedule next slot
- `_device_lock_available()` — pre-flight check (non-fatal)
- `run_consumer()` — subprocess voi timeout + lock policy
- `serve()` — main loop (poll → wait → run → plan tomorrow)
- `build_parser()` / `main()` — CLI wrapper

### 2. Consumer scheduler.py (thin wrapper)

```python
from automation_core.scheduler.base import SchedulerConfig, main as base_main

def build_command(project_root):
    return [sys.executable, str(project_root / "path/to/existing_script.py")]

def build_config():
    return SchedulerConfig(
        name="tiktok_reg", project="tiktok-reg",
        slot_hour=9, slot_minute=30,
        command_builder=build_command, project_root=PROJECT_ROOT,
    )

def main(argv=None): return base_main(build_config(), argv)
if __name__ == "__main__": raise SystemExit(main())
```

### 3. Unified tray (automation_core/scheduler/tray.py)

- `SchedulerManager` doc `processes: dict[str, Popen]`
- Start/stop via `subprocess.Popen` voi `--live` flag
- Read state.json per scheduler de hien status
- pystray icon voi menu: Start All / Stop All / View Status / Quit

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
