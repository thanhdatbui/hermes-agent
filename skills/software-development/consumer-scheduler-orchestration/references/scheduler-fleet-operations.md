# Scheduler fleet operations (Taadaa farm) — inventory, stop/start, respawn behavior

Session-proven facts (2026-08-07). All paths Windows; terminal via git-bash (MSYS).

## Ownership model — why killing python children doesn't stop automation

Every scheduled scheduler is launched by a **Scheduled Task whose action is a
`powershell.exe -Command "& { ... & python <scheduler> ... }"` wrapper**. The
wrapper process stays alive (its state shows `Running`), and the task's own
supervision restarts the python child when it dies. So:

- `taskkill /F` on the python PID → child respawns within seconds.
- To stop: `schtasks /end /tn <task>` OR kill the wrapper PID with `taskkill /PID <wrapper> /T /F`
  (children die with the tree).
- `wmic process where "name like '%python%'" get ProcessId,CommandLine` is the
  reliable inventory (tasklist silent-fails in git-bash).

## Task table (exact actions)

| Task | Spawns | Restart |
|---|---|---|
| `TikTokScheduler` | feed: `D:\Taadaa\python-envs\automation\Scripts\python.exe -m scheduler --live --poll-seconds 30` (cwd tiktok-luot nuoi acc; PYTHONPATH=`D:\Taadaa\tiktok-luot nuoi acc\python_runner`) | `schtasks /run /tn TikTokScheduler` |
| `TikTokScheduleRecovery` | `python -m scheduler.recovery_runtime --state ...\scheduler-state.json --watch --poll-seconds 15 --dispatch --enable-live-recovery` | `schtasks /run /tn TikTokScheduleRecovery` |
| `GmailRegistrationScheduler` | Py312 `gmail_scheduler.py --live --poll-seconds 30` (env GMAIL_*: EXCEL, DEVICE_MAP, WRITER/EXPECTED/WORKER id, ASSIGNMENT_MANIFEST) | `schtasks /run /tn GmailRegistrationScheduler` |
| `TikTokAllSchedulerTray` | `tiktok-scheduler-tray.ps1` (STA) → at logon runs `Start-AllSchedulers` + proxy watcher | `schtasks /run /tn TikTokAllSchedulerTray` |
| `GmailRegistrationSchedulerTray` / `TikTokSchedulerTray` | tray UIs (don't touch for stop/start) | — |
| `GmailSchedulerWake` / `TikTokSchedulerWake` | wake-on-schedule helpers (harmless) | — |

4 consumer schedulers have NO own task — they are spawned by the unified tray's
`Start-AllSchedulers` (`automation-core\src\automation_core\scheduler\tiktok-scheduler-tray.ps1:324`):

- `tiktok_reg` → `D:\Taadaa\Tiktok_Reg\scheduler.py --live` (slot 09:30)
- `tiktok_login` → `D:\Taadaa\tiktok-log-in\scheduler.py --live` (slot 14:00)
- `tiktok_2fa` → `D:\Taadaa\tiktok-add-bao-mat-f2a\scheduler.py --live` (slot 15:30)
- `tiktok_recovery` → `D:\Taadaa\add mail khoi phuc\scheduler.py --live` (slot 19:00)

## Manual start (when tray isn't available)

```powershell
Start-Process 'D:\Taadaa\python-envs\automation\Scripts\python.exe' `
  -ArgumentList '"D:\Taadaa\<consumer>\scheduler.py" --live' -WindowStyle Hidden
```

**MUST clear PYTHONPATH first** (`PYTHONPATH=` empty) — see pitfall below.

Each running scheduler = parent (automation-env python) → child (Py312 python)
pair. Killing the parent with `/T` takes both.

## Pitfall: Hermes PYTHONPATH shadows PIL (tiktok-log-in crash)

Hermes session exports `PYTHONPATH=<hermes-agent>;<hermes-agent>\venv\Lib\site-packages`.
Under it, `import PIL` resolves to the hermes venv and fails with
`ImportError: cannot import name '_imaging' from 'PIL'` → scheduler exits at
startup. Only tiktok-log-in shows this because `login_runner/source_navigation.py`
imports PIL at module load; the other consumers import lazily. Symptom check:

```bash
# from the consumer repo, with Hermes PYTHONPATH set:
timeout 15 /d/Taadaa/python-envs/automation/Scripts/python.exe scheduler.py --live   # crashes
PYTHONPATH= /d/Taadaa/python-envs/automation/Scripts/python.exe -c "import PIL; print(PIL.__file__)"  # should show automation-env site-packages
```

## Proxy watcher — keep it alive separately

`gan_proxy_fleet.py watch --all --workers 80 --mapping D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx
--adb "C:\Program Files (x86)\xiaowei\tools\adb.exe" --runtime D:\CodexRuntime\codex_gmail_debug-gan-proxy --poll-interval 30`

- Owned by `TikTokAllSchedulerTray`; tray's `Ensure-ProxyWatcher` timer (15s) respawns it.
- Watcher spawns a child python (parent = automation-env python, child = Py312).
- User's standing rule: **keep the proxy watcher running even when stopping all
  other automation** — stop only the scheduler task wrappers + consumer trees,
  leave `TikTokAllSchedulerTray` (or the watcher processes) alone.

## git-bash tool quirks

- `taskkill //PID //T //F` → MSYS converts `//PID` → error `Invalid argument/option`.
  Fix: `export MSYS_NO_PATHCONV=1` once, then `taskkill /PID n /T /F`.
- After `/T` tree kill, children report "not found" — that's success (killed with parent).
- `schtasks /query` / `schtasks /run` work from git-bash; `Get-ScheduledTask`/
  `Get-CimInstance` need `powershell.exe -NoProfile -Command`.
