# Ad-hoc Verification Script Template

Template for verifying scheduler implementations. Saves to `C:\Users\<user>\AppData\Local\Temp\hermes-verify-<topic>.py`.

## Structure

```python
"""Ad-hoc verification for <topic>."""
import sys, os, json, tempfile, importlib.util, subprocess, shutil
from pathlib import Path
from datetime import datetime, time as clock_time, timedelta

AUTOMATION_CORE_SRC = Path(r"D:\Taadaa\automation-core\src")
sys.path.insert(0, str(AUTOMATION_CORE_SRC))

RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if not ok and detail else ""))

# === TESTS ===

# 1. Constants & imports
check("module imports", True)
check("constants correct", ...)

# 2. Time math (critical for schedulers)
early = datetime.now().astimezone().replace(hour=3, minute=0, second=0, microsecond=0)
check("03:00 not available + next=08:00", 
      not is_available(early) and next_available_time(early).time() == clock_time(8, 0))

reserved = datetime.now().astimezone().replace(hour=12, minute=30, second=0, microsecond=0)
check("12:30 reserved + next=14:00", 
      not is_available(reserved) and next_available_time(reserved).time() == clock_time(14, 0))

# 3. State persistence (use tempfile, check no .tmp left behind)
with tempfile.TemporaryDirectory() as td:
    sp = Path(td) / "state.json"
    write_state(sp, {"status": "planned"})
    check("state round-trip", read_state(sp) == {"status": "planned"})
    check("no .tmp leftover", not list(Path(td).glob("*.tmp")))
    
    lp = Path(td) / "log.jsonl"
    append_log(lp, "evt", x=1)
    append_log(lp, "evt2", x=2)
    check("JSONL append", len(lp.read_text().strip().split("\n")) == 2)

# 4. Consumer schedulers via --dry-run subprocess
CONSUMERS = [
    ("tiktok_reg",   Path(r"D:\Taadaa\Tiktok_Reg\scheduler.py"),            "09:30", "_run_all_targets.py"),
    ("tiktok_login", Path(r"D:\Taadaa\tiktok-log-in\scheduler.py"),         "14:00", "sync_taikhoan_run_safe.py"),
    ("tiktok_2fa",   Path(r"D:\Taadaa\tiktok-add-bao-mat-f2a\scheduler.py"),"15:30", "run_batch_live_2fa.py"),
    ("tiktok_recovery", Path(r"D:\Taadaa\add mail khoi phuc\scheduler.py"), "19:00", "run_add_recovery.py"),
]

# CRITICAL: Clean runtime state before testing (dry-run writes state.json)
runtime = Path.home() / ".codex" / "tiktok-schedulers"
if runtime.exists():
    shutil.rmtree(runtime)

for name, path, expected_time, expected_script in CONSUMERS:
    check(f"{name} exists", path.exists())
    try:
        r = subprocess.run([sys.executable, str(path), "--dry-run"],
                           capture_output=True, text=True, timeout=15,
                           cwd=str(path.parent))
        ok = r.returncode == 0 and expected_time in r.stdout and expected_script in r.stdout
        check(f"{name} --dry-run (time={expected_time}, script={expected_script})", ok,
              f"rc={r.returncode} stdout={r.stdout[:200]} stderr={r.stderr[:200]}")
    except subprocess.TimeoutExpired:
        check(f"{name} --dry-run", False, "timed out")

# 5. Optional deps (tray module)
from automation_core.scheduler.tray import SchedulerManager, SCHEDULERS, _HAS_TRAY_DEPS
check("tray imports (no sys.exit)", True)
check("tray SCHEDULERS has 4", len(SCHEDULERS) == 4)

mgr = SchedulerManager()
check("SchedulerManager()", True)

# Test read_state for non-existent scheduler (not one that has state.json from dry-run!)
test_state = mgr.read_state("test_nonexistent_scheduler")
check("read_state for non-existent = not_started", test_state.get("status") == "not_started")

# After dry-run, state files exist with "planned" status
state_after_dryrun = mgr.read_state("tiktok_reg")
check("read_state after dry-run has planned status", state_after_dryrun.get("status") == "planned")

# Test create_tray_icon raises RuntimeError (not ImportError/sys.exit) when deps missing
try:
    from automation_core.scheduler.tray import create_tray_icon
    create_tray_icon(mgr)
    check("tray icon raises when deps missing", False, "unexpectedly succeeded")
except RuntimeError:
    check("tray icon raises RuntimeError without pystray", True)
except Exception as e:
    check("tray icon raises RuntimeError without pystray", False, 
          f"wrong exception: {type(e).__name__}: {e}")

# === SUMMARY ===
print("\n" + "=" * 60)
n_pass = sum(1 for _, ok in RESULTS if ok)
n_fail = sum(1 for _, ok in RESULTS if not ok)
print(f"Results: {n_pass} passed, {n_fail} failed, {len(RESULTS)} total")
for name, ok in RESULTS:
    if not ok:
        print(f"  FAIL: {name}")
sys.exit(0 if n_fail == 0 else 1)
```

