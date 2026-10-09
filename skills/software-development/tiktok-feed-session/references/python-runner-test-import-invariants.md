# Python Runner Test & Import Invariants (tiktok-luot nuoi acc)

## 1. Module Invariants
- `DeviceContext`, `ExitStatus`, `FlowResult` nằm tại `core.device` (`python_runner/core/device.py`), **KHÔNG** tồn tại `core.device_context`.
- Mọi file flow/test trong `python_runner` BẮT BUỘC import:
  ```python
  from core.device import DeviceContext, ExitStatus, FlowResult
  ```
- Nếu gặp prompt hoặc patch contract ghi `from core.device_context import DeviceContext`, đây là typo/anti-pattern cũ: kiểm tra file thật trước khi patch để tránh `ModuleNotFoundError: No module named 'core.device_context'`.

## 2. Test Path Setup (`_path_setup.py`)
- Mọi test file trong `python_runner/tests/` phải nạp sys.path bằng:
  ```python
  import _path_setup  # noqa: F401
  ```
- `_path_setup.py` tự động chèn `python_runner` (`parents[1]`) vào `sys.path[0]`, giúp import trực tiếp các module `core.*`, `flows.*`, `tests.*`.
- BẮT BUỘC đặt `import _path_setup  # noqa: F401` trước bất kỳ import nào từ `core` hay `flows`.

## 3. Fuzzy Patch Collision Guard
- Trước khi patch test file trong `python_runner/tests/`, luôn đọc 15-20 dòng đầu bằng `read_file` để kiểm tra chính xác thứ tự import hiện tại.
- Tránh fuzzy patch tự động thay thế sai block khi có các dòng import trùng lặp hoặc khi có subagent khác vừa chỉnh sửa file.
