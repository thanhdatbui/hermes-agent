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

## Pitfalls

### P1: `--dry-run` phai exit ngay, KHONG vao serve loop

```python
# WRONG — dry-run bi nested ben trong `if now >= planned`, bi block neu slot chua den
if args.once or force_run or now >= planned:
    if args.dry_run:
        ... return 0

# CORRECT — dry-run check TREN CUNG cua loop, truoc bat ky logic nao khac
while True:
    ...
    if args.dry_run:
        append_log(...); print(...); return 0
    if args.once or force_run or now >= planned:
        ...
```

Neu khong fix, `--dry-run` se timeout vi cho slot toi.

### P2: Optional deps (pystray/Pillow) KHONG duoc `sys.exit()` khi import fail

```python
# WRONG — lam bay import cua bat ky module nao dung tray.py
try:
    import pystray
except ImportError:
    print("ERROR: ..."); sys.exit(1)  # <-- giet ca process

# CORRECT — defer check den runtime
try:
    import pystray
    _HAS_TRAY_DEPS = True
except ImportError:
    _HAS_TRAY_DEPS = False

def create_tray_icon(manager):
    if not _HAS_TRAY_DEPS:
        raise RuntimeError("pystray required. pip install pystray Pillow")
```

### P3: Test expectations phai biet state.json co ton tai hay khong

Sau khi chay `--dry-run`, scheduler DA write state.json voi `status: "planned"`. Test ma mong doc `"not_started"` se FAIL.

Fix: test tren 1 scheduler name khong ton tai (e.g. "test_nonexistent_scheduler") hoac xoa runtime root truoc khi test.

### P4: Device lock IMPORT la FAIL-FAST (mandatory), pre-flight la non-fatal cho missing device

Co 2 layer khac nhau — KHONG duoc nhap lan:

**Layer 1: Import — FAIL-FAST (mandatory)**

```python
# WRONG — silent bypass cho phep scheduler chay MA KHONG CO device lock
try:
    from automation_core.device_lock import DeviceLock, ...
except ImportError:
    DeviceLock = None  # <-- NGUY HIEM: scheduler bypass lock → conflict

# CORRECT — raise ngay lap tuc
try:
    from automation_core.device_lock import DeviceLock, DeviceLockUnavailable, device_lock_paths
except ImportError as exc:
    raise ImportError(
        "automation_core.device_lock is required but could not be imported. "
        "Install automation_core or ensure it's on sys.path. "
        "Silent bypass is disabled to prevent device lock conflicts."
    ) from exc
```

**Layer 2: Pre-flight check — non-fatal cho missing device env vars**

```python
def _device_lock_available(cfg):
    # Module imported (fail-fast o tren) — khong check DeviceLock is None nua
    machine = cfg.machine or os.environ.get("CODEX_DEVICE_MACHINE")
    serial  = cfg.serial  or os.environ.get("CODEX_DEVICE_SERIAL")
    if not machine and not serial:
        return True  # Khong co device nao → khong can lock → allow
    ...
```

Pre-flight return True khi khong co machine/serial env vars (khong co device de lock). Module import la mandatory.

### P7: JSONL append can file locking (Windows race condition)

Windows KHONG atomic append cho file mo dong thoi. 2 scheduler process cung ghi vao 1 JSONL → interleaved/corrupted lines.

Fix: exclusive file lock truoc moi write — cross-platform:

```python
def _lock_file(handle):
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

def append_log(path, event, **fields):
    ...
    handle = path.open("a", encoding="utf-8")
    try:
        _lock_file(handle)
        handle.write(line)
        handle.flush()
    finally:
        _unlock_file(handle)
        handle.close()
```

Pitfall: `msvcrt.locking` lock 1 byte (LK_NBLCK, count=1) — du cho append mode. KHONG dung `LK_LOCK` (blocking) vi co the hang neu process khac crash giua lock.

### P5: Lock policy — phan biet "completed normally" vs crash/timeout

```python
# completed/failed → release (day la "normal completion" du exit code != 0)
# timeout/crashed → set_status("handoff") (giu lock de recovery khac takeover)

if status in ("completed", "failed"):
    lease.release()
else:
    lease.set_status("handoff")
```

### P6: Choose_run_at phai nhan du ca date, datetime, va string

