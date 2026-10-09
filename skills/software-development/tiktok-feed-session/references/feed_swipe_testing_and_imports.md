# Feed Swipe Testing and Core Imports Reference

## 1. Import Locations in `python_runner`
When writing or patching unit tests for `feed_swipe_smoke` (in `python_runner/tests/test_feed_swipe_smoke.py`):
- `FlowResult`, `ExitStatus`, and `DeviceContext` MUST be imported from `core.device`:
  ```python
  from core.device import ExitStatus, FlowResult
  ```
  *(Do NOT use `from core.flow_result import FlowResult` — `core.flow_result` does not exist in `python_runner` and causes `ModuleNotFoundError`)*.
- Deadline handling:
  ```python
  from core.deadline import RunPlanDeadlineExceeded, ensure_run_plan_deadline
  ```
- Logger:
  ```python
  from core.logger import JsonlLogger
  ```

## 2. Running Focused Tests
- Always run pytest targeted with `-k` and point directly to the test file:
  ```bash
  pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_feed_swipe_smoke.py" -k "deadline" -v
  ```
- Run directly inside `D:/Taadaa/tiktok-luot nuoi acc/python_runner`.

## 3. Tool and Scanning Safety
- Never run generic recursive scans like `find /d/Taadaa` or `grep -rn` across the entire `D:/Taadaa` directory.
- `D:/Taadaa` contains heavy trees (node_modules, virtual environments, backup archives) that will trigger a timeout (>180s).
- Target files directly using known paths under `python_runner/`.
