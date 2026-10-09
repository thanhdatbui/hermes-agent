# ADB Heavy I/O Semaphore Remediation & Concurrency Bounding (Closeout Gate 82 -> 85+)

## Context & Finding Trigger
When introducing concurrency throttling or USB bus protection primitives in `automation-core/src/automation_core/adb.py` (e.g. `_HEAVY_IO_SEMAPHORE = threading.BoundedSemaphore(8)`), Closeout Gate reviews (specifically Sol Auditor / Reviewer) penalize incomplete implementations with scores around 82/100 across 3 criteria:
1. **Logic Correctness / Robustness (Finding 1)**: Incomplete or fragile heavy I/O identification.
2. **Telemetry & Observability (Finding 2)**: Silent thread blocking without wait duration measurement or queue saturation alerts.
3. **Test Evidence (Finding 3)**: Missing dedicated concurrency bounding unit tests proving semaphore acquisition and guaranteed release under exception/timeout.

## 1. Heavy I/O Identification Normalization (`_is_heavy_io`)
### Anti-Pattern
```python
def _is_heavy_io(args: Sequence[str]) -> bool:
    first = args[0] if args else ""
    return first in ("pull", "push", "install", "exec-out") or "screencap" in args
```
- Missing subcommands like `sync`, `install-multiple`.
- Vulnerable to false positives or bypasses when invoked as `shell screencap`, `shell exec-out`, or when flags precede subcommands.

### Standardized Pattern
```python
HEAVY_IO_COMMANDS = frozenset({"pull", "push", "install", "install-multiple", "sync", "exec-out"})

def _is_heavy_io(args: Sequence[str]) -> bool:
    if not args:
        return False
    # Check top-level command
    cmd = args[0]
    if cmd in HEAVY_IO_COMMANDS:
        return True
    # Check shell-level heavy commands
    if cmd == "shell":
        # Look for screencap, screenrecord, content read/write heavy operations
        sub_args = [a for a in args[1:] if not a.startswith("-")]
        if sub_args and sub_args[0] in {"screencap", "screenrecord", "dumpstate"}:
            return True
    return "screencap" in args or "screenrecord" in args
```

## 2. Semaphore Wait Latency & Saturation Telemetry
### Implementation
Always measure semaphore acquisition latency. If threads wait (`wait_s > 0.05` or significant queue delay), emit structured logs and update telemetry:
```python
t0 = time.monotonic()
acquired = _HEAVY_IO_SEMAPHORE.acquire(timeout=effective_timeout)
wait_duration = time.monotonic() - t0

if wait_duration > 0.1:
    logger.warning(
        f"[ADB_HEAVY_IO_WAIT] Semaphore wait exceeded threshold: {wait_duration:.3f}s for command: {safe_args(command)}"
    )

try:
    completed = _run_bounded(command, timeout=effective_timeout, text=text)
finally:
    _HEAVY_IO_SEMAPHORE.release()
```
Always use explicit `try ... finally` to guarantee token release even if `TimeoutExpired`, `FileNotFoundError`, or custom `ADBError` occurs.

## 3. Required Test Suite Verification in `tests/test_adb_subprocess.py`
To pass the Closeout Gate test evidence rubric (scoring >= 23/25), include 3 deterministic unit tests:
1. **Concurrency bounding test**: Spawn $N > 8$ threads simulating concurrent heavy I/O operations with a barrier or sleep, asserting active concurrent executions $\le 8$.
2. **Release on exception/timeout test**: Trigger a failure (`TimeoutExpired` or `OSError`) inside `_run_bounded` and assert the bounded semaphore's internal value returns to full capacity (8 tokens).
3. **Wait latency telemetry assertion**: Mock semaphore acquisition delay and assert that `[ADB_HEAVY_IO_WAIT]` structured log / telemetry is triggered.