```python
def choose_run_at(cfg, day):
    if isinstance(day, datetime): day = day.date()
    elif not isinstance(day, date): day = date.fromisoformat(str(day))
    ...
```

### P8: Killing python children does NOT stop automation — Scheduled Task wrappers respawn

The scheduler processes are not standalone: each task runs a `powershell.exe -Command "& { ... & python <scheduler> }"` wrapper that stays alive and restarts its python child when the child dies. `taskkill` on the python PID alone → child comes back within seconds. To actually stop a scheduler: `schtasks /end /tn <task>` (ends the wrapper) or kill the wrapper PID with `taskkill /PID <wrapper> /T /F` so children die with the tree. Observed reality on this farm: after killing 13 python children, the feed scheduler + proxy watcher respawned on their own because the task wrappers were untouched.

### P9: Hermes PYTHONPATH shadows PIL → tiktok-log-in scheduler crashes on start

**Also hits the nuoi acc feed batch.** `scripts/run-feed-session.ps1 -Row N -Preset full -LocalRun -Run` (`run_tiktok.py` imports PIL via `flows.calibrate_screens` at module load) fails the same way from a manual `powershell -File` run under the inherited Hermes PYTHONPATH: `ImportError: cannot import name '_imaging' from 'PIL'`. The registered Task Scheduler action avoids it (sets `$env:PYTHONPATH='<repo>\python_runner'`), but a manual ps1 invocation inherits it — so ALWAYS launch farm python with `PYTHONPATH=` empty: `$env:PYTHONPATH=""`; `& <ps1> ...`. (The canonical batch command + PYTHONPATH fix is in `taadaa-farm-batch-ops` / `references/nuoi-acc-feed-batch.md`.)

The Hermes session exports `PYTHONPATH=<hermes-agent>;<hermes-agent>\venv\Lib\site-packages`. Starting any consumer scheduler from the Hermes terminal under that PYTHONPATH makes `import PIL` resolve to the hermes venv and fail with `ImportError: cannot import name '_imaging' from 'PIL'` → scheduler exits instantly (only tiktok-log-in shows it, because `login_runner/source_navigation.py` imports PIL at module load; other consumers import it lazily or not at all). Fix: start with `PYTHONPATH=` empty. Verify the target env's PIL is real first: `<automation-env python> -c "import PIL; print(PIL.__file__)"`.

### P10: taskkill in git-bash — MSYS path conversion eats the flags

`taskkill //PID 123 //T //F` fails with `Invalid argument/option - '//PID'`; `tasklist` also silent-fails in git-bash. Fix — export once, then use single-slash flags, and inventory via wmic:

```bash
export MSYS_NO_PATHCONV=1
taskkill /PID 123 /T /F          # /T kills the tree — children "not found" after = already killed with parent
wmic process where "name like '%python%'" get ProcessId,CommandLine   # reliable python inventory
```

### P11: "Bật lại schedule" = RE-REGISTER the task, NOT just Enable-ScheduledTask

When the feed scheduler shows `Disabled` and the user says "bật lại schedule", naively
`Enable-ScheduledTask -TaskName TikTokScheduler` re-enables it — but the task **ACTION
bakes absolute env vars at registration time** (`TIKTOK_TRACKING_WORKBOOK`,
`TIKTOK_ACCOUNT_WORKBOOK`, plus `TIKTOK_FEED_WRITER_ID`, `TIKTOK_SAFE_EXPECTED_WRITER_ID`,
`TIKTOK_FEED_WORKER_ID`, `TIKTOK_FEED_ASSIGNMENT_MANIFEST`). After a path migration
(e.g. `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` →
`D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` — see HANDOFF 2026-08-12),
the registered task keeps the OLD paths and the `python -m scheduler --live` worker silently
fails to find the tracking workbook. `Enable-ScheduledTask` just turns that broken task back on.

Correct sequence (from repo root `D:\Taadaa\tiktok-luot nuoi acc`):
1. `powershell -File scripts/register-scheduler-task.ps1 -DryRun` — validates the
   writer-id gate (`TIKTOK_SAFE_EXPECTED_WRITER_ID` == writer) + existence of every baked
   path (tracking/account workbook, assignment manifest, adb, proxy mapping, all-tray
   script). Prints task definitions, makes NO change. Stop if it errors.
