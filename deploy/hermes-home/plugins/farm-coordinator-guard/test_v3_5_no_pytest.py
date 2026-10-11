import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    check_worker_tool_gate,
    _PARENT_SESSION_CACHE,
    _validate_worker_terminal_command,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_pytest_and_python_arbitrary_execution_completely_blocked():
    """Worker tuyệt đối KHÔNG ĐƯỢC chạy pytest hay python tùy ý."""
    worker_sid = "worker_no_pytest"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # pytest trỏ vào file bảo vệ -> BỊ CHẶN 100%
    res1 = check_worker_tool_gate("terminal", worker_sid, {"command": "pytest C:/Users/Kibe/AppData/Local/hermes/state.db"})
    assert res1 is not None
    assert "PROTECTED TARGET" in res1.get("reason", "") or "INFO-LEAK BLOCKED" in res1.get("reason", "")

    # python -m pytest trỏ vào guard -> BỊ CHẶN 100%
    res2 = check_worker_tool_gate("terminal", worker_sid, {"command": "python -m pytest C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py"})
    assert res2 is not None
    assert "PROTECTED TARGET" in res2.get("reason", "") or "INFO-LEAK BLOCKED" in res2.get("reason", "")

    # python script tự do -> BỊ CHẶN 100%
    res3 = check_worker_tool_gate("terminal", worker_sid, {"command": "python my_script.py"})
    assert res3 is not None
    assert "DEFAULT-DENY TERMINAL" in res3.get("reason", "")


def test_windows_backslash_path_inspect_machine_exact_match():
    """Lệnh inspect_machine với path Windows chứa backslash không bị nuốt bởi shlex và match chính xác."""
    worker_sid = "worker_inspect_win"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # Lệnh có backslash chuẩn Windows
    cmd = r"python D:\Taadaa\tools\inspect_machine.py 41"
    res = check_worker_tool_gate("terminal", worker_sid, {"command": cmd})
    assert res is None  # Cho phép!
