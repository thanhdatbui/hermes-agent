# SafeAdb and adb_guard Patterns in automation-core

## Overview
`SafeAdb` and `adb_guard` provide strict locking enforcement around ADB executions:
- `SafeAdb`: Wraps `DeviceContext` to ensure commands to a specific device serial are gated by a distributed lock. Provides rolling wait retry (`acquire(timeout_seconds=...)`) and enforces that `.run()` or `.shell()` can only be called inside the active context manager.
- `adb_guard`: Monkey-patches `subprocess.run` to intercept raw `adb -s <serial>` calls across consumers or libraries. If the target serial is not currently held in `_ACTIVE_LOCKED_SERIALS`, `LockNotHeldError` is raised immediately.

## Verification & Import Pitfall (PYTHONPATH)
When running tests or modules in `automation-core`:
1. `automation-core` might be installed in the active venv in non-editable mode (`site-packages`), or `PYTHONPATH` may default to the current working directory.
2. In such cases, newly added submodules in `src/automation_core/` (like `safe_adb.py` or `adb_guard.py`) will fail with `ModuleNotFoundError: No module named 'automation_core.<new_module>'` during test collection unless `PYTHONPATH=src` is explicitly prepended.
3. **Canonical test execution**:
   ```bash
   PYTHONPATH=src pytest tests/test_safe_adb.py -v
   ```