## Post-run cleanup

```bash
# Clean runtime artifacts (dry-run writes state.json)
rm -rf ~/.codex/tiktok-schedulers

# Remove verification script
rm C:/Users/<user>/AppData/Local/Temp/hermes-verify-schedulers.py
```

## Key patterns

### 1. State-aware test expectations

After running `--dry-run`, schedulers write `state.json` with `status: "planned"`. Tests expecting `"not_started"` will FAIL unless:
- Test a non-existent scheduler name (e.g. "test_nonexistent_scheduler"), OR
- Clean runtime root before testing

### 2. Subprocess timeout for --dry-run

Use `timeout=15` seconds. If scheduler enters serve loop (bug in P1), it will timeout and report failure.

### 3. Check both stdout and return code

```python
ok = r.returncode == 0 and expected_time in r.stdout and expected_script in r.stdout
```

Catches both crashes (non-zero rc) and wrong behavior (missing expected output).

### 4. Optional deps test pattern

For modules with optional imports (pystray/Pillow):
- Test module imports without error
- Test `create_tray_icon()` raises `RuntimeError` (not `ImportError` or `sys.exit`)
- Verify `_HAS_TRAY_DEPS` flag is set correctly

## Focused seam probes when the suite is blocked

When a canonical test file hangs at an unrelated/pre-existing test or reaches a live dependency because its fixture leaves a helper unmocked, stop the broad run and preserve the exact test name as the blocker. Do not call that run green and do not rerun blindly. Verify the changed seam independently instead:

1. Create a temporary child script with `tempfile.NamedTemporaryFile(delete=False, prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir())`.
2. Bootstrap the repository import path explicitly (`sys.path.insert(0, str(repo / "scripts"))` or set child `PYTHONPATH`); a Temp script does not inherit repo-local import semantics from `cwd`.
3. Exercise the real function with a narrow mock and assert the exact propagated kwarg/side effect. For a watcher call-site change, mock `fleet.watch_device_reconnect`, set the outer stop event in the fake, and assert `captured["auto_enable_wifi"] is True` plus one call.
4. Avoid ADB, live devices, secrets, workbooks, and broad runtime startup in the probe.
5. Run the script, print a machine-readable success marker, and delete it in `finally`.
6. Report the result as **ad-hoc verification**, separately from the canonical-suite blocker.

## Common mistakes to avoid

1. **Testing state after dry-run without cleaning** — state.json exists from prior run
2. **Using `sys.exit(1)` on optional import failure** — kills entire process
3. **Nesting `--dry-run` check inside time-window logic** — causes timeout
4. **Expecting "not_started" for scheduler that just ran --dry-run** — it's "planned"
5. **Not cleaning runtime root before test** — stale state causes false failures
6. **Calling a blocked suite green** — a focused pass is not a substitute label for a timed-out canonical run
7. **Letting a focused watcher probe idle forever** — set the same stop event that `watch_one` observes so the mock returns deterministically
