# Bidirectional Device Lock Coordination & Clean Skip Architecture

Audit findings and architectural contract for coordinating operator ad-hoc scripts with batch runners (e.g. `tiktok-luot nuoi acc`).

## 1. Context & Two-Way Coordination Requirement
A robust phone farm requires bidirectional concurrency safety between scheduled batch sessions (ca nuôi / multi-machine feed) and out-of-band operator scripts (upgrades, account checks, canary, maintenance):
1. **Operator Script Runs First (Lock Held) → Batch Arrives:**
   The batch must cleanly skip the locked machine without aborting or marking the entire multi-machine batch as `MANUAL_NEEDED` (exit code 2). The batch completes successfully with remaining available machines (`partial-skip` / `SUCCESS`).
2. **Batch Runs First (Machine Busy) → Operator Script Arrives:**
   The operator script must not fail-fast or blindly clobber ADB. It must queue/wait (`wait_for_device_lock` / `operator_device_lock`) until the batch releases the device lock, then acquire exclusivity and proceed safely.

## 2. Identified Anti-Patterns & Root Causes

### Anti-Pattern A: Single-Mode No-Op Lease (`user_authorized=False`)
- **Symptom:** In `run_tiktok.py:886`, single-machine runs pass `user_authorized=False`.
- **Root Cause:** In `automation_core.device_lock:459-474`, `user_authorized=False` returns `_UnlockedDeviceLockLease` when no prior lock exists. This lease does not create any file on disk. External scripts inspecting `~/.codex/device-locks/machine_<ID>.lock.json` assume the machine is idle, causing ADB collision.
- **Rule:** Session flows touching physical devices must use `user_authorized=True` with `release_on_terminal=True` to ensure visible on-disk reservation without leaving orphaned retained locks on crash.

### Anti-Pattern B: Preflight Warning without Machine Filtering
- **Symptom:** `run-feed-session.ps1:292` joins `$machineList` before checking locks. When a living PID holds a lock, it only prints a warning after 600s and still passes the locked machine to Python runner.
- **Rule:** Preflight MUST filter out actively locked machines from `$machineList` prior to dispatch, or let Python handle reservation without failing the overall batch.

### Anti-Pattern C: Batch Aggregation Lock Escalate (`skipped-device-locked` → `MANUAL_NEEDED`)
- **Symptom:** `multi_machine_feed_session.py:5176` collapses both `skipped-device-locked` and `needs-user-decision` into `ExitStatus.MANUAL_NEEDED`. Even if 49/50 machines succeed, 1 skipped machine triggers a red batch status.
- **Rule:** Differentiate `skipped-device-locked` (clean skip due to active automation/operator lock) from `needs-user-decision` (retained failed lock). As long as at least one eligible machine ran, clean skip returns `ExitStatus.SUCCESS` with `final_status="partial-skip"`.

### Anti-Pattern D: Fail-Fast Lock Acquisition in Ad-Hoc Scripts
- **Symptom:** `acquire_device_lock` immediately raises `DeviceLockUnavailable` if locked. Standalone scripts in `tools/` bypass locks entirely and invoke raw ADB.
- **Rule:** Provide `wait_for_device_lock(machine, timeout=..., poll_interval=...)` and context manager `operator_device_lock` in `automation-core`. Wrap ad-hoc maintenance scripts so they wait for session teardown instead of conflicting.

## 3. Recommended Implementation Contract

```python
# Operator script pattern:
from automation_core.device_lock import wait_for_device_lock

with wait_for_device_lock(machine=5, project="operator_tool", timeout=300) as lease:
    # Safe exclusive ADB actions here
    ...
```

```powershell
# PowerShell launcher preflight filter:
$filtered = [System.Collections.Generic.List[int]]::new()
foreach ($m in $machineValues) {
    if (Is-Device-Actively-Locked $m) {
        Write-Host "[PRE-FLIGHT] SKIP machine $m: currently locked by active process"
        continue
    }
    $filtered.Add($m)
}
$machineList = ($filtered -join ",")
```
