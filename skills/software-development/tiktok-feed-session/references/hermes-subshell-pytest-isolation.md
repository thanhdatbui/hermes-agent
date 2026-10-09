# Hermes Subshell PYTHONPATH Isolation & Feed Swipe Testing

## 1. Pitfall: PYTHONPATH Inheritance in Hermes Subshell
When running external python virtual environments (e.g., `D:/Taadaa/python-envs/automation/Scripts/python.exe` running Python 3.12) via Hermes Agent's terminal bash tool, the shell inherits `PYTHONPATH` from Hermes Agent's own runtime (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`).

### Manifestation
When pytest or python imports packages with compiled C-extensions (such as Pillow / `PIL`):
```text
ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)
```
The runner attempts to load the 3.11 C-extension DLLs from Hermes venv into Python 3.12, causing test collection to fail immediately.

### Prevention / Fix
Prefix terminal commands with `PYTHONPATH=""` or run `unset PYTHONPATH` before executing tests:
```bash
cd "/d/Taadaa/tiktok-luot nuoi acc" && PYTHONPATH="" D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest python_runner/tests/test_feed_swipe_smoke.py -k "swipe" -v
```

## 2. ADBError Exception Handling in Feed Swipe Smoke
In `python_runner/flows/feed_swipe_smoke.py`:
- `_perform_feed_swipe` wraps `ctx.adb.shell(["input", "swipe", ...], timeout=swipe_timeout)` in a try/except block.
- On transient timeout, it catches `ADBError`, logs a retry step, waits 1.0s, and retries the swipe once.
- If the second attempt also raises `ADBError`, it logs failure and returns `False` (fail-closed).
- **Critical Invariant:** `python_runner/flows/feed_swipe_smoke.py` must import `ADBError` from `core.adb`:
  ```python
  from core.adb import ADBError
  ```
  Missing this import turns an ADB timeout into an unhandled `NameError: name 'ADBError' is not defined`.
