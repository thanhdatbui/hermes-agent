# Pytest Cache Contention & Foreground Timeout Anti-Hang Pattern

## 1. Symptom & Root Cause
- **Symptom**: Commands hang for 380s–900s (hitting the 15-minute timeout ceiling), accumulating across multiple sequential calls and causing the agent session to hang for hours.
- **Root Causes**:
  1. **Windows `.pytest_cache` Lock / Permission Denied (Errno 13)**: When multiple subagents or background processes run pytest in the same workspace or venv, concurrent writes to `.pytest_cache\v\cache\nodeids` cause Windows file-lock collisions, resulting in `Permission denied: [Errno 13]` and massive test slowdowns / indefinite blocking.
  2. **Unfocused Pytest Suites**: Running whole test suites (e.g. `pytest tests/`) instead of focused tests executes hundreds of integration/device tests that wait on network/ADB timeouts.
  3. **Broad Recursive Walks**: Running `os.walk`, `find`, or unbounded searches across `D:\Taadaa`, `D:\OneDrive`, `.ai-runs`, or `runtime` (150k+ files) blocks the process until the 900s foreground timeout kills it.

## 2. Standard Rules & Mitigations

### A. Disable Pytest Cache Provider
Always pass `-p no:cacheprovider` when running pytest across shared farm repos / automation venvs to eliminate `.pytest_cache` file locks:
```bash
PYTHONPATH="python_runner;." python -m pytest -p no:cacheprovider python_runner/tests/test_feed_session_smoke.py -k "test_specific_function" -q
```

### B. Strict Focused Test Scope (<30s)
- **CẤM** chạy toàn bộ test suite (`pytest tests/`) trên farm.
- **BẮT BUỘC** chỉ định rõ file test và test case cụ thể qua `-k` hoặc cú pháp `tests/test_file.py::test_case`.
- Thời gian chạy test phải < 30 giây.

### C. Cấm Quét Đệ Quy Thư Mục Lớn
- **CẤM** `os.walk('D:\\Taadaa')`, `find /d/Taadaa`, `grep -r` trên toàn bộ workspace/runtime.
- Khi cần kiểm tra log hoặc artifact máy N: vào THẲNG thư mục `runtime/machine_N` hoặc đọc file cấu hình cụ thể (`kibe.yaml`, `taikhoan_run_safe.xlsx`).
- Bounded file checks: dùng `maxdepth 2` hoặc chỉ định chính xác đường dẫn file.
