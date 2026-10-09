# Bidirectional Device Lock Orchestration: Feed Session vs Operator Tools

## 1. Problem Context (The 2-Way Lock Dispute)

In high-density phone farms (e.g. Taadaa 74 machines), two distinct execution modes conflict:
1. **Direction 1 (Operator Preempts/Intervenes)**: Operator locks a machine to run maintenance/debugging scripts (e.g. APK upgrades, account logouts, proxy tuning). When a scheduled feed session (ca nuôi) fires, the batch must **cleanly skip** that machine rather than marking the entire 74-machine batch as `MANUAL_NEEDED` (exit code 2).
2. **Direction 2 (Feed Session Running)**: When a feed session or batch is currently running on a device, operator maintenance scripts must **automatically wait (poll with timeout)** until the feed session releases the device lock, then acquire exclusivity.

---

## 2. Shared Core Architecture (`automation-core`)

### `wait_for_device_lock`
Polling wrapper over `acquire_device_lock`:
- Accepts `machine`, `serial`, `project`, `timeout`, `poll_interval`, `wait_on_user_decision`, `release_on_terminal`.
- Enforces non-negative timeout (`timeout >= 0`) and positive poll interval (`poll_interval > 0`).
- Loops with `time.monotonic()` to track actual elapsed time (`waited_seconds = elapsed`).
- Raises structured `DeviceLockTimeoutError` carrying `machine`, `serial`, `owner`, and `waited_seconds`.

### `operator_device_lock` (Context Manager)
```python
from automation_core.device_lock import operator_device_lock

with operator_device_lock(machine=12, project="operator_tool", timeout=300):
    # Device lock is held exclusively on disk (machine_12.lock.json + serial_...lock.json)
    # Perform maintenance/ADB commands here...
# Exiting block guarantees lease.release()
```

### CLI Wrapper (`tools/with_device_lock.py`)
Wraps arbitrary commands so ad-hoc operator scripts automatically queue behind feed sessions:
```bash
python D:/Taadaa/tools/with_device_lock.py --machine 12 -- python D:/Taadaa/tools/upgrade_tiktok.py 12
```

---

## 3. Consumer Batch Aggregation (`tiktok-luot nuoi acc`)

### The Semantic Split in `_aggregate_rows`
Do not conflate `needs-user-decision` with `skipped-device-locked`:
- `needs-user-decision`: An explicit conflict that requires operator review -> Retain `ExitStatus.MANUAL_NEEDED`.
- `skipped-device-locked`: An expected transient skip due to operator locking.
  - **Partial skip** (some machines succeeded/degraded, some skipped-device-locked): Return **`ExitStatus.SUCCESS`** with summary message `"multi-machine-feed-session completed with some locked machines cleanly skipped"`.
  - **100% skipped** (all machines skipped-device-locked): Return `ExitStatus.MANUAL_NEEDED` because no actual work took place.

### PowerShell Preflight Caveat
Do not silently drop locked machines from `$machineList` in launcher scripts (e.g. `run-feed-session.ps1`) before invoking the Python runner. Dropping them causes them to disappear from telemetry and aggregation summaries. Instead, pass the full list to the runner so `execute_multi_machine_feed_session` can record structured `skipped-device-locked` artifacts for each skipped target.
