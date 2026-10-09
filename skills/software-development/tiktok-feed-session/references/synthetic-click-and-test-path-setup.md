# Synthetic Click Swipe & Test Invocation (`_path_setup`) in tiktok-luot nuoi acc

## 1. Synthetic Click (100ms swipe) vs 0ms Tap Swallow
- **Problem**: In custom Android UI widgets (such as custom `RecyclerView` item views, in-feed CTA overlays, custom action buttons), ADB `input tap <x> <y>` issues instantaneous (0ms) touch down/up events that can be dropped or swallowed by touch handlers without triggering `onClick`.
- **Solution (Case 2026-09-07)**: In `_tap_ui_element` (and similar UI tap helpers), execute a synthetic click swipe with 100ms duration:
  ```python
  ctx.adb.shell(["input", "swipe", str(x), str(y), str(x), str(y), "100"], timeout=ctx.timeout("adb_seconds", 15))
  ```
  This simulates a natural finger down-hold-up sequence and reliably activates custom click listeners.

## 2. Test Execution Pitfall: ModuleNotFoundError '_path_setup'
- **Problem**: Test scripts in `python_runner/tests/test_*.py` import `_path_setup` (`import _path_setup  # noqa: F401`), which resides in `python_runner/tests/_path_setup.py`. When running unittest from repo root with `PYTHONPATH` unset:
  ```bash
  env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe -m unittest python_runner/tests/test_feed_session_smoke.py
  ```
  Python puts the current directory (`D:/Taadaa/tiktok-luot nuoi acc`) into `sys.path`, but NOT `python_runner/tests/`, triggering:
  `ModuleNotFoundError: No module named '_path_setup'`.
- **Correct Invocations**:
  1. Use unittest discovery targeting `python_runner/tests`:
     ```bash
     env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe -m unittest discover -s python_runner/tests -p test_feed_session_smoke.py
     ```
  2. Or run from within `python_runner/tests`:
     ```bash
     (cd "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests" && D:/Taadaa/python-envs/automation/Scripts/python.exe -m unittest test_feed_session_smoke.py)
     ```
  3. Or pass `PYTHONPATH=python_runner/tests`:
     ```bash
     PYTHONPATH="python_runner/tests" D:/Taadaa/python-envs/automation/Scripts/python.exe -m unittest python_runner/tests/test_feed_session_smoke.py
     ```
