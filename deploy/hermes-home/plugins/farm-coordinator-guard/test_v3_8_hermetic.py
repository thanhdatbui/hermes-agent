import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    check_worker_tool_gate,
    _PARENT_SESSION_CACHE,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_gap_2_git_full_hermetic_env():
    """Xác nhận hermetic git environment đầy đủ."""
    worker_sid = "worker_git_hermetic"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    res = check_worker_tool_gate("terminal", worker_sid, {"command": "git diff"})
    assert res is None
    assert os.environ.get("GIT_CONFIG_GLOBAL") == os.devnull
    assert os.environ.get("GIT_CONFIG_SYSTEM") == os.devnull
    assert os.environ.get("GIT_ALLOW_PROTOCOL") == "file"
    assert os.environ.get("GIT_TERMINAL_PROMPT") == "0"


def test_worker_info_leak_read_file_blocked():
    """Worker dùng read_file đọc state.db hoặc guard source -> BỊ CHẶN."""
    worker_sid = "worker_leak"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # Đọc state.db -> BỊ CHẶN!
    res1 = check_worker_tool_gate("read_file", worker_sid, {"path": "C:/Users/Kibe/AppData/Local/hermes/state.db"})
    assert res1 is not None
    assert "INFO-LEAK BLOCKED" in res1.get("reason", "")

    # Đọc guard source -> BỊ CHẶN!
    res2 = check_worker_tool_gate("read_file", worker_sid, {"path": "C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py"})
    assert res2 is not None
    assert "INFO-LEAK BLOCKED" in res2.get("reason", "")
