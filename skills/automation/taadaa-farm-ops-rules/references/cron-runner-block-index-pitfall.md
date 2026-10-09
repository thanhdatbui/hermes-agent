# Cron Runner Block-Index Pitfall (2026-09-10)

## Problem

`tiktok_runner.py` cron wrapper calls `build_cohort_plan()` from `python_runner/hermes_cron/cohort.py`. The validator at line 108 hard-codes:

```python
if block not in (1, 2, 3) or session not in (1, 2, 3):
    raise ValueError("cohort entry session is invalid")
```

Farm runs 4 Ca/day (block_index 1-4 for Row 2/4/6/8). When block 4 (Ca 4, Row 8, 00:00) exists in the manifest, the entire `build_cohort_plan()` throws → `tiktok_runner.py` logs "active manifest has no valid cohort" → **silently skips all dispatch**.

## Impact

- Cron `phase9-runner-tiktok-feed` runs every 15 min but produces zero output (silent).
- No machines get dispatched via cron. Farm sits idle until manual intervention.
- Manifest `/runtime/kibe/cron-state/manifests/<day>/ACTIVE.json` points to a manifest with block_index 4 entries → always crashes cohort builder.

## Workaround

Bypass the cron runner entirely. Dispatch feed sessions directly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-feed-session.ps1 `
  -Row <ROW> -Preset full `
  -AccountWorkbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" `
  -SkipAccountWorkbookSync -LocalRun `
  -MachineStartStaggerMs "2000,8000" -RandomizeMachineOrder -Run
```

Or via Python directly (use automation venv, NOT Hermes venv):

```bash
"D:/Taadaa/python-envs/automation/Scripts/python.exe" \
  python_runner/run_tiktok.py --mode multi-machine-feed-session \
  --machines 1,...,80 --account-row-index <ROW> ...
```

## Zombie processes

When the cron picker manages to spawn Row 8 processes at the wrong time (e.g. 14:00 for a 00:00 slot), those become zombies with stale device locks. Kill them manually:
```bash
wmic process where "name='python.exe' and commandline like '%run_tiktok%'" get ProcessId,CommandLine
taskkill /PID <pid> /F
```

Device locks at `~/.codex/device-locks/machine_<N>.lock.json` clear via `reap-dead-owner-locks` cron after ~15 min.

## Root fix needed

`cohort.py` line 108 should accept block 1-4 (or be configurable). The user wants this entire picker/cohort/manifest layer simplified — just read Row from `taikhoan_run_safe.xlsx` by time of day.