2. Re-run WITHOUT `-DryRun` to re-register — the script reads CURRENT env vars, so it
   bakes the corrected paths automatically. It also re-creates `TikTokSchedulerWake`,
   `TikTokSchedulerTray`, `TikTokAllSchedulerTray`; `TikTokScheduleRecovery`/`Health` stay
   Disabled by default (Recovery only enables with `-EnableRecoveryTask`/`-EnableAutonomousRecovery`).
3. `Start-ScheduledTask -TaskName TikTokScheduler` to go live now.

Verify after: `(Get-ScheduledTask -TaskName TikTokScheduler).Actions[0].Arguments` shows the
NEW workbook paths; `STATE=Ready`; after Start, `STATE=Running`, `LastTaskResult=267009`.

### P12: automation_core version drift → missing submodule (e.g. `automation_core.escalation`)

Symptom: `import run_tiktok` / `python -m scheduler` fails with
`ModuleNotFoundError: No module named 'automation_core.<x>'`. The venv's installed
`automation-core` is OLDER than what the repo code requires (the submodule was added later).

Diagnose:
```
<venv>/Scripts/python.exe -c "import importlib.metadata as m; print(m.version('automation-core'))"
```
vs the pinned version in `<repo>/requirements-automation-core.txt`
(e.g. `automation-core @ file:///C:/Users/Kibe/p1-venv-wheels-<date>/automation_core-<ver>-py3-none-any.whl`).
Install the pinned P1 wheel into the venv:
```
<venv>/Scripts/python.exe -m pip install --force-reinstall --no-deps <wheel-path>
```
Use `--no-deps` to avoid touching Pillow/other deps. The wheel lives in
`C:\Users\Kibe\p1-venv-wheels-<date>\`. pip may warn
"Not uninstalling automation-core at ...hermes venv..., outside environment" — that is the
venv's install record pointing at the hermes venv; the force-install still writes into the
target venv. Don't be alarmed. This is SEPARATE from the PYTHONPATH shadow (P9): even with
PYTHONPATH cleared, a stale automation_core still blocks import.

### P13: `skipped-device-locked` is almost always STALE locks, not a live competitor — verify the worker before blaming a scheduler

When a `multi-machine-feed-session` (or any run) reports `skipped-device-locked` on many machines, the reflex "something else is running and holding the lock" is usually WRONG. On this farm it is **stale device locks from dead prior runs** (tiktok-upload / tiktok-follow / tiktok-luot nuoi acc / reg) whose owner processes exited without releasing.

**Verify, don't assume:**
- Lock store: `C:\Users\Kibe\.codex\device-locks\` — one JSON per machine/serial; fields `machine`, `serial`, `pid`, `host`, `project`, `status` (`queued`/`running`/`recovery`/`handoff`/`blocked`/`temporarily_skipped`/`failed_locked`), `owner_active`, `started_at`.
- Liveness: for each lock, `os.kill(pid, 0)` (Windows) — `OSError` ⇒ dead. In practice ALL of them are dead (`pid_alive=False`) even when `owner_active=True` (that flag is stale).
- **Do NOT conclude a Running Task Scheduler task holds the locks without grepping the actual worker.** `Get-ScheduledTask` shows `State=Running` / `LastTaskResult=267009` even when NO `python -m scheduler` (or target `python ... run_tiktok.py`) process exists — the task wrapper is alive but the worker died or never spawned (empty `scheduler-task.log`). Confirm with `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*scheduler*' -or $_.CommandLine -like '*run_tiktok*' }`. A "Running" schedule that isn't feeding cannot hold device locks. (This is exactly why re-enabling `TikTokScheduler` + running a manual batch concurrently does NOT make the scheduler "hold" the batch's locks — the manual batch is skipped by the stale ones.)

**Fix (sanctioned, audited — do NOT `rm` lock JSON):**
- `run_tiktok.py` supports `--full-scope-takeover` (valid ONLY for `multi-machine-feed-session`; reason string = `"user-requested full-machine run"`). It reclaims stale leases via `acquire_device_lock(allow_takeover=True, takeover_scope=FULL_SCOPE_TAKEOVER)` in `automation_core.device_lock` — the audited path — instead of deleting lock files.
- The canonical `run-feed-session.ps1` does NOT forward this flag. Call `run_tiktok.py` directly with the same args the ps1 builds (P9 PYTHONPATH-clear launch) plus `--full-scope-takeover`. Concrete recipe + lock scanner: `references/device-lock-stale-takeover.md`.
- Because every owner pid is dead, takeover is safe (no live process to clash). Use whenever the user wants a full-machine pass and prior runs left locks behind.
- For `FAILED_LOCKED` (retained) locks — distinct from stale `handoff`/`running`/`blocked` — use the CLI `python -m automation_core lock open --confirm --reason ... --scope FULL_SCOPE_TAKEOVER` (see `automation-core-development`). Never mass-release those automatically.

### P14: "Bật lại schedule" then run a batch — NEVER run both simultaneously; the manual batch IS the authority

User asks "bật lại schedule + chạy luôn row N" — do the re-register (P11), then decide: either the schedule is live-feeding (leave it, do NOT also run a manual batch — the manual run will collide/queue) or it is NOT actually feeding (verify via P13 worker grep; then run the manual batch with `--full-scope-takeover`). Running a manual `run-feed-session.ps1 -Run` immediately after `Start-ScheduledTask` means two feeders fighting the same lock store; the result is mass `skipped-device-locked` and an unusable report. If the schedule is healthy and feeding, `Start-ScheduledTask` alone satisfies "chạy luôn" — do not stack a second batch on top.

### P15: `powershell -Command` from git-bash — `$` and quotes get mangled; use a `.ps1` file

Inline `powershell -Command '... $env:PYTHONPATH="" ...'` from git-bash (MSYS) mangles `$env:` (bash expands it) and nested quotes — the powershell child receives a syntactically broken line (e.g. `File "<string>", line 1 ... SyntaxError: unterminated string literal`). Launch farm scripts via `powershell -File <script>.ps1` (write the ps1 with `write_file`), NOT `-Command`. Inside the ps1 set `$env:PYTHONPATH = ""` first (P9). For one-liners, wrap the whole powershell invocation in SINGLE quotes and keep `$` OUT of the double-quoted inner string; prefer the file approach.

### P16: Xóa/tái tạo đè manifest giữa ca gây lỗi `cohort artifact assignment digest mismatch` (Case 58)

Khi phiên feed (`multi-machine-feed-session`) đang chạy, runner đã nạp và khoá chữ ký `--cohort-artifact` (`manifest_digest = sha256(manifest_cu)`).
Nếu script đồng bộ (như `hermes_taikhoan_sync_cron.py`) chạy giữa chừng, thực hiện `shutil.rmtree` dọn thư mục `manifests/<day>` và gọi `tiktok_picker.py` tái tạo manifest mới (`assignment-v1-<hash_moi>.json`), các tiến trình con khi đối soát manifest trên đĩa sẽ phát hiện digest SHA-256 bị lệch, ném ngoại lệ `ValueError: cohort artifact assignment digest mismatch` và kích hoạt dừng phiên giữ hiện trường toàn bộ máy.
**Quy tắc:** Tuyệt đối KHÔNG xoá hoặc tái tạo đè manifest/cohort trong ngày khi đang có tiến trình feed active. Chi tiết phân tích & phòng ngừa: [`references/cohort-manifest-midrun-regeneration-pitfall.md`](references/cohort-manifest-midrun-regeneration-pitfall.md).

## Operations: stop/start the whole scheduler fleet

The 5+ schedulers are owned by Windows Scheduled Tasks plus the unified tray — not standalone processes. Full inventory + exact task actions (env vars, python paths) live in `references/scheduler-fleet-operations.md`. Cheat sheet:

| Task | Spawns | Restart |
|---|---|---|
| `TikTokScheduler` | feed `-m scheduler --live --poll-seconds 30` (tiktok-luot nuoi acc) | `schtasks /run /tn TikTokScheduler` |
| `TikTokScheduleRecovery` | `scheduler.recovery_runtime --watch --dispatch --enable-live-recovery` | `schtasks /run /tn TikTokScheduleRecovery` |
| `GmailRegistrationScheduler` | `gmail_scheduler.py --live --poll-seconds 30` (Py312) | `schtasks /run /tn GmailRegistrationScheduler` |
| `TikTokAllSchedulerTray` | tray ps1 → proxy watcher + 4 consumer schedulers at logon | `schtasks /run /tn TikTokAllSchedulerTray` |

The 4 consumer schedulers (Tiktok_Reg, tiktok-log-in, tiktok-add-bao-mat-f2a, add mail khoi phuc) have NO own task — they are children of `TikTokAllSchedulerTray`'s `Start-AllSchedulers` (`tiktok-scheduler-tray.ps1:324`). Manual start, one per consumer, MUST be `PYTHONPATH=` empty (P9):

```powershell
Start-Process 'D:\Taadaa\python-envs\automation\Scripts\python.exe' `
  -ArgumentList '"D:\Taadaa\<consumer>\scheduler.py" --live' -WindowStyle Hidden
```

Each scheduler appears as a parent (automation-env python) → child (Py312) pair; kill with `/T` or target both.

To stop everything except the proxy watcher (user's recurring ask): end/kill only the scheduler task wrappers + their python trees (`schtasks /end /tn TikTokScheduler`, `/tn GmailRegistrationScheduler`, `/tn TikTokScheduleRecovery`; kill the 4 consumer python trees). Leave `TikTokAllSchedulerTray` running — it owns the `gan_proxy_fleet.py watch --all` watcher (also respawned by its 15s `Ensure-ProxyWatcher` timer, `tiktok-scheduler-tray.ps1:382-385`).

## Consumer startup contracts: core readiness before app logic

For any consumer state machine that controls TikTok or another device app, make the app-neutral core readiness call the hard boundary before app-specific logic. The intended sequence is `ACQUIRE_LOCKS -> CONNECT_DEVICE/PREPARE_DEVICE -> OPEN_APP -> DISMISS_POPUPS -> ACCOUNT_SWITCHER -> DISMISS_POPUPS -> ACCOUNT_READY`. `prepare_device` should own wake, credential-free swipe, rotation lock, and readiness verification; the consumer must pass explicit safe options and must not duplicate the call in later TikTok handlers. Treat `locked_or_secure` and failed rotation verification as terminal readiness failures routed to manual review before app launch. Add tests for exact transition order, prepare call count/options including configured rotation, and both readiness failure gates. If retries reset the state machine, reset preparation and adapter/ADB state together so a stale idempotence flag cannot skip setup.

## Consumer workflow failure gates and lock cleanup

For consumer workflows that drive devices or accounts, readiness is a hard gate, not a warning. If preparation reports `locked_or_secure`, or UI dump/profile confirmation is unavailable, stop before app launch/account switching, record a stable error code plus last state in checkpoint/report, and avoid retrying the same job blindly. Never let a broad exception handler convert account-switcher failure into success. Keep `FAILED` and `MANUAL_REVIEW` distinct.

Lock cleanup must be idempotent and independent of reaching the nominal `RELEASE` state: release every acquired lease on failure paths, clear the local lease reference after release, and never delete a live lock merely because a run failed. Consumer-specific policy belongs in the consumer repo; do not patch automation-core/sibling repos for a consumer orchestration defect.

## Fresh-verification protocol when Hermes evidence is stale

This fallback applies to any consumer-repository code change, not only scheduler work; use it for UI selector/popup regressions and other narrow seams when Hermes marks the workspace unverified.

If the workspace verifier reports `unverified` or stale evidence after edits, do not rely only on an earlier pytest result. Create a focused temporary verifier under Windows `%TEMP%` with `tempfile.NamedTemporaryFile(delete=False, prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir())`. Exercise the changed behavior with real temporary fixtures, explicitly label the result **ad-hoc verification** (not suite green), and delete the script afterward when possible. For dry-run/runtime-mode fixes, assert both dependency flag propagation and the observable side effect in each mode. If pytest passes but cannot write `.pytest_cache`, report that as an environmental warning, not a functional failure. If a broader test-file run hangs at a pre-existing test whose fixture leaves a live dependency unmocked (for example, a real ADB/battery helper), record the exact test and stop; do not rerun blindly, call it suite-green, or broaden into live-device verification. Use the focused mock-based probe as **ad-hoc verification** and report the suite blocker separately.

A verifier stored in `%TEMP%` does not inherit the repository's import directory, even when its subprocess uses the repository as `cwd`. Bootstrap the code under test explicitly before importing repo-local helpers (for example, set child-process `PYTHONPATH` to the repo root or inject it into `sys.path`); do not assume `_path_setup` can be imported from the temp script's directory. Use a `try/finally` cleanup path. If the first run fails solely because of import resolution, clean up and retry with the explicit path fix, then report the successful retry as ad-hoc verification; treat any unresolved bootstrap failure as an unverified blocker, never as suite-green evidence.

### Workbook numeric path values

Excel/openpyxl may return an identifier-like folder cell as `float` (`489.0`). Preserve the raw value at the caller boundary and let the shared resolver canonicalize it (`489.0` → `"489"`) before path construction. Do not stringify first (`str(489.0)` → `"489.0"`), which creates a false missing-folder failure. Regression coverage should use a real temporary workbook containing `489.0` and exercise the CLI/preflight seam with fake ADB/lock dependencies; never require a live device or upload.

## Verification pattern (ad-hoc)

Tao script `C:\Users\<user>\AppData\Local\Temp\hermes-verify-<topic>.py`:
1. Test constants (slot times, reserved blocks)
2. Test time math (03:00 → next=08:00; 12:30 → next=14:00; 23:00 → unavailable)
3. Test state round-trip voi tempfile (khong de lai .tmp)
4. Test `--dry-run` subprocess cho TUNG consumer (timeout 15s)
5. Test tray imports KHONG sys.exit
6. Test `create_tray_icon()` raises RuntimeError khi deps missing
7. Clean runtime root (`~/.codex/tiktok-schedulers`) truoc va sau

```bash
python "C:/Users/<user>/AppData/Local/Temp/hermes-verify-schedulers.py"
rm -rf ~/.codex/tiktok-schedulers  # clean state artifacts from --dry-run
rm C:/Users/<user>/AppData/Local/Temp/hermes-verify-schedulers.py
```

## CLI usage

```bash
# Test slot assignment
python scheduler.py --dry-run
# Output: [DRY-RUN] tiktok_reg: planned at 2026-07-26T09:30:00+07:00

# Run for real (requires --live safety gate)
python scheduler.py --live

# Run once and exit
python scheduler.py --live --once

# Force run bypassing clock window
python scheduler.py --live --run-now

# Tray (requires pystray + Pillow)
python automation_core/scheduler/tray.py
```

## Hermes cron migration: planner / runner / watcher harness

Use this extension when migrating a farm from long-lived Windows schedulers or Task Scheduler wrappers to Hermes cron orchestration while keeping existing consumers unchanged.

### Read-only audit first

Before proposing implementation, inspect the repo rules and every user-mandated source path with read-only tools. Build the plan from observed contracts, not filenames or assumptions. Do not open credential-bearing workbooks; inspect only workbook readers, schema/header code, JSON/JSONL structure, launchers, recovery scripts, and docs. If a required source cannot be read, put a verdict such as `PLAN_NEEDS_MORE_INFO` first and name the exact missing contract.

If the user explicitly requests final-only Markdown and no file writes, do not save `.hermes/plans/`; the skill's normal plan-file behavior is subordinate to that explicit constraint.

### Separate scheduling assignment from execution evidence

Do not reuse a render CSV or a legacy resource-ownership manifest as the complete orchestration state. Treat them as separate layers:

- **Assignment manifest:** immutable daily intent: day, timezone, resources, machine/serial/account mapping, slot, action type, seed, idempotency key, and constraints.
- **Execution ledger/reports:** append-only observations: attempt, start/end, exit code, lock result, artifact/report paths, verifier proof, recovery state, and final status.

If legacy manifests only expose `resources` such as `machine:<N>`, preserve that compatibility surface and namespace new orchestration fields rather than silently changing the old loader contract. Explicitly record conflicts between feed and upload manifests and choose one canonical schema plus compatibility projection.

### Three-process contract

For a daily farm schedule, keep the boundaries narrow:

1. **Picker:** pure Python/no LLM; read workbook and ledgers; filter invalid, logged-out, unmapped, already-completed, and no-content accounts; solve per-machine constraints; write the day manifest atomically.
2. **Runner:** cron every 15–30 minutes; claim due entries idempotently; call existing launcher adapters; do not duplicate feed and post when the contract requires `feed_then_post`; treat lock ownership and verified evidence as separate from process exit code.
3. **Watcher:** cron every 15 minutes; parse reports/ledger; classify failure; invoke existing recovery runtime; suppress Telegram after attempt one and alert only after the contractual final attempt or a real blocker.

The runner must be non-interactive. Audit every existing PowerShell wrapper for `Read-Host` confirmations and require an explicit non-interactive adapter/flag in the implementation phase; a cron process must never hang waiting for `RUN`/`YES`.

### Constraint solver pattern for account-per-machine schedules

For account cadence plus machine-cluster constraints, make picker functions deterministic and testable:

- Derive a recorded seed from day and stable source revision; never use global random state.
- Filter candidates before scheduling and emit per-account reason codes for skips.
- Generate slots from the **authoritative contract for this migration**. Reuse shared `WORK_START`/`WORK_END` only when they are explicitly the approved contract; do not silently inherit legacy core hours when a new logical-day window differs. It is valid for a bounded P1 to reuse only shared `RESERVED_BLOCKS` while owning its separately specified timezone-aware window helper and testing rollover boundaries.
- Enforce max entries per machine and minimum start-to-start gap as hard constraints.
- Use bounded backtracking or deterministic swap when greedy placement fails; never relax a hard constraint silently.
- Make combined actions one entry (`feed_then_post`) with post metadata nested under the same entry; never create an independent `post_only` entry unless explicitly designed and approved.
- Validate the finished manifest before atomic replace and make a same-day rerun reuse a valid manifest instead of rerolling.

### Idempotency and crash recovery

Use a process lock per picker/runner/watcher, distinct from device locks. Write JSON manifests via temp file + flush + `os.replace`; preserve a valid prior manifest if generation crashes. Define states such as `planned`, `running`, `success`, `failed`, `recovery`, `blocked`, and `missed`, and specify which states are runnable. A stale `running` entry is evidence for watcher review, not permission for blind replay.

For retry logic, distinguish:

- normal non-zero completion with a report;
- crash/timeout with incomplete ownership evidence;
- device-lock conflict;
- verified business failure;
- true blocker such as missing mapping, logout, missing video, or corrupted manifest.

The scheduler must not use exit code alone as success proof. Require report/verifier/artifact evidence, and preserve the existing device-lock rule: no implicit stale-file deletion or unapproved takeover. If a consumer owns target-level locks, the harness should normally preflight and delegate ownership rather than claim a second outer lease; if an outer lease is required, define a shared run ID and promotion/release contract first.

### Timezone and window contract

Make cron timezone explicit in the manifest and scheduler config. Convert all comparisons to timezone-aware timestamps. Test the exact boundaries of working hours and reserved blocks, plus session duration fitting before the end of a valid window. Define the grace period for late runner invocations and the policy for entries that miss it.

### Phase-boundary TDD when production code is already fixed

If the requested phase change is already present in `HEAD`, do not manufacture a no-op production diff just to match the plan. Inspect `git show HEAD:<path>` and `git blame` first. Add the missing behavior tests; if strict RED evidence is required, temporarily invert only the relevant guard locally, run the focused tests to observe the expected failure, then restore the correct implementation before GREEN. Commit only genuinely missing files, and state explicitly when production behavior was pre-existing.


### Required verification matrix

At minimum, plan pure-function tests for header normalization, source mapping priority/conflicts, cadence/jitter, due-state extraction, slot generation, reserved boundaries, machine capacity, minimum gaps, deterministic seeds, backtracking, action-type validation, and manifest idempotency. Add adapter tests with fake launchers for non-interactive argument propagation, lock conflict, timeout, missing verifier evidence, feed failure preventing post, and successful feed triggering the nested post. Add watcher tests for attempt-one recovery suppression, attempt-two escalation, blocker-immediate alert, stale lease identity, and redacted Telegram payloads.

### Migration boundary

Keep P1/Core Harness limited to new scripts, schema, adapters, and tests. Do not patch consumer scripts or shared automation-core merely to make the migration convenient. Defer consumer contract changes, workbook normalization, recovery runtime changes, and farm-wide rollout/dual-run/rollback to explicitly named later phases. Include exact paths, observed entrypoint parameters, owner of each lock, and a canary/rollback gate in the worker-ready plan.

### P1 audit gates: preview, proof, and deterministic cadence

Before approving a worker-ready harness spec, explicitly close these three gaps:

1. **Preview isolation:** a default dry-run/preview must not write a launch reservation, consume an idempotency key, increment an attempt, or create a terminal result. If logged, use a non-terminal preview event only. Test preview followed by execute and prove the real launcher is still invoked exactly once.
2. **Invocation-bound verifier:** reserve a generated `invocation_id` before a real launch and use a dedicated artifact root. Define the exact files and predicates proving fresh success for the scheduled machine/serial/account row; exit code alone never proves it. An unresolved reservation is handoff/unknown, not permission to relaunch.
3. **Closed cadence table:** specify every input state for feed and post (same-day, one-day, two-day, overdue, never-success, missing/malformed/future date), the exact `due` values/action type, priority, and fail-closed behavior. Byte-stable manifests cannot contain wall-clock-derived IDs/timestamps or unordered/random serialization.

Use `references/p1-harness-audit-gates.md` for a ready-to-apply checklist and regression matrix.

### Cron job creation mechanics (verified 2026-08-10)

Các gotcha khi tạo job trên Hermes cron tool — đã dính và fix trực tiếp:

- **Script path PHẢI tương đối với `~/.hermes/scripts/`** — path tuyệt đối bị từ chối: `Script path must be relative to ~/.hermes/scripts/. Got absolute or home-relative path`. Pattern chuẩn: repo giữ logic (commit được), `~/.hermes/scripts/<launcher>.py` chỉ là cầu nối subprocess gọi repo script bằng python env đúng (thường `D:\Taadaa\python-envs\automation\Scripts\python.exe` — không dùng python mặc định của Hermes, repo script import `automation_core`).
- **Schedule gotcha:** `1m` → job tạo ra là `once in 1m` (one-shot, KHÔNG lặp). `every 1m` cũng vẫn hiển thị `repeat: once`. Để lặp vô hạn phải dùng cron expression `*/1 * * * *` **VÀ** truyền `repeat=0` — thiếu `repeat=0` thì vẫn `once` dù schedule là cron expr. Luôn kiểm tra response trả về: phải thấy `"repeat": "forever"`.
- **`no_agent=true` = watchdog im lặng:** script chạy mỗi tick, **stdout rỗng → không gửi gì**, stdout non-empty → gửi verbatim về origin chat. Dùng cho sync/check định kỳ: chỉ in khi CÓ thay đổi/lỗi, im lặng khi không có gì (không spam Telegram). Exit code != 0 kèm stdout = alert lỗi.
- **State file để tránh chạy lại khi không đổi:** wrapper stat source (size + mtime_ns) lưu JSON state; source không đổi → stdout rỗng → silent; đổi → chạy sync + in kết quả + cập nhật state. Lỗi thì KHÔNG cập nhật state (retry lần sau).
- **Verify sau tạo:** `cronjob action=run` để chạy ngay, check `last_status: ok` + `execution_success: true`. Lần chạy đầu sẽ sync (state chưa có), lần 2 im lặng — đó là hành vi đúng.

Ví dụ đầy đủ (watchdog sync workbook, code launcher + wrapper + params cron): `references/hermes-cron-watchdog-sync-example.md`.

## Reference implementations

- Base scheduler: `D:\\Taadaa\\automation-core\\src\\automation_core\\scheduler\\base.py`
- Time windows: `D:\Taadaa\automation-core\src\automation_core\scheduler\time_windows.py`
- Tray: `D:\Taadaa\automation-core\src\automation_core\scheduler\tray.py`
- Example consumer: `D:\\Taadaa\\Tiktok_Reg\\scheduler.py`
- Lock policy source: `D:\\\\Taadaa\\\\automation-core\\\\src\\\\automation_core\\\\device_lock.py`
- Stale device-lock diagnosis + `--full-scope-takeover` re-run recipe + lock scanner (verified 2026-08-13): `references/device-lock-stale-takeover.md`
- Hermes cron migration thực tế (user-chốt constraints, workbook source-of-truth, mapping priority, gotchas verified 2026-08-10): `references/hermes-cron-orchestration-migration.md`
