# Controlled watcher restart — tray auto-respawn (2026-08-08)

Goal: load a new `gan_proxy_fleet.py watch` code version into the live fleet
without touching unrelated schedulers. The tray **auto-respawns** the watcher,
so a full restart is: verify tree → check locks → kill tree → wait → verify new.

## 1. Identify the watcher process tree (PowerShell, not bash)

The watcher is a TREE with the SAME command line on both nodes:
- parent `python.exe` = `D:\Taadaa\python-envs\automation\Scripts\python.exe`
- child `python.exe` = `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe`
Both run `gan_proxy_fleet.py watch --all --workers 80 --mapping ... --runtime ... --poll-interval 30`.
Parent is spawned by a hidden powershell wrapper (`run-proxy-watcher.ps1` via
`tiktok-scheduler-tray.ps1`, task `TikTokAllSchedulerTray`).

**git-bash pitfalls — do NOT inline PowerShell:**
- bash eats `$_` inside double quotes → use a `.ps1` file under the runtime dir
  and run `powershell -NoProfile -ExecutionPolicy Bypass -File find-watcher.ps1`.
- `taskkill //PID <id> //T //F` fails in git-bash (`Invalid argument/option - '//PID'`)
  → use PowerShell `Stop-Process -Id <pid> -Force` (or `cmd /c "taskkill /PID <id> /T /F"`).

Reusable probe (.ps1 saved to `%RUNTIME%\find-watcher.ps1`, deleted after):

```powershell
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
         Where-Object { $_.CommandLine -match 'gan_proxy_fleet' }
if (-not $procs) { Write-Output "NO_WATCHER"; exit 0 }
foreach ($p in $procs) {
    Write-Output ("PID=" + $p.ProcessId + " PPID=" + $p.ParentProcessId + " Created=" + $p.CreationDate)
}
```

## 2. Preflight — no locks held by the watcher PIDs

The watcher only holds per-event device locks. Verify none belong to it before
killing (a mid-event kill could strand a lock):

```bash
cd /c/Users/Kibe/.codex/device-locks
grep -l "<pid1>\|<pid2>" machine_*.lock.json serial_*.lock.json   # empty = safe
```

Zero hits → kill. Locks owned by OTHER consumers (tiktok-upload etc.) are
untouched — this is exactly what we want.

## 3. Kill and let the tray respawn

`TikTokAllSchedulerTray` runs a 15-second `Windows.Forms.Timer` →
`Ensure-ProxyWatcher` → `Start-ProxyWatcher`, which re-runs
`run-proxy-watcher.ps1`. So: kill BOTH python nodes, wait ~15-60s, and a NEW
tree appears automatically with fresh PIDs and a new log file
`watcher-logs/proxy-watcher-<yyyyMMdd-HHmmss>-*.stdout.log`.

Note: killing only the child may leave the parent holding the singleton lock;
kill the whole tree. The singleton lock (`runtime/watcher-singleton.lock`,
msvcrt) is released on process death, so the respawn acquires it cleanly —
empty stderr + new run dir proves it.

## 4. Worker spawn is INCREMENTAL — be patient

76 machine dirs do not all appear at once. Observed pace for
`--workers 80` on this box: 17 → 26 → 38 → 56 → 72 → 76 over ~4 minutes
(poll cadence 30 s). A missing `machine-<N>` dir in the first minutes is NOT
a failure. Re-check every ~45-60 s until the count is stable.

## 5. Verification checklist (all real artifacts, no self-report)

- New PIDs exist, old PIDs gone (`Get-Process -Id <old> -ErrorAction SilentlyContinue` empty).
- New log file `proxy-watcher-<fresh-ts>.stdout.log` exists; **stderr empty** (no singleton error).
- New run hash dir `<runtime>/<new-hash>/` created after kill time.
- Target machine worker: `<runtime>/<new-hash>/machine-<N>/watch-events.jsonl`
  contains `WATCH_WORKER_STARTED` → `WATCH_MONITORING` → (event)
  `WATCH_EVENT_VERIFIED_SUCCESS` for the machine of interest.
- Cleanup: delete the temporary `.ps1` probe; repo working tree untouched by
  the restart itself.

## Why not touch the tray/task

Only restart `TikTokAllSchedulerTray` itself when the tray is dead
(Last Result 267014, no watcher, see SKILL.md 2026-08-05 case). If the tray is
alive, killing the watcher tree is sufficient and is the minimal action that
loads new code.