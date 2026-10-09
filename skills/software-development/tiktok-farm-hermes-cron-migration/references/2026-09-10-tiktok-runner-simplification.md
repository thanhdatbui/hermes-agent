# tiktok_runner.py Simplification (2026-09-10)

## What Changed
Rewrote `tiktok_runner.py` from 1121-line picker/cohort/manifest-dependent runner to ~280-line self-contained time-of-day scheduler.

## What Was Removed
- All imports from `python_runner/hermes_cron/` modules (cohort.py, picker.py, manifest.py, hermes_cron_runner.py)
- `_load_active_manifest()`, `_due_entries()`, `_write_cohort_plan()`
- `_live_lease_path()`, `_lease_alive()`, `_kill_stale_pids()`, `_is_feed_runner_process()`
- `_terminal_cohort_machines()`, `_active_assignment_manifest_path()`
- PID management, lease management, cohort plan writing
- Complex environment forwarding (ALLOWED_FORWARD_ENV, REQUIRED_FORWARD_ENV, _ARG_MAP)
- Business script spawning (`python_runner/scripts/hermes_cron_runner.py`)

## What Was Added
- `_determine_row(now)` — pure function mapping (hour, day_parity) → (row, window_key)
- `_load_state()` / `_save_state()` / `_already_ran()` — simple JSON de-dup
- `_spawn_feed_session(row, now)` — direct Popen to PS1

## Schedule Table
```python
_SCHEDULE = {
    6:  {0: 2, 1: 1},   # 06h → Row2(even), Row1(odd)
    12: {0: 4, 1: 3},   # 12h → Row4(even), Row3(odd)
    18: {0: 6, 1: 5},   # 18h → Row6(even), Row5(odd)
    0:  {0: 8, 1: 7},   # 00h → Row8(even), Row7(odd)
}
# 02:00-05:59 = dead zone (exit 0 silently)
# Non-mapped hours (e.g. 13h, 15h) = exit 0 silently
```

## PS1 Command
```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File scripts/run-feed-session.ps1 \
  -Row <N> \
  -Preset full \
  -AccountWorkbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" \
  -SkipAccountWorkbookSync \
  -LocalRun \
  -MachineStartStaggerMs "2000,8000" \
  -RandomizeMachineOrder \
  -Run
```

## State File
`D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json`
```json
{
  "last_row": 2,
  "last_window": "2026-09-10T06",
  "last_run_at": "2026-09-10T06:30:00+07:00"
}
```

## Test Results (10/09/2026)
| Scenario | Expected | Result |
|---|---|---|
| Dead zone (03h) | silent exit 0 | ✅ |
| Even day 06h → Row2 | spawn Row2 | ✅ |
| Odd day 06h → Row1 | spawn Row1 | ✅ |
| Even day 12h → Row4 | spawn Row4 | ✅ |
| Odd day 18h → Row5 | spawn Row5 | ✅ |
| Non-scheduled hour (15h) | silent exit 0 | ✅ |
| De-dup (same window 2nd run) | silent exit 0 | ✅ |

## Pitfall
After simulation tests with `HERMES_CRON_NOW`, reset the state file:
```bash
echo '{"last_row": null, "last_window": null, "last_run_at": null}' > D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json
```
Otherwise the de-dup check will block real cron runs for already-simulated windows.
