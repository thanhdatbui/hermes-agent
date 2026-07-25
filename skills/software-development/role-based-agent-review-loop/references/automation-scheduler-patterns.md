# Automation Scheduler Design Patterns

Reference for designing schedulers in the D:/Taadaa automation ecosystem. Covers tiktok-luoi, gmail-reg, and 4 TikTok consumer schedulers.

## Scope Rules

**CRITICAL — user corrected multiple times:**

- Scheduler **calls existing scripts** in consumer repos (e.g., `run_all.ps1`), NOT create new automation scripts
- Scope = scheduler.py + state management + tray icon. NOT the underlying automation logic
- Do NOT expand scope to "improve" or "refactor" the scripts being scheduled

## Timeline Constraints (Vietnam time UTC+7)

```
Working hours: 08:00 - 22:00

Reserved blocks (DO NOT schedule other scripts):
  12:00 - 14:00  → tiktok-luoi nuoi acc
  17:00 - 19:00  → tiktok-luoi + gmail-reg

Available slots:
  08:00 - 12:00  (4h)
  14:00 - 17:00  (3h)
  19:00 - 22:00  (3h)

Default schedule per machine:
  08:00 → gmail-reg (existing)
  09:30 → tiktok-reg (right after gmail-reg)
  14:00 → tiktok-log-in
  15:30 → tiktok-add-bao-mat-f2a
  19:00 → add-mail-khoi-phuc
  20:30 → retry/recovery slot
```

## Device Lock Lifecycle

**Use `automation_core.device_lock` (already in core).**

Lock policy for scheduler:

| Script outcome | Lock action | Reason |
|---------------|-------------|--------|
| Script completed normally (success OR fail) | `lock.release()` | Fail is normal, user debugs manually |
| Script crash/timeout/hang | `lock.set_status("handoff")` | Keep lock so user can debug without interference |

**Key insight**: "Fail" means script ran to completion but result was failure (e.g., reg failed). This is normal — release lock immediately. "Block" means script crashed mid-execution — hold lock for debugging.

## Subprocess Policy

- **Timeout**: 90 minutes per subprocess call
- **No hard deadline**: If script runs past 22:00, let it finish. Do NOT force-stop.
- **No notifications on fail**: Fail is expected. User handles debug manually.

## Tray Icon Pattern

- **Unified tray**: 1 tray icon manages ALL schedulers (not 1 tray per script)
- Uses `pystray` library
- Status display: read state.json of each scheduler
- Menu: Start All / Stop All / View Status / Quit

## Architecture Pattern (copy from gmail_scheduler.py)

Each consumer's `scheduler.py` should:

1. **State management**: `state.json` (atomic writes via temp + os.replace)
2. **Logging**: `scheduler.jsonl` (append-only JSONL events)
3. **Control**: `control.json` (tray icon writes, scheduler reads)
4. **Main loop**: `serve()` pattern
   - Poll time (30s interval)
   - Check if in time window
   - Pre-flight: check device lock
   - Run subprocess with timeout
   - Log result
   - Release/hold lock per policy above

## Pre-flight Lock Check

Before running script on device:

```python
# Read device lock state
lock_exists = device_lock_paths(machine, serial).exists()

if lock_exists:
    owner = read_lock_owner(path)
    if owner.status in ["handoff", "blocked"]:
        if owner.pid is dead and allow_takeover:
            → Takeover lock, run script
        else:
            → Skip device, try next
    elif owner.project != current_script:
        → Skip device (different project using it)
else:
    → Acquire lock, run script
```

## Pitfalls

- **Do NOT use ThreadPoolExecutor** for multiple scripts on same machine — must be sequential
- **Do NOT put scheduler logic in automation-core** — only `time_windows.py` shared mechanism. Scheduler.py stays in consumer repo per AGENTS.md scope rules
- **Do NOT force-stop scripts at hard deadline** — user explicitly rejected this
- **Do NOT add notification/alert on fail** — fail is normal operation
- **Do NOT create per-script tray icons** — user wants unified tray

## Reference Files

- `/d/Taadaa/register gmail/gmail_scheduler.py` — pattern to copy
- `/d/Taadaa/tiktok-luot nuoi acc/python_runner/scheduler/` — tray + state pattern
- `/d/Taadaa/automation-core/src/automation_core/device_lock.py` — lock mechanism
- `/d/Taadaa/automation-core/src/automation_core/scheduler/time_windows.py` — shared time slots
