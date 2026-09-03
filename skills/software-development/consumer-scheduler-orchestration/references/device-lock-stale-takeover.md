# Stale device-lock → `--full-scope-takeover` (feed batches, verified 2026-08-13)

Context: `run-feed-session.ps1 -Row N -Preset full -LocalRun -Run` finished with
`multi-machine-feed-session completed with failed machine(s)` and almost every machine
`skipped-device-locked` (64/72 in the observed run) — NOT because a scheduler was running,
but because **stale locks from dead prior runs** (projects `tiktok-upload`, `tiktok-follow`,
`tiktok-luot nuoi acc`, reg) blocked acquisition. All owner PIDs were dead
(`pid_alive=False`) even when `owner_active=True`.

## 1. Diagnose: who holds the locks (run with the automation-env python)

Lock store: `C:\Users\Kibe\.codex\device-locks\` — top-level `.json` / `.tmp` files only;
skip `backup_*` directories. Per-machine JSON has: `machine`, `serial`, `pid`, `host`,
`project`, `command`, `status`, `owner_active`, `started_at`, `lock_id`, `run_id`.

```python
# _scan_locks.py — print locks for machines 1-80 with pid liveness
import json, os
from pathlib import Path
root = Path.home() / ".codex" / "device-locks"
machines = set(range(1, 81))
def pid_alive(pid):
    if not pid: return None
    try:
        os.kill(pid, 0); return True
    except OSError: return False
    except Exception: return None
for p in sorted(root.iterdir()):
    if not p.is_file() or not (p.suffix == ".json" or p.name.endswith(".tmp")):
        continue
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    m = d.get("machine")
    if m is None or int(m) not in machines:
        continue
    print(f"m{int(m):>2} {d.get('status'):<22} owner_active={d.get('owner_active')} "
          f"pid={d.get('pid')} pid_alive={pid_alive(d.get('pid'))} "
          f"proj={d.get('project')} start={d.get('started_at')} serial={d.get('serial')}")
```

Key reads: `status` values — `queued`/`running`/`recovery` are active; `handoff`/`blocked`/
`temporarily_skipped`/`failed_locked` are retained. **`owner_active` can be stale — trust
`os.kill(pid,0)`.**

## 2. Verify a "Running" schedule is NOT the culprit before blaming it

`Get-ScheduledTask` reports `State=Running`, `LastTaskResult=267009` even when no worker
process exists (task wrapper alive, worker died / never spawned; `scheduler-task.log`
stays 0 bytes). Grep real processes:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*scheduler*' -or $_.CommandLine -like '*run_tiktok*' } | Select-Object ProcessId,CommandLine | Format-List
```

Empty ⇒ the "Running" schedule holds nothing; the skipped locks are stale.

## 3. Fix: re-run with `--full-scope-takeover` (audited reclaim — NEVER `rm` lock JSON)

`run-feed-session.ps1` does NOT forward the flag, so call `run_tiktok.py` directly with the
same args the ps1 builds. Launch via a `.ps1` file (P15 — never `powershell -Command` from
git-bash) and clear PYTHONPATH first (P9):

```powershell
# _run_row2_takeover.ps1
$env:PYTHONPATH = ""
$repo = "D:\Taadaa\tiktok-luot nuoi acc"
$py = "D:\Taadaa\python-envs\automation\Scripts\python.exe"
$args = @(
  (Join-Path $repo "python_runner\run_tiktok.py"),
  "--mode", "multi-machine-feed-session",
  "--machines", ((1..80) -join ","),
  "--account-workbook", "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx",
  "--account-row-index", "2",
  "--max-workers", "40",
  "--config", (Join-Path $repo "python_runner\config.example.yaml"),
  "--artifact-root", (Join-Path $repo ".ai-runs"),
  "--allow-navigation-only", "--allow-feed-swipe", "--allow-benign-popup-dismiss",
  "--prepare-tiktok", "--machine-start-stagger-ms", "2000,8000",
  "--randomize-machine-order", "--full-scope-takeover"
)
Set-Location $repo
& $py @args
exit $LASTEXITCODE
```

Why it is safe: `--full-scope-takeover` is restricted to `multi-machine-feed-session`
(`run_tiktok.py:568-569` errors otherwise) and goes through
`acquire_device_lock(allow_takeover=True, takeover_scope=FULL_SCOPE_TAKEOVER)`,
reason `"user-requested full-machine run"` — the audited reclaim path in
`automation_core/device_lock.py`. With every owner pid dead there is no live process to
clash with.

## 4. FAILED_LOCKED (retained) locks — DIFFERENT path, do not mass-release

`FAILED_LOCKED` is a deliberate retained state (recovery contract). Open individually with
explicit user confirmation:

```bash
python -m automation_core lock open machine:<N> --confirm --reason "<user reason>" --scope FULL_SCOPE_TAKEOVER
```

Never mass-delete or mass-takeover these without per-target user authorization (see
`automation-core-development` for the CLI `lock list/inspect/open` contract).

## Pitfalls recap

- `owner_active=True` ≠ live owner — always `os.kill(pid, 0)`.
- A "Running" Scheduled Task ≠ feeding worker — grep `CommandLine` for `run_tiktok`/`scheduler`.
- `--full-scope-takeover` only valid for `multi-machine-feed-session`.
- Running the manual batch + the schedule simultaneously stacks two feeders on one lock
  store → mass `skipped-device-locked`; pick one authority per pass.
