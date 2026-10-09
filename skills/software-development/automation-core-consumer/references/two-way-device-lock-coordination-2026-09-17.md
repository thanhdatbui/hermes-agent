# Two-Way Device Lock Coordination Architecture (Feed Session vs Operator Scripts)

## Problem & Concurrency Model
In phone farms (such as Taadaa 74 Samsung S7 devices), devices are shared between:
1. **Automated Scheduled Batch Runs (Feed Sessions / Mass Nurture):** Runs multi-device batches (e.g. 50–74 machines). Must run uninterrupted once a device is claimed.
2. **Ad-hoc Operator Scripts:** Maintenance, account inspection, APK upgrades, password resets, or test canaries.

Two critical failure modes exist without two-way coordination:
- **Direction 1 (Operator locks device -> Feed session triggers):** The scheduled feed session must cleanly skip the locked device (Clean Skip) without marking the whole multi-machine batch as `MANUAL_NEEDED` / exit code 2.
- **Direction 2 (Feed session running -> Operator runs script):** The operator script must not issue conflicting ADB commands or steal focus. Instead, it must atomically wait (with timeout & retry) until the feed session releases the device lock, then acquire it exclusively.

---

## Key Invariants & Pitfalls

### 1. The Windows PID Reuse Trap
- On Windows NTFS, Process IDs (PIDs) are rapidly recycled.
- Relying solely on `psutil.pid_exists(pid)` or `GetExitCodeProcess` can falsely report a dead process as active if another unrelated process was assigned the same PID.
- **Invariant:** Stored lock metadata MUST include `process_started_at` (obtained via `GetProcessTimes` on Win32 or fallback to `wmic process where ProcessId=X get CreationDate`). When validating a lock's liveness, verify `current_process_started_at == stored_process_started_at`.

### 2. Single-Mode vs Multi-Machine Lock Parity
- **Pitfall:** `run_tiktok.py` in single-device mode historically used `user_authorized=False`, returning a no-op `_UnlockedDeviceLockLease` which wrote ZERO lock files to disk. Operator tools inspecting `~/.codex/device-locks/` saw no lock and presumed the machine was idle, causing immediate ADB collision.
- **Invariant:** All device executions (single-mode and batch) must acquire real, persistent locks on disk with `user_authorized=True` and `release_on_terminal=True`.

### 3. Batch Aggregation Semantics (`_aggregate_rows`)
- **Pitfall:** Treating `skipped-device-locked` the same as `needs-user-decision`. A device locked by an active operator script is an *expected transient state*. Escalating `skipped-device-locked` to `MANUAL_NEEDED` causes a batch of 74 devices with 73 successes and 1 locked device to fail the entire run.
- **Hierarchy:**
  - `needs-user-decision`: Stored or ambiguous conflicting lock -> `MANUAL_NEEDED`.
  - `skipped-device-locked`: Operator or known peer holds lock -> Mark device as skipped; if other devices succeeded, return `SUCCESS_WITH_SKIPS` (exit 0).
  - Only escalate to `MANUAL_NEEDED` if 100% of devices were locked / no work was runnable.

### 4. Wait & Context Manager Pattern for Operator Tools
Instead of ad-hoc ADB commands, operator tools should use a polling wait wrapper:
```python
@contextmanager
def operator_device_lock(
    *, machine=None, serial=None, project="operator_tool",
    timeout=300.0, poll_interval=5.0, release_on_terminal=True
):
    lease = wait_for_device_lock(
        machine=machine, serial=serial, project=project,
        timeout=timeout, poll_interval=poll_interval,
        release_on_terminal=release_on_terminal
    )
    try:
        yield lease
    finally:
        if release_on_terminal:
            lease.release()
```
Or via CLI wrapper:
`python D:/Taadaa/tools/with_device_lock.py --machine 12 -- python D:/Taadaa/tools/upgrade_tiktok.py`
