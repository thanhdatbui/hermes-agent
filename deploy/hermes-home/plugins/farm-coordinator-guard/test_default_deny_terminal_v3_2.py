import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    _on_pre_tool_call,
    check_worker_tool_gate,
    _update_session_state,
    _PARENT_SESSION_CACHE,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_worker_arbitrary_python_terminal_blocked_default_deny():
    """LỖ HỔNG CHÍ MẠNG MỚI: Worker chạy terminal 'python foo.py' hoặc 'python -c ...' -> BỊ DEFAULT-DENY CHẶN!"""
    worker_sid = "worker_python_escape"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # 1. python foo.py -> BỊ CHẶN!
    res1 = check_worker_tool_gate("terminal", worker_sid, {"command": "python foo.py"})
    assert res1 is not None
    assert res1.get("action") == "block"
    assert "DEFAULT-DENY TERMINAL" in res1.get("reason", "")

    # 2. python -c "..." -> BỊ CHẶN!
    res2 = check_worker_tool_gate("terminal", worker_sid, {"command": 'python -c "import sqlite3..."'})
    assert res2 is not None
    assert "DEFAULT-DENY TERMINAL" in res2.get("reason", "")

    # 3. bash / node / powershell -> BỊ CHẶN!
    res3 = check_worker_tool_gate("terminal", worker_sid, {"command": "bash run.sh"})
    assert res3 is not None
    assert "DEFAULT-DENY TERMINAL" in res3.get("reason", "")


def test_worker_whitelisted_terminal_commands_allowed():
    """Các lệnh kiểm thử/kiểm tra hợp lệ trong WORKER_TERMINAL_ALLOWLIST -> CHO PHÉP."""
    worker_sid = "worker_valid_tests"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # pytest -> Cho phép
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "pytest -v tests/test_core.py"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "python -m pytest tests/"}) is None

    # git diff / status -> Cho phép
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "git diff"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "git status"}) is None

    # inspect_machine.py -> Cho phép
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "python D:/Taadaa/tools/inspect_machine.py 41"}) is None


def test_protected_state_db_and_guard_source():
    """State.db và Guard Plugin được bảo vệ tuyệt đối trước mọi hành vi ghi."""
    worker_sid = "worker_db_attack"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # Worker cố ghi vào state.db -> BỊ CHẶN!
    db_path = r"C:/Users/Kibe/AppData/Local/hermes/state.db"
    res = check_worker_tool_gate("write_file", worker_sid, {"path": db_path})
    assert res is not None
    assert "SELF-MODIFICATION BLOCKED" in res.get("reason", "")
