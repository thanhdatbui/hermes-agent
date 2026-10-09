# OpenBLAS Memory Allocation Failure on High-Core Windows Hosts

## Symptom
A Python cron job, watchdog, or background worker fails with exit code 1 and stderr:
```text
OpenBLAS error: Memory allocation still failed after 10 retries, giving up.
OpenBLAS error: Memory allocation still failed after 10 retries, giving up.
...
```
No Python traceback is produced. The Python interpreter terminates immediately because OpenBLAS encounters an allocation failure inside its C library and directly calls `exit(1)` or `abort()`.

## Root Cause
1. **Host Topology**: Multi-socket or high-core Windows machines (e.g. Dual CPU with 56 logical cores, or AMD Threadripper with 64/128 threads).
2. **Implicit Dependency Trigger**: Scripts often do not explicitly import `numpy` or `scipy`, but import libraries like `openpyxl` (which has optional numpy integration) or other data processing tools. When `numpy` is loaded in the environment, OpenBLAS (`libscipy_openblas64.dll` or `openblas.dll`) initializes.
3. **Thread Pool Memory Exhaustion**: By default, OpenBLAS queries the CPU core count (`cpu_count = 56`) and attempts to allocate memory buffers for all 56 worker threads simultaneously via `VirtualAlloc`.
4. **Fragmentation / Heavy Load**: When the machine has high memory commit charge or virtual memory fragmentation (typical on phone farm hosts running dozens of emulator / ADB / runner processes), `VirtualAlloc` fails to find contiguous virtual memory for each thread buffer. After 10 internal retries, OpenBLAS prints the error to stderr and forces process exit.

## 3-Tier Defense Pattern

### Tier 1: Script Level (Immediate / Self-Contained)
At the very top of any watchdog or automation script, before importing any data libraries:
```python
import os

# Prevent OpenBLAS/MKL memory allocation failure on high-core hosts (e.g., 56 cores)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import subprocess
import openpyxl  # Safe now
```
*Note*: `os.environ.setdefault` must be called BEFORE importing `openpyxl`, `pandas`, `scipy`, or `numpy`. Setting it after import has no effect because OpenBLAS allocates its thread structures during DLL initialization.

### Tier 2: Scheduler / Runner Level (Systemic Protection)
In the scheduler (e.g. Hermes cron `_run_job_script` in `cron/scheduler.py` or background process spawner):
Ensure the sanitized child process environment always injects thread caps:
```python
cron_env = _sanitize_subprocess_env(os.environ.copy())
# Default thread caps to prevent OpenBLAS/MKL memory allocation failures on high-core hosts
cron_env.setdefault("OPENBLAS_NUM_THREADS", "1")
cron_env.setdefault("MKL_NUM_THREADS", "1")
cron_env.setdefault("OMP_NUM_THREADS", "1")
cron_env.setdefault("NUMEXPR_NUM_THREADS", "1")

result = subprocess.run(argv, env=cron_env, ...)
```

### Tier 3: Operating System Level (Host-Wide Baseline)
Configure persistent Windows User environment variables so all future shells and child processes inherit safe thread limits:
```powershell
[System.Environment]::SetEnvironmentVariable('OPENBLAS_NUM_THREADS', '1', 'User')
[System.Environment]::SetEnvironmentVariable('MKL_NUM_THREADS', '1', 'User')
[System.Environment]::SetEnvironmentVariable('OMP_NUM_THREADS', '1', 'User')
```

## Verification
Verify that child processes observe the thread limit:
```bash
python -c "import os; print('OPENBLAS_NUM_THREADS:', os.environ.get('OPENBLAS_NUM_THREADS'))"
```

## Deployment & Drive C: Headroom Pitfall
1. **Dual Locations**: Scripts like `feed_session_watchdog.py` exist in both `%LOCALAPPDATA%\hermes\scripts\` and `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`. Both must be updated to prevent sync regressions.
2. **Drive C: Space Exhaustion**: When `%LOCALAPPDATA%` (drive `C:`) has low free space (<200MB), standard patch tools using temporary file buffering can fail with `No space left on device`. Apply changes to `D:` first, then stream directly to `C:` via Python binary write:
```python
with open("D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py", "rb") as src:
    data = src.read()
with open("C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py", "wb") as dst:
    dst.write(data)
```
Follow up with `python -m py_compile` to ensure integrity.
