# Subprocess sys.path Strip Trap & Dispatch Worker Routing Invariant

## 1. Subprocess sys.path Strip Trap (The 0.001s Instant Crash Loop)

### Problem Description
In farm automation architectures, child scripts (such as `batch_gpm_hotmail_password_login.py`) spawned by supervisors often try to isolate their execution environment to avoid C-extension binary conflicts (e.g. `greenlet._greenlet`):
```python
# ANTI-PATTERN: Blindly stripping virtualenv site-packages
sys.path = [p for p in sys.path if not ("hermes" in p.lower() and "site-packages" in p.lower())]
```

### Root Cause
When the script is spawned by a scheduler or supervisor using `sys.executable` from the virtual environment itself (e.g. `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe`):
1. `sys.path` is stripped of the virtual environment's own `site-packages`.
2. The child process immediately loses access to its installed third-party libraries (`requests`, `playwright`, `openpyxl`).
3. Calling `import requests` in `gpm_client.py` raises `ModuleNotFoundError: No module named 'requests'` within **1 millisecond** (0.001s).
4. The child exits with code 1 without ever opening a browser or contacting the GPM API.
5. The supervisor interprets exit code 1 as an authentication failure (`Hotmail login that bai`), increments `login_retry_count` from 1 to 3 in consecutive ticks, and escalates healthy accounts into `QUARANTINE`.

### Diagnostic Signature
- In `batch_gpm_5profiles_supervisor_state.json`, multiple accounts across an entire batch (e.g. 5 accounts) fail with the **exact same millisecond timestamp** (`at: 2026-10-28T17:36:06.642039` to `17:36:06.643062`).
- A genuine browser login over a mobile proxy takes 15–45 seconds. Any failure occurring in $\le 0.1$s is guaranteed to be an environment/ImportError crash at launch, never a bad password or proxy disconnect.

### Safe Patch Contract
Always guard the strip logic against the active interpreter's own prefix:
```python
# SAFE CONTRACT: Only strip foreign hermes paths when running under an external interpreter
if "hermes" not in sys.prefix.lower():
    sys.path = [p for p in sys.path if not ("hermes" in p.lower() and "site-packages" in p.lower())]
```

---

## 2. Hard Gate #3: Code Edit Dispatch via dispatch_worker.py

### Policy Constraint
- `delegate_task` is strictly BLOCKED for code modification tasks:
  `[HARD GATE #3 - CODE EDIT DISPATCH BLOCKED] delegate_task BỊ CẤM CHO TASK SỬA CODE! Bắt buộc thi công qua dispatch_worker.py (O(1), 6-15s).`
- Coordinator must never attempt code edits via `delegate_task`.

### Canonical Execution Command
Execute via terminal using `dispatch_worker.py` with scoped contract, file target, and unique anchor:
```bash
python D:/Taadaa/tools/dispatch_worker.py \
  "Fix line 22 in scripts/<file>.py: replace '<old>' with '<new>'" \
  --workdir "D:/Taadaa/<repo>" \
  --file "D:/Taadaa/<repo>/<file>.py" \
  --anchor "<unique_symbol_anchor>"
```

### Coordinator Terminal Concurrency & Timeout
- `dispatch_worker.py` routes through Tier 1 (Sol Web Worker :20129) -> Tier 2 (Agy CLI) -> Tier 3 (Haiku CLI). Execution typically takes 60–200 seconds.
- To prevent triggering **Hard Gate #5 (Device/Coordinator Bulkhead)** which blocks foreground execution $>60$s, Coordinator MUST launch via background process:
  `terminal(command=..., background=True, notify_on_complete=True)`
- Verification: Poll with `process(action='poll', session_id=...)` and verify syntax using `python -m py_compile <file.py>` and `<file.py> --help`.
