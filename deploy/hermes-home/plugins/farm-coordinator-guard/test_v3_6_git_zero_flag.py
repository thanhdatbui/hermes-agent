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


def test_git_c_flag_arbitrary_execution_blocked():
    """LỖ HỔNG CHÍ MẠNG MỚI: git -c core.pager=... hoặc git -c ... BỊ CHẶN TUYỆT ĐỐI."""
    worker_sid = "worker_git_c"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # 1. git -c core.pager=calc.exe log -> BỊ CHẶN!
    res1 = check_worker_tool_gate("terminal", worker_sid, {"command": "git -c core.pager=calc.exe log"})
    assert res1 is not None
    assert "GIT FLAG/COMMAND BLOCKED" in res1.get("reason", "")

    # 2. git -c "core.pager=python C:\\evil.py" log -> BỊ CHẶN!
    res2 = check_worker_tool_gate("terminal", worker_sid, {"command": 'git -c "core.pager=python evil.py" log'})
    assert res2 is not None
    assert "GIT FLAG/COMMAND BLOCKED" in res2.get("reason", "")

    # 3. git diff -p -> BỊ CHẶN VÌ CÓ CỜ!
    res3 = check_worker_tool_gate("terminal", worker_sid, {"command": "git diff -p"})
    assert res3 is not None
    assert "GIT FLAG BLOCKED" in res3.get("reason", "")


def test_shell_metacharacters_percent_and_caret_blocked():
    """Chặn % (Windows env expansion) và ^ (cmd escape)."""
    worker_sid = "worker_meta"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # cmd có % -> BỊ CHẶN!
    res_percent = check_worker_tool_gate("terminal", worker_sid, {"command": "git status %VAR%"})
    assert res_percent is not None
    assert "HERMETIC SHELL" in res_percent.get("reason", "")

    # cmd có ^ -> BỊ CHẶN!
    res_caret = check_worker_tool_gate("terminal", worker_sid, {"command": "git status ^"})
    assert res_caret is not None
    assert "HERMETIC SHELL" in res_caret.get("reason", "")


def test_clean_git_status_diff_log_allowed():
    """Lệnh git sạch không có cờ -> CHO PHÉP."""
    worker_sid = "worker_clean_git"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    assert check_worker_tool_gate("terminal", worker_sid, {"command": "git status"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "git diff"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "git log"}) is None
