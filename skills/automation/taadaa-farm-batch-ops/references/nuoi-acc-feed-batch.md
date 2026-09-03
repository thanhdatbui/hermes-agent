# Nuoi acc feed batch — exact recipe (tiktok-luot nuoi acc)

Canonical launcher `run_74machines.bat` prompts `set /p ROW_INDEX=` interactively, so from
Hermes invoke the underlying PowerShell directly. Repo root: `D:\Taadaa\tiktok-luot nuoi acc`.

## Launch (live)

```powershell
$env:PYTHONPATH=""
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/run-feed-session.ps1 `
  -Row <N> -Preset full `
  -AccountWorkbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" `
  -SkipAccountWorkbookSync -LocalRun `
  -MachineStartStaggerMs "2000,8000" -RandomizeMachineOrder `
  -Python "D:\Taadaa\python-envs\automation\Scripts\python.exe" -Run
```

Run from the `terminal` tool as `background=true, notify_on_complete=true`.

## Flags (do NOT reinvent — match run_74machines.bat)

| Flag | Why |
|---|---|
| `-Row <N>` | account row 1-6; user must name the row (preflight). |
| `-Preset full -LocalRun` | machines discovered from workbook row; bypasses assignment-manifest/worker gate. Never combine `-LocalRun` with `-Machines`. |
| `-SkipAccountWorkbookSync` | workbook already synced; avoids re-sync from a (possibly moved) tracking workbook. Bare ps1 without it syncs from `TIKTOK_TRACKING_WORKBOOK` and fails on a stale path. |
| `-MachineStartStaggerMs "2000,8000" -RandomizeMachineOrder` | copied verbatim from run_74machines.bat. |
| `-Python "D:\Taadaa\python-envs\automation\Scripts\python.exe"` | EXPLICIT. ps1 default `python` on PATH = hermes venv (Py3.11, wrong). Always pass the automation venv. |
| `-Run` | without it the script only previews (prints machines + command). |

## Mandatory: clear PYTHONPATH

The Hermes terminal exports `PYTHONPATH` into the hermes venv (Python 3.11). The automation
venv is Python 3.12; under the inherited PYTHONPATH, `import PIL` resolves to the hermes
venv's cp311 `_imaging` and fails: `ImportError: cannot import name '_imaging' from 'PIL'`.
The registered Task Scheduler action avoids this (it sets `PYTHONPATH=python_runner`), but a
manual `powershell -File` run inherits the bad value. Always `$env:PYTHONPATH=""` first.
Verify the target env's PIL resolves to itself:
`<automation-env python> -c "import PIL; print(PIL.__file__)"` → must print the automation venv path, not hermes.

## Preflight (preview, no -Run)

Drop `-Run` and run once. Confirm output shows the expected machine list for the row
(e.g. kibe → `Machines: 1,2,...,80`) and `Run mode: local`. If it lists 0 machines, the row
has no accounts / all excluded — stop and ask the user.

## Verify it actually started (first ~30s)

Poll the background output. Success looks like:
```
[HOST] host=kibe machines=1-80 workbook_root=D:\OneDrive\TaadaaData\kibe runtime=D:\Taadaa\runtime\kibe
navigation-only taps enabled
feed swipe enabled
prepare TikTok enabled
```
A traceback `ImportError: cannot import name '_imaging'` = PYTHONPATH not cleared.
`ModuleNotFoundError: No module named 'automation_core.<x>'` = stale automation_core in the
venv → install the pinned P1 wheel from `C:\Users\Kibe\p1-venv-wheels-<date>\`
(see `consumer-scheduler-orchestration` P12).

## Re-enable the schedule (separate from the batch)

If the user also said "bật lại schedule": re-REGISTER the Windows task, don't just enable.
See `consumer-scheduler-orchestration` P11 — `Enable-ScheduledTask` turns a possibly-stale
(bad workbook paths) task back on. Use `scripts/register-scheduler-task.ps1 -DryRun` first,
then re-register, then `Start-ScheduledTask -TaskName TikTokScheduler`.
